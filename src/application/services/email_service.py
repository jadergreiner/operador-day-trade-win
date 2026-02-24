"""
Email Service - Async email sending with retry logic and template rendering.
Supports Gmail SMTP with exponential backoff retry mechanism.
"""

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Optional

import yaml
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class EmailService:
    """
    Async email service with retry logic and Jinja2 template support.

    Features:
    - Gmail SMTP configuration with TLS/SSL
    - Exponential backoff retry (configurable attempts)
    - Jinja2 template rendering with environment variable substitution
    - Comprehensive logging and error handling
    """

    def __init__(self, config_file: str = "config/alertas_email.yaml") -> None:
        """
        Initialize email service with YAML configuration.

        Args:
            config_file: Path to YAML config file with email settings

        Raises:
            FileNotFoundError: If config file not found
            yaml.YAMLError: If config file is invalid YAML
        """
        if not Path(config_file).exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            self.config: Dict = yaml.safe_load(f)

        # Substitute environment variables in config
        self._substitute_env_vars()

        # Initialize Jinja2 template environment
        template_dir = Path("templates").absolute()
        if not template_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {template_dir}")

        self.jinja_env: Environment = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )

        logger.info(f"EmailService initialized with config: {config_file}")

    def _substitute_env_vars(self) -> None:
        """
        Substitute environment variables in config (${VAR_NAME} format).

        This allows sensitive data to be loaded from .env without hardcoding.
        """
        def substitute(value: any) -> any:
            """Recursively substitute ${VAR} with environment variable values."""
            if isinstance(value, str):
                # Check if string contains ${...} pattern
                if '${' in value and '}' in value:
                    import re
                    pattern = r'\$\{([^}]+)\}'

                    def replace_var(match):
                        var_name = match.group(1)
                        env_value = os.getenv(var_name)
                        if env_value is None:
                            raise ValueError(f"Environment variable not found: {var_name}")
                        return env_value

                    return re.sub(pattern, replace_var, value)
                return value
            elif isinstance(value, dict):
                return {k: substitute(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute(v) for v in value]
            return value

        self.config = substitute(self.config)

    def _get_smtp_connection(self) -> smtplib.SMTP:
        """
        Create and authenticate SMTP connection.

        Returns:
            Authenticated SMTP connection instance

        Raises:
            smtplib.SMTPException: If connection or authentication fails
        """
        cfg = self.config['email']['smtp']

        try:
            # Create SMTP connection based on SSL/TLS config
            if cfg.get('use_ssl', False):
                smtp = smtplib.SMTP_SSL(
                    cfg['host'],
                    int(cfg['port']),
                    timeout=int(cfg.get('timeout', 10))
                )
            else:
                smtp = smtplib.SMTP(
                    cfg['host'],
                    int(cfg['port']),
                    timeout=int(cfg.get('timeout', 10))
                )

                if cfg.get('use_tls', True):
                    smtp.starttls()

            # Authenticate
            smtp.login(cfg['from_email'], cfg['password'])
            logger.debug(f"SMTP connection established to {cfg['host']}:{cfg['port']}")

            return smtp

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {str(e)}")
            raise
        except smtplib.SMTPException as e:
            logger.error(f"SMTP connection error: {str(e)}")
            raise

    def _render_template(
        self,
        template_name: str,
        **template_vars: any
    ) -> str:
        """
        Render Jinja2 template with provided variables.

        Args:
            template_name: Name of template file in templates/ directory
            **template_vars: Variables to inject into template

        Returns:
            Rendered HTML string

        Raises:
            jinja2.TemplateNotFound: If template not found
            jinja2.TemplateSyntaxError: If template has syntax errors
        """
        try:
            template = self.jinja_env.get_template(template_name)
            html = template.render(**template_vars)
            logger.debug(f"Template {template_name} rendered successfully")
            return html
        except Exception as e:
            logger.error(f"Template rendering error: {str(e)}")
            raise

    async def send_email_with_retry(
        self,
        to_email: str,
        subject: str,
        template_name: str = "alert_email.html",
        **template_vars: any
    ) -> bool:
        """
        Send email with exponential backoff retry mechanism.

        Attempts to send email up to max_attempts times. If initial attempt fails,
        waits exponentially longer between retries (e.g., 1s, 2s, 4s).

        Args:
            to_email: Recipient email address
            subject: Email subject line
            template_name: Name of HTML template file to render
            **template_vars: Variables for template rendering

        Returns:
            True if email sent successfully, False if all retries exhausted

        Example:
            >>> service = EmailService()
            >>> success = await service.send_email_with_retry(
            ...     to_email="trader@example.com",
            ...     subject="Alerta Volatilidade",
            ...     action="BUY",
            ...     symbol="WIN$N",
            ...     price="194.50",
            ...     timestamp="23/02/2026 14:30:00"
            ... )
        """
        cfg = self.config['email']['retry']
        max_attempts: int = cfg['max_attempts']
        backoff_seconds: list = cfg['backoff_seconds']

        for attempt in range(1, max_attempts + 1):
            try:
                # Render HTML template
                html_body = self._render_template(template_name, **template_vars)

                # Create email message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.config['email']['sender']['email']
                msg['To'] = to_email

                # Attach HTML body
                msg.attach(MIMEText(html_body, 'html'))

                # Send email
                smtp = self._get_smtp_connection()
                try:
                    smtp.sendmail(
                        self.config['email']['sender']['email'],
                        [to_email],
                        msg.as_string()
                    )
                finally:
                    smtp.quit()

                logger.info(
                    f"Email sent successfully to {to_email} "
                    f"(attempt {attempt}/{max_attempts})"
                )
                return True

            except Exception as e:
                logger.warning(
                    f"Email send attempt {attempt}/{max_attempts} failed: {str(e)}"
                )

                # If not last attempt, wait and retry
                if attempt < max_attempts:
                    wait_time = backoff_seconds[attempt - 1]
                    logger.info(
                        f"Retrying in {wait_time}s... "
                        f"({max_attempts - attempt} retries remaining)"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Email send failed after {max_attempts} attempts. "
                        f"Last error: {str(e)}"
                    )
                    return False

        return False

    async def send_alert_email(
        self,
        to_email: Optional[str] = None,
        **alert_data: any
    ) -> bool:
        """
        Send alert email using alert_email.html template.

        Convenience method that uses alert-specific template and config.

        Args:
            to_email: Recipient email (defaults to ALERT_EMAIL config)
            **alert_data: Alert variables (action, symbol, price, etc.)

        Returns:
            True if email sent successfully
        """
        if to_email is None:
            to_email = os.getenv('ALERT_EMAIL', '')
            if not to_email:
                logger.error("No recipient email provided and ALERT_EMAIL not set")
                return False

        return await self.send_email_with_retry(
            to_email=to_email,
            subject=f"Alerta: {alert_data.get('action', 'AÇÃO')} - {alert_data.get('symbol', 'ATIVO')}",
            template_name="alert_email.html",
            **alert_data
        )


# Example usage:
if __name__ == "__main__":
    import sys

    async def test_email():
        """Test email service (requires proper .env setup)"""
        service = EmailService()

        success = await service.send_email_with_retry(
            to_email="test@example.com",
            subject="Teste Alerta Quantico",
            action="BUY",
            symbol="WIN$N",
            price="194.50",
            timestamp="23/02/2026 14:30:00",
            pattern_type="Volatilidade Z-score",
            confidence=85,
            volatility="2.1σ",
            rsi=75,
            volume="1.2M",
            signal_strength=92,
            recommendation="Compra conservadora com SL 194.00",
            timestamp_iso="2026-02-23T14:30:00Z",
            alert_class="success"
        )

        if success:
            print("✅ Email sent successfully")
            sys.exit(0)
        else:
            print("❌ Email send failed")
            sys.exit(1)

    asyncio.run(test_email())
