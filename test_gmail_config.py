"""
Gmail SMTP Configuration Validator.

Quick test to verify Gmail SMTP connection before running full service.
This script validates:
1. Environment variables are set correctly
2. SMTP connection can be established
3. Authentication is successful
"""

import os
import smtplib
import sys
from typing import Tuple


def validate_env_vars() -> Tuple[bool, str]:
    """
    Check if all required environment variables are set.

    Returns:
        (success: bool, message: str)
    """
    required_vars = ['SMTP_HOST', 'SMTP_PORT', 'FROM_EMAIL', 'PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        return False, f"Missing environment variables: {', '.join(missing)}"

    return True, "All environment variables configured ✅"


def validate_smtp_connection() -> Tuple[bool, str]:
    """
    Test SMTP connection and authentication.

    Returns:
        (success: bool, message: str)
    """
    try:
        smtp_host = os.getenv('SMTP_HOST', '')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        from_email = os.getenv('FROM_EMAIL', '')
        password = os.getenv('PASSWORD', '')

        # Create SMTP connection
        smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=10)

        # Start TLS (standard for port 587)
        smtp.starttls()

        # Authenticate
        smtp.login(from_email, password)

        # Test message (not sent)
        print(f"  ✓ Connected to {smtp_host}:{smtp_port}")
        print(f"  ✓ Authenticated as {from_email}")

        smtp.quit()

        return True, "SMTP connection successful ✅"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed: Invalid credentials ❌"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)} ❌"
    except Exception as e:
        return False, f"Connection error: {str(e)} ❌"


def validate_config_file() -> Tuple[bool, str]:
    """
    Check if config/alertas_email.yaml exists.

    Returns:
        (success: bool, message: str)
    """
    from pathlib import Path

    config_path = Path("config/alertas_email.yaml")

    if not config_path.exists():
        return False, f"Config file not found: {config_path} ❌"

    return True, f"Config file found: {config_path} ✅"


def validate_templates() -> Tuple[bool, str]:
    """
    Check if templates directory and alert_email.html exist.

    Returns:
        (success: bool, message: str)
    """
    from pathlib import Path

    template_file = Path("templates/alert_email.html")

    if not template_file.exists():
        return False, f"Template not found: {template_file} ❌"

    return True, f"Template found: {template_file} ✅"


def main() -> int:
    """
    Run all Gmail configuration validation checks.

    Returns:
        0 if all checks pass, 1 if any check fails
    """
    print("\n" + "="*60)
    print("🔧 GMAIL SMTP CONFIGURATION VALIDATOR")
    print("="*60)

    checks = [
        ("Environment Variables", validate_env_vars),
        ("Config File", validate_config_file),
        ("Templates", validate_templates),
        ("SMTP Connection", validate_smtp_connection),
    ]

    results = []

    for check_name, check_func in checks:
        print(f"\n📋 Checking {check_name}...")
        success, message = check_func()
        results.append((check_name, success))
        print(f"   {message}")

    # Summary
    print("\n" + "="*60)
    passed = sum(1 for _, success in results if success)
    total = len(results)

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("="*60 + "\n")
        return 0
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total})")
        print("\nFailed checks:")
        for name, success in results:
            if not success:
                print(f"  - {name}")
        print("="*60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
