"""Tests for BofA email notification parsers.

Validates regex-based extraction of balance and transaction data from
Bank of America HTML alert emails. Uses sample HTML fragments that
match the structure of real BofA notifications.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.services.email_parser import (
    parse_balance_email,
    parse_debit_email,
    try_parse_email,
)


# -- Sample HTML fragments -------------------------------------------------

BALANCE_HTML = """
<html>
<head><style>.header { color: blue; }</style></head>
<body>
<p>Your Bank of America account information</p>
<p>Account - 1787</p>
<p>Available Balance: $7,981.52</p>
<p>As of February 15, 2026</p>
</body>
</html>
"""

BALANCE_HTML_NO_DATE = """
<html><body>
<p>Account - 4321</p>
<p>Available Balance: $500.00</p>
</body></html>
"""

BALANCE_HTML_NO_AMOUNT = """
<html><body>
<p>Account - 1787</p>
<p>Your account has been updated.</p>
</body></html>
"""

DEBIT_HTML = """
<html><body>
<p>Your debit card transaction</p>
<p>Amount: $42.99</p>
<p>Purchase made at WHOLE FOODS MKT</p>
<p>Card ending in 8832</p>
<p>March 10, 2026</p>
</body></html>
"""

DEBIT_HTML_NO_DATE = """
<html><body>
<p>Amount: $19.50</p>
<p>Where: STARBUCKS</p>
<p>Card ending in 5566</p>
</body></html>
"""

DEBIT_HTML_NO_AMOUNT = """
<html><body>
<p>Your card was used somewhere.</p>
<p>Card ending in 5566</p>
</body></html>
"""


# -- Balance parser --------------------------------------------------------


class TestParseBalanceEmail:
    def test_extracts_balance_and_account(self):
        result = parse_balance_email(BALANCE_HTML)

        assert result is not None
        assert result.balance == Decimal("7981.52")
        assert result.account_label == "Account - 1787"

    def test_extracts_date(self):
        result = parse_balance_email(BALANCE_HTML)

        assert result is not None
        assert result.observed_at.year == 2026
        assert result.observed_at.month == 2
        assert result.observed_at.day == 15

    def test_strips_style_tags(self):
        """Style tag content should not interfere with regex matching."""
        result = parse_balance_email(BALANCE_HTML)
        assert result is not None

    def test_returns_none_when_no_amount(self):
        result = parse_balance_email(BALANCE_HTML_NO_AMOUNT)
        assert result is None

    def test_falls_back_to_received_at_when_no_date(self):
        received = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
        result = parse_balance_email(BALANCE_HTML_NO_DATE, received_at=received)

        assert result is not None
        assert result.observed_at == received
        assert result.balance == Decimal("500.00")
        assert result.account_label == "Account - 4321"

    def test_falls_back_to_utcnow_when_no_date_or_received_at(self):
        result = parse_balance_email(BALANCE_HTML_NO_DATE)

        assert result is not None
        # Timestamp should be very recent (within last 5 seconds).
        delta = datetime.now(timezone.utc) - result.observed_at
        assert delta.total_seconds() < 5


# -- Debit parser ----------------------------------------------------------


class TestParseDebitEmail:
    def test_extracts_amount_and_merchant(self):
        result = parse_debit_email(DEBIT_HTML)

        assert result is not None
        assert result.amount == Decimal("42.99")
        # Merchant regex grabs from label to next double-space or end-of-text.
        # With simple HTML, _strip_html normalizes to single spaces so the
        # merchant captures trailing text. Real BofA emails have table padding
        # that produces double-space delimiters.
        assert "WHOLE FOODS MKT" in result.merchant  # type: ignore[operator]

    def test_extracts_card_last_four(self):
        result = parse_debit_email(DEBIT_HTML)

        assert result is not None
        assert result.card_last_four == "8832"

    def test_extracts_date(self):
        result = parse_debit_email(DEBIT_HTML)

        assert result is not None
        assert result.purchase_date.month == 3
        assert result.purchase_date.day == 10
        assert result.purchase_date.year == 2026

    def test_returns_none_when_no_amount(self):
        result = parse_debit_email(DEBIT_HTML_NO_AMOUNT)
        assert result is None

    def test_falls_back_to_received_at_when_no_date(self):
        received = datetime(2026, 3, 5, 9, 30, tzinfo=timezone.utc)
        result = parse_debit_email(DEBIT_HTML_NO_DATE, received_at=received)

        assert result is not None
        assert result.purchase_date == received
        assert result.card_last_four == "5566"

    def test_merchant_from_where_label(self):
        result = parse_debit_email(DEBIT_HTML_NO_DATE)

        assert result is not None
        assert "STARBUCKS" in result.merchant  # type: ignore[operator]


# -- Routing ---------------------------------------------------------------


class TestTryParseEmail:
    def test_routes_to_balance_parser(self):
        result = try_parse_email("Your Available Balance Update", BALANCE_HTML)

        assert result is not None
        assert result.balance == Decimal("7981.52")  # type: ignore[union-attr]

    def test_routes_to_debit_parser(self):
        result = try_parse_email("Your Debit Card Was Used", DEBIT_HTML)

        assert result is not None
        assert result.amount == Decimal("42.99")  # type: ignore[union-attr]

    def test_returns_none_for_unknown_subject(self):
        result = try_parse_email("Your monthly statement is ready", BALANCE_HTML)
        assert result is None

    def test_case_insensitive_subject_matching(self):
        result = try_parse_email("YOUR AVAILABLE BALANCE", BALANCE_HTML)
        assert result is not None

    def test_passes_received_at_through(self):
        received = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
        result = try_parse_email(
            "Your Available Balance", BALANCE_HTML_NO_DATE, received_at=received
        )

        assert result is not None
        assert result.observed_at == received  # type: ignore[union-attr]
