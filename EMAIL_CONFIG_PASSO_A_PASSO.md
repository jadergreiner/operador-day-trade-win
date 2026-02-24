# 🔴 EMAIL CONFIG - PASSO-A-PASSO PARA LIBERAR (TODAY 17:00 BRT)

**Propósito:** Liberar versão v1.1 (Alertas) para Beta 13/03
**Owner:** Eng Sr
**Deadline:** TODAY 23/02 17:00 BRT ⏰
**Esforço:** 1-2 horas
**Blocker:** SIM - Atrasa Beta se não completar TODAY

---

## 🎯 O QUE FAZER (5 COMPONENTES)

### 1️⃣ SMTP Configuration (30 minutos)

**Arquivo a criar:** `config/alertas_email.yaml`

```yaml
email:
  smtp:
    host: ${SMTP_HOST}          # env var
    port: ${SMTP_PORT}          # env var (587 ou 465)
    from_email: ${FROM_EMAIL}   # env var
    password: ${PASSWORD}       # env var - NUNCA hardcode
    use_tls: true              # para port 587
    use_ssl: false             # para port 465, muda para true
    timeout: 10

  sender:
    name: "Operador Quântico"
    email: ${FROM_EMAIL}

  retry:
    max_attempts: 3
    backoff_seconds: [1, 2, 4]  # Exponential: 1s, 2s, 4s

  rate_limit:
    max_per_minute: 60
    cooldown_seconds: 1
```

**AC-1 Requirements:**
- ✅ Arquivo criado com todas keys
- ✅ Env vars referencias (não hardcoded)
- ✅ Test connection: `python -c "import smtplib; smtplib.SMTP(...)"`

---

### 2️⃣ HTML Template (15 minutos)

**Arquivo a criar:** `templates/alert_email.html`

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alerta Quantico</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; }
        .header { background: #1a1a1a; color: white; padding: 15px; text-align: center; }
        .content { padding: 20px 0; }
        .alert-box {
            border-left: 5px solid #ff6b6b;
            padding: 15px;
            background: #fff5f5;
            margin: 15px 0;
        }
        .success { border-left-color: #51cf66; background: #f1fdf4; }
        .info { border-left-color: #4c6ef5; background: #f0f4ff; }
        .metric { display: inline-block; margin: 10px 15px; }
        .label { font-weight: bold; color: #666; }
        .value { font-size: 1.2em; color: #1a1a1a; }
        .footer { text-align: center; color: #999; font-size: 0.9em; padding-top: 20px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Alerta Quantico</h1>
        </div>

        <div class="content">
            <div class="alert-box {{ alert_class }}">
                <h2>{{ action }} - {{ symbol }}</h2>
                <p><strong>Preço:</strong> {{ price }}</p>
                <p><strong>Timestamp:</strong> {{ timestamp }}</p>
                <p><strong>Padrão:</strong> {{ pattern_type }}</p>
                <p><strong>Confiança:</strong> {{ confidence }}%</p>
            </div>

            <div>
                <h3>Métricas:</h3>
                <div class="metric">
                    <div class="label">Volatilidade (σ):</div>
                    <div class="value">{{ volatility }}</div>
                </div>
                <div class="metric">
                    <div class="label">RSI:</div>
                    <div class="value">{{ rsi }}</div>
                </div>
                <div class="metric">
                    <div class="label">Volume:</div>
                    <div class="value">{{ volume }}</div>
                </div>
            </div>

            <hr>

            <p><strong>Recomendação:</strong> {{ recommendation }}</p>
        </div>

        <div class="footer">
            <p>Gerado por Operador Quântico | {{ timestamp_iso }}</p>
        </div>
    </div>
</body>
</html>
```

**AC-2 Requirements:**
- ✅ Template renderiza sem erros (usar Jinja2)
- ✅ Variáveis: `{{ action }}`, `{{ symbol }}`, `{{ price }}`, `{{ timestamp }}`, etc.
- ✅ Responsivo mobile

---

### 3️⃣ Retry Logic + Service (20 minutos)

**Arquivo a criar:** `src/application/services/email_service.py`

```python
import asyncio
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from typing import Optional
import os

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, config_file: str = "config/alertas_email.yaml"):
        """Initialize email service with YAML config"""
        import yaml
        with open(config_file) as f:
            self.config = yaml.safe_load(f)
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates")
        )

    def _get_smtp_connection(self):
        """Create SMTP connection (SSL or TLS)"""
        cfg = self.config['email']['smtp']

        if cfg.get('use_ssl'):
            smtp = smtplib.SMTP_SSL(cfg['host'], cfg['port'])
        else:
            smtp = smtplib.SMTP(cfg['host'], cfg['port'])
            if cfg.get('use_tls'):
                smtp.starttls()

        smtp.login(cfg['from_email'], cfg['password'])
        return smtp

    def _render_template(self, template_name: str, **kwargs) -> str:
        """Render Jinja2 template with variables"""
        template = self.jinja_env.get_template(template_name)
        return template.render(**kwargs)

    async def send_email_with_retry(
        self,
        to_email: str,
        subject: str,
        template_name: str = "alert_email.html",
        **template_vars
    ) -> bool:
        """Send email with exponential backoff retry (3x)"""

        cfg = self.config['email']['retry']
        max_attempts = cfg['max_attempts']
        backoff_seconds = cfg['backoff_seconds']

        for attempt in range(1, max_attempts + 1):
            try:
                # Render template
                html_body = self._render_template(template_name, **template_vars)

                # Create email
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.config['email']['sender']['email']
                msg['To'] = to_email

                msg.attach(MIMEText(html_body, 'html'))

                # Send
                smtp = self._get_smtp_connection()
                smtp.sendmail(
                    self.config['email']['sender']['email'],
                    [to_email],
                    msg.as_string()
                )
                smtp.quit()

                logger.info(f"Email sent successfully to {to_email}")
                return True

            except Exception as e:
                logger.warning(f"Email send attempt {attempt} failed: {str(e)}")

                if attempt < max_attempts:
                    wait_time = backoff_seconds[attempt - 1]
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Email send failed after {max_attempts} attempts")
                    return False

# Exemplo de uso:
# email_service = EmailService()
# success = asyncio.run(email_service.send_email_with_retry(
#     to_email="trader@example.com",
#     subject="Alerta Volatilidade",
#     action="BUY",
#     symbol="WIN$N",
#     price="194.50",
#     timestamp="23/02/2026 14:30:00"
# ))
```

**AC-3 Requirements:**
- ✅ Retries 3x em caso de falha
- ✅ Exponential backoff: 1s → 2s → 4s
- ✅ Logging em cada tentativa (`logger.warning`, `logger.info`)

---

### 4️⃣ Unit Tests (30 minutos)

**Arquivo a criar:** `tests/test_email_service.py`

```python
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from src.application.services.email_service import EmailService

@pytest.fixture
def email_service():
    return EmailService("config/alertas_email.yaml")

@pytest.mark.asyncio
async def test_email_send_success(email_service):
    """AC-4.1: Email sent successfully"""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value = mock_instance

        result = await email_service.send_email_with_retry(
            to_email="test@example.com",
            subject="Test",
            action="BUY",
            symbol="WIN$N",
            price="194.50",
            timestamp="23/02/2026 14:30:00"
        )

        assert result == True
        mock_instance.sendmail.assert_called_once()

@pytest.mark.asyncio
async def test_email_retry_on_failure(email_service):
    """AC-4.2: Retries on failure (3x with backoff)"""
    with patch('smtplib.SMTP') as mock_smtp:
        # Fail 2x, succeed on 3rd
        mock_smtp.side_effect = [
            Exception("Connection failed"),
            Exception("Timeout"),
            MagicMock()
        ]

        result = await email_service.send_email_with_retry(
            to_email="test@example.com",
            subject="Test",
            action="BUY",
            symbol="WIN$N",
            price="194.50",
            timestamp="23/02/2026 14:30:00"
        )

        assert result == True
        assert mock_smtp.call_count == 3  # Called 3 times

@pytest.mark.asyncio
async def test_invalid_smtp_credentials(email_service):
    """AC-4.3: Handle invalid credentials"""
    with patch('smtplib.SMTP.login') as mock_login:
        mock_login.side_effect = Exception("Invalid credentials")

        result = await email_service.send_email_with_retry(
            to_email="test@example.com",
            subject="Test",
            action="BUY",
            symbol="WIN$N",
            price="194.50",
            timestamp="23/02/2026 14:30:00"
        )

        assert result == False  # Finally fails

def test_template_rendering(email_service):
    """AC-4.4: Template renders correctly"""
    html = email_service._render_template(
        "alert_email.html",
        action="BUY",
        symbol="WIN$N",
        price="194.50",
        timestamp="23/02/2026 14:30:00",
        pattern_type="Volatilidade Z-score",
        confidence=85,
        volatility="2.1σ",
        rsi=75,
        volume="1.2M",
        recommendation="Compra conservadora com SL",
        timestamp_iso="2026-02-23T14:30:00Z"
    )

    assert "WIN$N" in html
    assert "194.50" in html
    assert "BUY" in html

def test_config_from_env(email_service):
    """AC-4.5: Config loaded from environment variables"""
    import os
    os.environ['SMTP_HOST'] = 'smtp.gmail.com'
    os.environ['SMTP_PORT'] = '587'
    os.environ['FROM_EMAIL'] = 'bot@example.com'
    os.environ['PASSWORD'] = 'secret'

    assert email_service.config['email']['smtp']['host'] == 'smtp.gmail.com'
    # Cleanup
    for key in ['SMTP_HOST', 'SMTP_PORT', 'FROM_EMAIL', 'PASSWORD']:
        if key in os.environ:
            del os.environ[key]
```

**AC-4 Requirements:**
- ✅ test_email_send_success: Email enviado ✅
- ✅ test_email_retry_on_failure: Retries 3x ✅
- ✅ test_invalid_smtp_credentials: Falha gracefully ✅
- ✅ test_template_rendering: Template renderiza ✅
- ✅ test_config_from_env: Env vars carregadas ✅

**Run tests:**
```bash
pytest tests/test_email_service.py -v
pytest tests/test_email_service.py --cov=src.application.services.email_service
# Coverage deve ser >90%
```

---

### 5️⃣ Code Quality Validation (5 minutos)

**AC-5 Requirements:**

```bash
# 1️⃣ Type hints - 100%
# Adicione type hints em TODAS as functions:
def send_email_with_retry(...) -> bool:  # ✅ Tem return type
async def send_email_with_retry(...) -> bool:  # ✅ Async também

# 2️⃣ Coverage >90%
pytest tests/test_email_service.py --cov=src/application/services/email_service --cov-report=term-missing
# Saída esperada: TOTAL 95%

# 3️⃣ mypy --strict
mypy src/application/services/email_service.py --strict
# Expected: Success

# 4️⃣ UTF-8 Verified
file -i src/application/services/email_service.py
# Expected: charset=utf-8
```

---

## 📋 EXECUÇÃO PASSO-A-PASSO (1h50min total)

```
00:00 - 00:05 ... Design phase (review specs)
00:05 - 00:35 ... SMTP config implementation
00:35 - 00:50 ... HTML template creation
00:50 - 01:10 ... Email service + retry logic
01:10 - 01:40 ... Unit tests (5 test cases)
01:40 - 01:50 ... Code quality validation
01:50 - END   ... Git commit + merge
```

**Timeline:**
- Comece AGORA (sugestão: 14:00 BRT)
- Pronto para merge: ~15:50 BRT
- Buffer até deadline: 1h10min ✅

---

## 🆗 ACCEPTANCE CRITERIA - FINAL CHECKLIST

### AC-1: SMTP Configuration ✅
- [ ] `config/alertas_email.yaml` criado
- [ ] Env vars: SMTP_HOST, SMTP_PORT, FROM_EMAIL, PASSWORD
- [ ] SSL/TLS configurado (port 587 ou 465)
- [ ] Test connection passou

### AC-2: Email Template ✅
- [ ] `templates/alert_email.html` criado
- [ ] Todas variáveis Jinja2 presentes
- [ ] Renderiza sem erros
- [ ] Mobile responsive (meta viewport + CSS)

### AC-3: Retry Mechanism ✅
- [ ] Retries 3x em caso de SMTP failure
- [ ] Exponential backoff: 1s, 2s, 4s
- [ ] Logging em cada tentativa
- [ ] Finally falha gracefully após 3 retries

### AC-4: Unit Tests ✅
- [ ] test_email_send_success() passa ✅
- [ ] test_email_retry_on_failure() passa ✅
- [ ] test_invalid_smtp_credentials() passa ✅
- [ ] test_template_rendering() passa ✅
- [ ] test_config_from_env() passa ✅
- [ ] Coverage >90%

### AC-5: Code Quality ✅
- [ ] 100% type hints (todas functions + return types)
- [ ] Coverage >90%
- [ ] mypy --strict OK
- [ ] UTF-8 verified (no broken chars)

---

## 💾 GIT COMMIT (Final Step)

```bash
# Create feature branch
git checkout -b feature/email-config-phase6

# Stage files
git add config/alertas_email.yaml
git add templates/alert_email.html
git add src/application/services/email_service.py
git add tests/test_email_service.py

# Commit with proper message (PORTUGUESE!)
git commit -m "feat: Email configuration para alertas automáticos - SMTP + template + retry logic + tests

- SMTP configuration with env vars (no hardcoded credentials)
- HTML Jinja2 template for alert delivery
- Retry mechanism with exponential backoff (3x, 1s-2s-4s)
- 5 unit tests with >90% coverage
- 100% type hints + mypy --strict OK
- Desbloqueia Beta 13/03"

# Push & create PR
git push origin feature/email-config-phase6
```

**Commit será:** feat: Email configuration para alertas automáticos...

---

## ✅ SUCCESS = LIBERA

Se TODOS os 5 AC passarem ✅:

```
🟢 Email config READY for Beta 13/03
🟢 Can merge to main
🟢 Amanhã checkpoint pode dar GO para Sprint 1
🟢 v1.1 vai para staging deployment
🟢 Primeira milha do projeto cumprida! 🚀
```

---

## ❌ BLOCKER - Se ALGUM AC falhar:

```
PARE e FIX:
1. Identifique qual AC falhou
2. Fix imediatamente
3. Rerun todos tests
4. NÃO merge até todos AC passarem
5. Se não conseguir: ESCALATE para CTO
```

---

**Owner:** Eng Sr
**Deadline:** TODAY 23/02 17:00 BRT ⏰
**Impacto:** Desbloqueia Beta 13/03 + Checkpoint 24/02 09:00
**Prioridade:** 🔴 CRÍTICA - BLOCKER

---

Precisa de ajuda? Chama o CTO ou ML Expert para pair programming! 🤝

Você está pronto? LET'S GO! 🚀
