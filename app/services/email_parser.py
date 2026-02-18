"""Parsers for Bank of America email notifications.

Extracts balance and debit-card-usage data from BofA HTML alert emails.
Parsers strip HTML tags and apply regex patterns to the plain text content.
These patterns may need tuning if BofA changes their email format.
"""
from __future__ import annotations

import html as html_module
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

BOA_SENDER = "onlinebanking@ealerts.bankofamerica.com"

# Subject line markers (compared case-insensitively).
BALANCE_SUBJECT = "your available balance"
DEBIT_SUBJECT = "your debit card was used"

# -- Regex patterns --------------------------------------------------------

_STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

# Balance email: dollar amount near "Balance".
_BALANCE_RE = re.compile(
    r"(?:available\s+)?balance[:\s]*\$?([\d,]+\.\d{2})", re.IGNORECASE
)

# Account identifier like "Account - 1787".
_ACCOUNT_RE = re.compile(r"account\s*[-:]\s*(\d{4})", re.IGNORECASE)

# Debit email: dollar amount near "Amount".
_AMOUNT_RE = re.compile(r"amount[:\s]*\$?([\d,]+\.\d{2})", re.IGNORECASE)

# Merchant name after common labels.
_MERCHANT_RE = re.compile(
    r"(?:purchase\s+made\s+at|where|merchant)[:\s]+(.+?)(?:\s{2,}|$)",
    re.IGNORECASE,
)

# Card ending in four digits.
_CARD_RE = re.compile(r"ending\s+in\s+(\d{4})", re.IGNORECASE)

# Date like "February 15, 2026".
_DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October"
    r"|November|December)\s+\d{1,2},\s+\d{4}",
    re.IGNORECASE,
)


@dataclass
class BalanceNotification:
    """Parsed data from a BofA available-balance email."""

    balance: Decimal
    account_label: str | None
    observed_at: datetime


@dataclass
class DebitNotification:
    """Parsed data from a BofA debit-card-used email."""

    amount: Decimal
    merchant: str | None
    card_last_four: str | None
    purchase_date: datetime


# -- Helpers ---------------------------------------------------------------


def _strip_html(raw: str) -> str:
    """Remove HTML tags, decode entities, and collapse whitespace."""
    text = _STYLE_RE.sub("", raw)
    text = _TAG_RE.sub(" ", text)
    text = html_module.unescape(text)
    # Normalize non-breaking spaces.
    text = text.replace("\xa0", " ")
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _parse_dollar(raw: str) -> Decimal | None:
    """Parse a dollar string like '7,981.52' into Decimal."""
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def _parse_date(text: str) -> datetime | None:
    """Extract and parse the first date found (e.g. 'February 15, 2026')."""
    match = _DATE_RE.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(0), "%B %d, %Y").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


# -- Public API ------------------------------------------------------------


def parse_balance_email(html: str, received_at: datetime | None = None) -> BalanceNotification | None:
    """Parse a BofA 'Available Balance' email and extract balance data.

    Returns None if the required balance amount cannot be extracted.
    Falls back to *received_at* (email Date header) or utcnow() for the
    observation timestamp when the email body contains no parseable date.
    """
    text = _strip_html(html)

    balance_match = _BALANCE_RE.search(text)
    if not balance_match:
        return None

    balance = _parse_dollar(balance_match.group(1))
    if balance is None:
        return None

    account_match = _ACCOUNT_RE.search(text)
    account_label = f"Account - {account_match.group(1)}" if account_match else None

    # Prefer the email Date header (precise timestamp) over body date (midnight-only).
    observed_at = received_at or _parse_date(text) or datetime.now(timezone.utc)

    return BalanceNotification(
        balance=balance,
        account_label=account_label,
        observed_at=observed_at,
    )


def parse_debit_email(html: str, received_at: datetime | None = None) -> DebitNotification | None:
    """Parse a BofA 'Debit Card Used' email and extract transaction data.

    Returns None if the required amount cannot be extracted.
    Falls back to *received_at* (email Date header) or utcnow() when
    the email body contains no parseable date.
    """
    text = _strip_html(html)

    amount_match = _AMOUNT_RE.search(text)
    if not amount_match:
        return None

    amount = _parse_dollar(amount_match.group(1))
    if amount is None:
        return None

    merchant_match = _MERCHANT_RE.search(text)
    merchant = merchant_match.group(1).strip() if merchant_match else None

    card_match = _CARD_RE.search(text)
    card_last_four = card_match.group(1) if card_match else None

    purchase_date = _parse_date(text) or received_at or datetime.now(timezone.utc)

    return DebitNotification(
        amount=amount,
        merchant=merchant,
        card_last_four=card_last_four,
        purchase_date=purchase_date,
    )


def try_parse_email(
    subject: str, html: str, received_at: datetime | None = None
) -> BalanceNotification | DebitNotification | None:
    """Route to the correct parser based on the email subject.

    Returns None if the subject doesn't match known BofA patterns or
    if parsing fails.
    """
    lower_subject = subject.lower()

    if BALANCE_SUBJECT in lower_subject:
        return parse_balance_email(html, received_at)

    if DEBIT_SUBJECT in lower_subject:
        return parse_debit_email(html, received_at)

    return None
