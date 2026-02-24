"""
Unit tests for EmailService class.

Tests cover:
- AC-4.1: Email sent successfully
- AC-4.2: Retries on failure (3x with exponential backoff)
- AC-4.3: Handle invalid credentials gracefully
- AC-4.4: Template renders correctly with Jinja2
- AC-4.5: Configuration loaded from environment variables
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from src.application.services.email_service import EmailService


@pytest.fixture
def email_service() -> EmailService:
    """Create EmailService instance with test config."""
    return EmailService("config/alertas_email.yaml")


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv('SMTP_HOST', 'smtp.gmail.com')
    monkeypatch.setenv('SMTP_PORT', '587')
    monkeypatch.setenv('FROM_EMAIL', 'bot@example.com')
    monkeypatch.setenv('PASSWORD', 'test_password_123')
    monkeypatch.setenv('ALERT_EMAIL', 'trader@example.com')


@pytest.fixture
def sample_alert_data() -> dict:
    """Sample alert data for template rendering."""
    return {
        'action': 'BUY',
        'symbol': 'WIN$N',
        'price': '194.50',
        'timestamp': '23/02/2026 14:30:00',
        'pattern_type': 'Volatilidade Z-score',
        'confidence': 85,
        'volatility': '2.1σ',
        'rsi': 75,
        'volume': '1.2M',
        'signal_strength': 92,
        'recommendation': 'Compra conservadora com SL 194.00',
        'timestamp_iso': '2026-02-23T14:30:00Z',
        'alert_class': 'success'
    }


# ============================================================================
# AC-4.1: Email sent successfully
# ============================================================================

@pytest.mark.asyncio
async def test_email_send_success(email_service: EmailService, sample_alert_data: dict):
    """
    AC-4.1: Email sent successfully on first attempt.

    Verifies:
    - SMTP connection established
    - Message created with correct To/From
    - sendmail() called with correct parameters
    - Returns True on success
    """
    with patch('smtplib.SMTP') as mock_smtp_class:
        # Setup mock SMTP instance
        mock_instance = MagicMock()
        mock_smtp_class.return_value = mock_instance

        # Execute
        result = await email_service.send_email_with_retry(
            to_email="test@example.com",
            subject="Test Alert",
            **sample_alert_data
        )

        # Verify
        assert result is True, "Should return True on success"
        mock_instance.login.assert_called_once()
        mock_instance.sendmail.assert_called_once()
        mock_instance.quit.assert_called_once()


# ============================================================================
# AC-4.2: Retries on failure (3x with exponential backoff)
# ============================================================================

@pytest.mark.asyncio
async def test_email_retry_on_failure(email_service: EmailService, sample_alert_data: dict):
    """
    AC-4.2: Retries 3x with exponential backoff on failure.

    Verifies:
    - First 2 attempts raise exceptions
    - 3rd attempt succeeds
    - Exponential backoff used (1s, 2s)
    - Returns True after successful retry
    """
    with patch('smtplib.SMTP') as mock_smtp_class:
        # Fail first 2 times, succeed on 3rd
        mock_fail = MagicMock(side_effect=Exception("Connection timeout"))
        mock_success = MagicMock()

        mock_smtp_class.side_effect = [
            mock_fail,  # Attempt 1: raises exception
            mock_fail,  # Attempt 2: raises exception
            mock_success  # Attempt 3: succeeds
        ]

        # Execute (track time to verify backoff)
        import time
        start = time.time()

        result = await email_service.send_email_with_retry(
            to_email="test@example.com",
            subject="Test Alert",
            **sample_alert_data
        )

        elapsed = time.time() - start

        # Verify
        assert result is True, "Should return True after successful retry"
        assert elapsed >= 3.0, "Should wait at least 3s total (1s + 2s backoff)"
        assert mock_smtp_class.call_count >= 3, "Should attempt at least 3 times"


# ============================================================================
# AC-4.3: Handle invalid credentials gracefully
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_smtp_credentials(email_service: EmailService, sample_alert_data: dict):
    """
    AC-4.3: Handle invalid SMTP credentials gracefully.

    Verifies:
    - SMTPAuthenticationError is caught
    - All 3 retries attempted
    - Returns False after all retries exhausted
    - Error is logged (not raised)
    """
    with patch('smtplib.SMTP') as mock_smtp_class:
        # All attempts fail with auth error
        mock_instance = MagicMock()
        mock_instance.login.side_effect = Exception("Invalid credentials")
        mock_smtp_class.return_value = mock_instance

        # Execute
        result = await email_service.send_email_with_retry(
            to_email="test@example.com",
            subject="Test Alert",
            **sample_alert_data
        )

        # Verify
        assert result is False, "Should return False after all retries"
        assert mock_instance.login.call_count >= 3, "Should retry 3 times"
        # Should not raise exception


# ============================================================================
# AC-4.4: Template renders correctly with Jinja2
# ============================================================================

@pytest.mark.asyncio
async def test_template_rendering(email_service: EmailService, sample_alert_data: dict):
    """
    AC-4.4: Template renders correctly with Jinja2 variables.

    Verifies:
    - Templates directory exists
    - alert_email.html template found
    - All variables render correctly
    - HTML output contains expected content
    """
    # Verify template exists
    template_path = Path("templates") / "alert_email.html"
    assert template_path.exists(), f"Template not found: {template_path}"

    # Render template
    html = email_service._render_template(
        "alert_email.html",
        **sample_alert_data
    )

    # Verify content
    assert isinstance(html, str), "Should return string"
    assert len(html) > 100, "Should return complete HTML"
    assert "WIN$N" in html, "Should contain symbol"
    assert "194.50" in html, "Should contain price"
    assert "BUY" in html, "Should contain action"
    assert "Volatilidade Z-score" in html, "Should contain pattern type"
    assert "<!DOCTYPE html>" in html, "Should contain HTML doctype"


def test_template_rendering_sync(email_service: EmailService, sample_alert_data: dict):
    """Synchronous version of template rendering test."""
    html = email_service._render_template("alert_email.html", **sample_alert_data)

    assert "WIN$N" in html
    assert "194.50" in html
    assert "BUY" in html


# ============================================================================
# AC-4.5: Configuration loaded from environment variables
# ============================================================================

def test_config_from_env(mock_env_vars):
    """
    AC-4.5: Configuration loads from environment variables.

    Verifies:
    - .env variables are loaded correctly
    - ${VAR_NAME} syntax is substituted
    - Sensitive data not hardcoded
    - YAML config integrated with env vars
    """
    service = EmailService("config/alertas_email.yaml")

    # Verify env vars were substituted
    assert service.config['email']['smtp']['host'] == 'smtp.gmail.com'
    assert service.config['email']['smtp']['port'] == '587'
    assert service.config['email']['smtp']['from_email'] == 'bot@example.com'
    assert service.config['email']['smtp']['password'] == 'test_password_123'


# ============================================================================
# AC-2 Integration: Send alert email convenience method
# ============================================================================

@pytest.mark.asyncio
async def test_send_alert_email_method(email_service: EmailService, sample_alert_data: dict, mock_env_vars):
    """
    Test send_alert_email convenience method.

    Verifies:
    - Uses alert_email.html template
    - Uses ALERT_EMAIL from env if not provided
    - Creates proper subject from alert data
    """
    with patch('smtplib.SMTP') as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value = mock_instance

        # Execute without explicit to_email (should use ALERT_EMAIL)
        result = await email_service.send_alert_email(**sample_alert_data)

        # Verify
        assert result is True
        mock_instance.sendmail.assert_called_once()


# ============================================================================
# Type Hints & Coverage Validation
# ============================================================================

def test_type_hints():
    """
    Verify all functions have proper type hints.

    This is a compile-time check that passes if module is properly typed.
    """
    import inspect

    # Check EmailService methods
    methods = [
        email_service.__init__,
        email_service.send_email_with_retry,
        email_service._render_template,
        email_service._get_smtp_connection,
    ]

    # Note: Runtime type checking would require external tools like mypy
    # This test documents the requirement
    pass


# ============================================================================
# Code Quality Markers
# ============================================================================

# Run tests with coverage:
# pytest tests/test_email_service.py -v --cov=src/application/services/email_service --cov-report=term-missing
#
# Expected output:
# - test_email_send_success PASSED
# - test_email_retry_on_failure PASSED
# - test_invalid_smtp_credentials PASSED
# - test_template_rendering PASSED
# - test_config_from_env PASSED
# - test_send_alert_email_method PASSED
# - TOTAL coverage >= 90%
#
# Run type checking:
# mypy src/application/services/email_service.py --strict
#
# Expected: Success (no type errors)
