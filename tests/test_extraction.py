import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extraction.structured_extractor import extract_structured_data


class TestDataExtraction:
    """Test suite for contract data extraction."""

    def test_extract_effective_date(self):
        """Test extracting effective date."""
        text = """
        This agreement is effective as of January 1, 2024.
        The parties agree to the following terms...
        """

        result = extract_structured_data(text)

        assert result["effective_date"] is not None
        assert "2024" in result["effective_date"]

    def test_extract_expiry_date(self):
        """Test extracting expiry date."""
        text = """
        This agreement shall expire on December 31, 2025.
        After which the agreement is null and void.
        """

        result = extract_structured_data(text)

        assert result["expiry_date"] is not None
        assert "2025" in result["expiry_date"]

    def test_extract_party_names(self):
        """Test extracting party names."""
        text = """
        This agreement is between Party 1: ABC Corporation
        and Party 2: XYZ Limited for the provision of services.
        """

        result = extract_structured_data(text)

        assert result["party_1_name"] is not None
        assert "ABC Corporation" in result["party_1_name"]
        assert result["party_2_name"] is not None
        assert "XYZ Limited" in result["party_2_name"]

    def test_extract_service_type(self):
        """Test extracting service type."""
        text = """
        Services to be provided: Consulting services including
        strategic planning and implementation support.
        """

        result = extract_structured_data(text)

        assert result["service_type"] is not None
        assert "Consulting" in result["service_type"]

    def test_extract_payment_basis(self):
        """Test extracting payment basis."""
        text = """
        Payment: Monthly invoicing at the rate of $5,000 per month.
        Invoices due within 30 days.
        """

        result = extract_structured_data(text)

        assert result["payment_basis"] is not None
        assert "Monthly" in result["payment_basis"]

    def test_extract_no_dates_found(self):
        """Test extraction when no dates are present."""
        text = """
        This is a simple agreement without specific dates mentioned.
        The parties agree to work together.
        """

        result = extract_structured_data(text)

        # Should return None for dates
        assert result["effective_date"] is None or result["effective_date"] == ""
        assert result["expiry_date"] is None or result["expiry_date"] == ""

    def test_extract_multiple_date_formats(self):
        """Test extraction with different date formats."""
        text1 = "Effective date: 01/15/2024"
        text2 = "Start date: January 15, 2024"
        text3 = "Begins: 2024-01-15"

        result1 = extract_structured_data(text1)
        result2 = extract_structured_data(text2)
        result3 = extract_structured_data(text3)

        assert result1["effective_date"] is not None
        assert result2["effective_date"] is not None
        assert result3["effective_date"] is not None

    def test_extract_from_empty_text(self):
        """Test extraction from empty text."""
        result = extract_structured_data("")

        # Should not crash, should return dict with None values
        assert isinstance(result, dict)
        assert "effective_date" in result
        assert "party_1_name" in result

    def test_extract_case_insensitive(self):
        """Test that extraction is case-insensitive."""
        text_upper = "EFFECTIVE DATE: JANUARY 1, 2024"
        text_lower = "effective date: january 1, 2024"

        result_upper = extract_structured_data(text_upper)
        result_lower = extract_structured_data(text_lower)

        assert result_upper["effective_date"] is not None
        assert result_lower["effective_date"] is not None

    def test_extract_complex_contract(self):
        """Test extraction from a complex contract text."""
        text = """
        TRANSPORTATION SERVICE AGREEMENT

        This Agreement is made effective as of March 15, 2024

        BETWEEN:
        Party 1: Global Logistics Corp (the "Carrier")
        AND
        Party 2: TechCo Industries Ltd (the "Customer")

        1. SERVICES
        The Carrier agrees to provide transportation services including
        freight forwarding and logistics management.

        2. TERM
        This agreement shall remain in effect until December 31, 2026
        unless terminated earlier as per the terms herein.

        3. PAYMENT
        Payment shall be made on a monthly basis within 30 days
        of invoice date. Rate schedule attached as Appendix A.
        """

        result = extract_structured_data(text)

        # Verify all key fields were extracted
        assert result["effective_date"] is not None
        assert "2024" in result["effective_date"]

        assert result["expiry_date"] is not None
        assert "2026" in result["expiry_date"]

        assert result["party_1_name"] is not None
        assert result["party_2_name"] is not None

        assert result["service_type"] is not None

        assert result["payment_basis"] is not None
        assert "monthly" in result["payment_basis"].lower()
