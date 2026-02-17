"""Gmail API client for fetching and processing bank notification emails.

Uses a hardcoded refresh token (single-user system) to auto-refresh access
tokens at runtime. All Gmail API calls are sync (google-api-python-client uses
httplib2) and are wrapped in asyncio.to_thread for non-blocking execution.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Settings

logger = logging.getLogger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _build_credentials(settings: Settings) -> Credentials:
    """Build OAuth2 credentials from stored refresh token."""
    return Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri=_TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )


def _build_service(settings: Settings):
    """Build a Gmail API service client (sync -- call from thread)."""
    creds = _build_credentials(settings)
    return build("gmail", "v1", credentials=creds)


async def get_user_email(settings: Settings) -> str:
    """Fetch the Gmail address associated with the stored credentials."""
    def _get():
        service = _build_service(settings)
        profile = service.users().getProfile(userId="me").execute()
        return profile["emailAddress"]

    return await asyncio.to_thread(_get)


async def register_watch(settings: Settings) -> dict:
    """Register a Gmail push notification watch via Pub/Sub.

    Returns the watch response containing historyId and expiration (ms epoch).
    """
    def _watch():
        service = _build_service(settings)
        topic = f"projects/{settings.google_project_id}/topics/athena-gmail"
        return service.users().watch(
            userId="me",
            body={"topicName": topic, "labelIds": ["INBOX"]},
        ).execute()

    return await asyncio.to_thread(_watch)


async def fetch_history_message_ids(
    settings: Settings, start_history_id: str
) -> list[str]:
    """Fetch message IDs added since the given history ID.

    Uses Gmail history.list with messageAdded filter. Returns deduplicated
    message IDs in discovery order.
    """
    def _fetch():
        service = _build_service(settings)
        message_ids: list[str] = []
        seen: set[str] = set()
        page_token = None

        while True:
            response = service.users().history().list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded"],
                pageToken=page_token,
            ).execute()

            for record in response.get("history", []):
                for added in record.get("messagesAdded", []):
                    msg_id = added.get("message", {}).get("id")
                    if msg_id and msg_id not in seen:
                        seen.add(msg_id)
                        message_ids.append(msg_id)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return message_ids

    return await asyncio.to_thread(_fetch)


async def get_message(settings: Settings, message_id: str) -> dict:
    """Fetch a full Gmail message by ID."""
    def _get():
        service = _build_service(settings)
        return service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

    return await asyncio.to_thread(_get)


def extract_header(message: dict, name: str) -> str | None:
    """Extract a header value from a Gmail message payload."""
    headers = message.get("payload", {}).get("headers", [])
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def extract_body_html(message: dict) -> str | None:
    """Extract the HTML body from a Gmail message payload.

    Handles both simple and multipart MIME structures by recursively
    searching for text/html parts.
    """
    payload = message.get("payload", {})
    return _extract_html_from_part(payload)


def _extract_html_from_part(part: dict) -> str | None:
    """Recursively search MIME parts for text/html content."""
    if part.get("mimeType") == "text/html":
        data = part.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for sub_part in part.get("parts", []):
        result = _extract_html_from_part(sub_part)
        if result:
            return result

    return None


def watch_needs_renewal(expiry: datetime | None) -> bool:
    """True if the watch is expired or expiring within 24 hours."""
    if expiry is None:
        return True
    threshold = datetime.now(timezone.utc) + timedelta(hours=24)
    return expiry <= threshold


def parse_watch_expiry(expiration_ms: int | str) -> datetime:
    """Convert Gmail API watch expiration (ms since epoch) to datetime."""
    return datetime.fromtimestamp(int(expiration_ms) / 1000, tz=timezone.utc)
