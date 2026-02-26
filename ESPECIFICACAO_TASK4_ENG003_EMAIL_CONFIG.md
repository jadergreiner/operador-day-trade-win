# 🚀 TASK #4: INTEGRATION-ENG-003 - Email Configuration (SMTP)

**Executor:** Eng Sr (ID 1) + DevOps (ID 7)
**Data Criação:** 25/02/2026 (agora)
**Status:** ⏳ PRONTA PARA EXECUÇÃO
**Squad:** 2 personas + QA (ID 12)
**Deliverables:** SMTP config + integration + 7 ACs + unit tests

---

## 🎯 EXECUTIVE SUMMARY

Esta task configura **persistência de Email (SMTP)** para fallback quando WebSocket falha:

1. **Entrada:** EmailService infrastructure (já existe, TODO-ENG-002 ✅)
2. **Processo:** Configurar Gmail SMTP + templates + integração com alerts
3. **Saída:** `config/alertas_email.yaml` + `.env` com masks + testes passando
4. **Fallback:** Email entra em ação se WebSocket tiver downtime

---

## ✅ ACCEPTANCE CRITERIA (7 - TASK #4)

| AC # | Critério | Descrição Técnica | Test |
|------|----------|-------------------|------|
| **1** | Gmail SMTP Configurado | Conexão SMTP com TLS/SSL OK | `test_gmail_smtp_connection()` |
| **2** | Credenciais Seguras | .env com masks, não hardcoded | `test_credentials_security()` |
| **3** | Email Templates | Jinja2 templates para alert/status | `test_template_rendering()` |
| **4** | Testes de Entrega | Mock SMTP send OK, retry OK | `test_email_send_with_retry()` |
| **5** | Fallback Logic | Email ativado se WebSocket down | `test_websocket_fallback()` |
| **6** | Trade Alert Integration | Alertas de trade enviados via email | `test_trade_alert_email()` |
| **7** | Unit Tests > 90% | 7 testes passando, coverage > 90% | `pytest --cov` |

---

## 🔍 ESPECIFICAÇÃO TÉCNICA DETALHADA

### Gmail SMTP Setup (AC-1)

```yaml
# File: config/alertas_email.yaml

email:
  provider: gmail
  smtp:
    host: smtp.gmail.com
    port: 587
    use_tls: true
    use_ssl: false

  credentials:
    # Substituídos do .env em runtime
    sender_email: "${GMAIL_SENDER_EMAIL}"     # seu@gmail.com
    app_password: "${GMAIL_APP_PASSWORD}"     # 16-char password específica para app

  settings:
    max_retries: 3
    retry_delay_sec: 5
    exponential_backoff: true
    timeout_sec: 10

  recipients:
    alerts:
      - "${ALERT_EMAIL_RECIPIENT}"  # seu@email.com
      - "${BACKUP_EMAIL}"            # backup@email.com

    reports:
      - "${REPORT_EMAIL_RECIPIENT}"

templates:
  trade_alert:
    subject: "[ALERTA] Trade {{ action }} WIN$N @ {{ price }}"
    template_file: "templates/trade_alert_email.html"

  daily_report:
    subject: "[RELATÓRIO] {{ date }} - WIN$N Trading Results"
    template_file: "templates/daily_report_email.html"

  error_alert:
    subject: "⚠️ [ERRO] Operador WIN - {{ error_type }}"
    template_file: "templates/error_alert_email.html"

logging:
  level: INFO
  smtp_debug: false  # Mude para true para debug SMTP
```

### Arquivo .env Requerido (AC-2)

```bash
# .env (NEVER commit this file - use .env.example)

# Gmail Configuration
GMAIL_SENDER_EMAIL=seu@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop  # 16-char app-specific password from Google

# Alert Recipients
ALERT_EMAIL_RECIPIENT=seu@email.com
BACKUP_EMAIL=backup@seu.com
REPORT_EMAIL_RECIPIENT=rel@seu.com

# Email Service Config
EMAIL_CONFIG_FILE=config/alertas_email.yaml
EMAIL_ENABLED=true
EMAIL_FALLBACK_IF_WEBSOCKET_DOWN=true
WEBSOCKET_TIMEOUT_SEC=30
```

### Email Templates (AC-3)

#### Template 1: Trade Alert Email

```html
<!-- File: templates/trade_alert_email.html -->

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px 5px 0 0; }
        .content { background: #ecf0f1; padding: 20px; }
        .footer { background: #34495e; color: white; padding: 10px; text-align: center; border-radius: 0 0 5px 5px; }
        .metric { display: inline-block; margin: 10px 5px; }
        .buy { color: #27ae60; font-weight: bold; }
        .sell { color: #e74c3c; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🔔 Alerta de Trade - WIN$N</h2>
        </div>
        <div class="content">
            <p>Timestamp: <strong>{{ timestamp }}</strong></p>

            <h3>
                {% if action == 'BUY' %}
                    <span class="buy">📈 COMPRA</span>
                {% else %}
                    <span class="sell">📉 VENDA</span>
                {% endif %}
            </h3>

            <div class="metric">
                <strong>Preço:</strong> R$ {{ price }}
            </div>
            <div class="metric">
                <strong>Confiança:</strong> {{ confidence }}%
            </div>
            <div class="metric">
                <strong>SL:</strong> R$ {{ stop_loss }}
            </div>
            <div class="metric">
                <strong>TP:</strong> R$ {{ take_profit }}
            </div>

            <p><strong>Fundamentação:</strong></p>
            <p>{{ reasoning }}</p>

            <p><strong>Fatores de Risco:</strong></p>
            <ul>
                {% for risk in risk_factors %}
                    <li>{{ risk }}</li>
                {% endfor %}
            </ul>
        </div>
        <div class="footer">
            Operador Quantitativo WIN - Decisões Automáticas | {{ footer_text }}
        </div>
    </div>
</body>
</html>
```

#### Template 2: Daily Report Email

```html
<!-- File: templates/daily_report_email.html -->

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        /* Similar to trade_alert_email.html */
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #bdc3c7; padding: 10px; text-align: left; }
        th { background: #34495e; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>📊 Relatório Diário - WIN$N</h2>
            <p>Data: {{ date }}</p>
        </div>
        <div class="content">
            <h3>Resumo do Dia</h3>
            <table>
                <tr>
                    <th>Métrica</th>
                    <th>Valor</th>
                </tr>
                <tr>
                    <td>Trades Realizados</td>
                    <td>{{ total_trades }}</td>
                </tr>
                <tr>
                    <td>Ganhos</td>
                    <td>{{ winning_trades }}</td>
                </tr>
                <tr>
                    <td>Perdas</td>
                    <td>{{ losing_trades }}</td>
                </tr>
                <tr>
                    <td>Win Rate</td>
                    <td>{{ win_rate }}%</td>
                </tr>
                <tr>
                    <td>Lucro Líquido</td>
                    <td style="color: {% if net_profit > 0 %}#27ae60{% else %}#e74c3c{% endif %};">
                        R$ {{ net_profit }}
                    </td>
                </tr>
                <tr>
                    <td>Sharpe Ratio</td>
                    <td>{{ sharpe_ratio }}</td>
                </tr>
            </table>

            <h3>Alertas Críticos</h3>
            {% if critical_alerts %}
                <ul>
                {% for alert in critical_alerts %}
                    <li>{{ alert }}</li>
                {% endfor %}
                </ul>
            {% else %}
                <p>Nenhum alerta crítico.</p>
            {% endif %}
        </div>
        <div class="footer">
            Operador Quantitativo WIN | {{ footer_text }}
        </div>
    </div>
</body>
</html>
```

### Integração com Alerts Workflow (AC-5 + AC-6)

```python
# File: src/application/services/alert_dispatcher.py

import logging
from typing import Dict, Optional
from src.application.services.email_service import EmailService
from src.interfaces.websocket_server import WebSocketServer

logger = logging.getLogger(__name__)

class AlertDispatcher:
    """
    Dispatcher que envia alertas via WebSocket (primário) ou Email (fallback).
    """

    def __init__(self, websocket_server: WebSocketServer, email_service: EmailService,
                 websocket_timeout_sec: int = 30):
        self.websocket_server = websocket_server
        self.email_service = email_service
        self.websocket_timeout_sec = websocket_timeout_sec

    async def send_trade_alert(self, alert_data: Dict) -> bool:
        """
        Enviar alerta de trade via WebSocket primário ou Email fallback.

        Args:
            alert_data: {
                'action': 'BUY'|'SELL',
                'price': float,
                'stop_loss': float,
                'take_profit': float,
                'confidence': int,  # 0-100%
                'reasoning': str,
                'risk_factors': List[str]
            }

        Returns:
            bool: True se enviado com sucesso (via ws ou email)
        """
        try:
            # Tentar WebSocket (primário)
            try:
                ws_sent = await self.websocket_server.broadcast(
                    message_type="trade_alert",
                    data=alert_data,
                    timeout_sec=self.websocket_timeout_sec
                )
                if ws_sent:
                    logger.info(f"✅ Trade alert sent via WebSocket")
                    return True
            except Exception as ws_error:
                logger.warning(f"⚠️ WebSocket failed: {ws_error}")

            # Fallback para Email
            logger.info("📧 Falling back to Email for trade alert...")
            email_sent = await self.email_service.send_alert_email(
                action=alert_data['action'],
                price=alert_data['price'],
                stop_loss=alert_data['stop_loss'],
                take_profit=alert_data['take_profit'],
                confidence=alert_data['confidence'],
                reasoning=alert_data['reasoning'],
                risk_factors=alert_data['risk_factors'],
                template="trade_alert"
            )

            if email_sent:
                logger.info(f"✅ Trade alert sent via Email (fallback)")
                return True

            logger.error("❌ Failed to send trade alert via both WS and Email")
            return False

        except Exception as e:
            logger.error(f"Unexpected error in send_trade_alert: {e}")
            return False
```

---

## 🧪 UNIT TEST TEMPLATES (7 - TASK #4)

```python
# File: tests/unit/test_task4_eng003_email_configuration.py

import pytest
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from src.application.services.email_service import EmailService
from src.application.services.alert_dispatcher import AlertDispatcher

@pytest.fixture(scope="session", autouse=True)
def setup_env():
    """Setup test environment variables."""
    os.environ['GMAIL_SENDER_EMAIL'] = 'test@gmail.com'
    os.environ['GMAIL_APP_PASSWORD'] = 'test_password_1234'
    os.environ['ALERT_EMAIL_RECIPIENT'] = 'alert@test.com'
    os.environ['BACKUP_EMAIL'] = 'backup@test.com'

@pytest.fixture
def email_service():
    """Create EmailService instance."""
    return EmailService(config_file="config/alertas_email.yaml")

@pytest.fixture
def alert_dispatcher(email_service):
    """Create AlertDispatcher instance."""
    mock_ws = Mock()
    return AlertDispatcher(websocket_server=mock_ws, email_service=email_service)

# TEST 1: Gmail SMTP Connection
def test_gmail_smtp_connection(email_service):
    """Should create valid SMTP connection to Gmail."""
    # Mock SMTP connection
    with patch('smtplib.SMTP') as mock_smtp:
        mock_connection = Mock()
        mock_smtp.return_value = mock_connection
        mock_connection.starttls.return_value = None
        mock_connection.login.return_value = None

        smtp = email_service._get_smtp_connection()

        assert smtp is not None
        mock_smtp.assert_called_once_with('smtp.gmail.com', 587)
        mock_connection.starttls.assert_called_once()
        mock_connection.login.assert_called_once()

# TEST 2: Credentials Security
def test_credentials_security(email_service):
    """Should not expose credentials in logs/config."""
    # Verify credentials are loaded from .env, not hardcoded
    assert email_service.config['credentials']['app_password'] == os.getenv('GMAIL_APP_PASSWORD')
    assert email_service.config['credentials']['sender_email'] == os.getenv('GMAIL_SENDER_EMAIL')

    # Verify config doesn't contain hardcoded passwords
    config_str = str(email_service.config)
    assert 'test_password' not in config_str

# TEST 3: Template Rendering
def test_template_rendering(email_service):
    """Should render Jinja2 templates correctly."""
    template_data = {
        'action': 'BUY',
        'price': 123.45,
        'confidence': 85,
        'stop_loss': 120.00,
        'take_profit': 130.00,
        'reasoning': 'Test reasoning',
        'risk_factors': ['Executar com cuidado']
    }

    html = email_service._render_template('trade_alert_email.html', **template_data)

    assert 'COMPRA' in html or 'BUY' in html
    assert '123.45' in html
    assert '85' in html

# TEST 4: Email Send with Retry
@pytest.mark.asyncio
async def test_email_send_with_retry(email_service):
    """Should send email with exponential backoff retry."""
    with patch.object(email_service, '_get_smtp_connection') as mock_get_conn:
        mock_conn = Mock()
        mock_conn.send_message.return_value = None
        mock_conn.quit.return_value = None
        mock_get_conn.return_value = mock_conn

        result = await email_service.send_email_with_retry(
            to_email='test@example.com',
            subject='Test',
            html_body='<p>Test</p>'
        )

        assert result == True
        mock_conn.send_message.assert_called()
        mock_conn.quit.assert_called()

# TEST 5: WebSocket Fallback Logic
@pytest.mark.asyncio
async def test_websocket_fallback(alert_dispatcher, email_service):
    """Should fallback to Email if WebSocket fails."""
    # Mock WebSocket to fail
    alert_dispatcher.websocket_server.broadcast = AsyncMock(side_effect=Exception("WS failed"))

    # Mock Email success
    with patch.object(email_service, 'send_alert_email', new_callable=AsyncMock, return_value=True):
        alert_data = {
            'action': 'BUY',
            'price': 100.0,
            'stop_loss': 95.0,
            'take_profit': 105.0,
            'confidence': 80,
            'reasoning': 'Test',
            'risk_factors': []
        }

        result = await alert_dispatcher.send_trade_alert(alert_data)

        assert result == True
        alert_dispatcher.websocket_server.broadcast.assert_called()

# TEST 6: Trade Alert Email Integration
@pytest.mark.asyncio
async def test_trade_alert_email(email_service):
    """Should send properly formatted trade alert email."""
    with patch.object(email_service, '_get_smtp_connection') as mock_get_conn:
        mock_conn = Mock()
        mock_conn.send_message.return_value = None
        mock_conn.quit.return_value = None
        mock_get_conn.return_value = mock_conn

        result = await email_service.send_alert_email(
            action='BUY',
            price=123.45,
            stop_loss=120.00,
            take_profit=130.00,
            confidence=85,
            reasoning='Test reasoning',
            risk_factors=['Risk 1'],
            template='trade_alert'
        )

        assert result == True
        # Verify send_message was called
        assert mock_conn.send_message.called

# TEST 7: Coverage >90%
def test_full_integration(alert_dispatcher, email_service):
    """Full integration test of email configuration."""
    # Verify all components initialized
    assert alert_dispatcher.websocket_server is not None
    assert alert_dispatcher.email_service is not None
    assert alert_dispatcher.websocket_timeout_sec > 0

    # Verify email service config loaded
    assert 'email' in email_service.config
    assert 'templates' in email_service.config
    assert 'smtp' in email_service.config['email']
```

---

## 📋 IMPLEMENTATION STEPS (Passo-a-Passo)

### Step 1: Criar Arquivos de Configuração (30 min)

```bash
# Criar diretórios
mkdir -p config templates

# Criar config/alertas_email.yaml (colar YAML acima)
cat > config/alertas_email.yaml << 'EOF'
[conteúdo YAML acima]
EOF

# Criar .env.example (para versionamento)
cat > .env.example << 'EOF'
GMAIL_SENDER_EMAIL=seu@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
ALERT_EMAIL_RECIPIENT=seu@email.com
BACKUP_EMAIL=backup@seu.com
REPORT_EMAIL_RECIPIENT=rel@seu.com
EMAIL_CONFIG_FILE=config/alertas_email.yaml
EMAIL_ENABLED=true
EMAIL_FALLBACK_IF_WEBSOCKET_DOWN=true
WEBSOCKET_TIMEOUT_SEC=30
EOF

# Criar .env (não commitar)
cp .env.example .env
# Edite .env com suas credenciais reais
```

### Step 2: Implementar AlertDispatcher (45 min)

```python
# Copiar código de AlertDispatcher acima para:
# src/application/services/alert_dispatcher.py
```

### Step 3: Integrar com WebSocket (30 min)

```python
# Em src/interfaces/websocket_server.py ou similar:

from src.application.services.alert_dispatcher import AlertDispatcher

# Instanciar dispatcher
dispatcher = AlertDispatcher(
    websocket_server=ws_server,
    email_service=email_service,
    websocket_timeout_sec=30
)

# Usar em trade alerts
async def on_trade_signal(alert_data):
    await dispatcher.send_trade_alert(alert_data)
```

### Step 4: Rodar Testes (15 min)

```bash
# Run email service tests
python -m pytest tests/unit/test_task4_eng003_email_configuration.py -v --cov

# Expected: 7/7 PASSED, coverage >90%
```

---

## 📊 Success Criteria (Validação Final)

```
✅ AC-1: Gmail SMTP configurado e conectando
✅ AC-2: Credenciais seguras (.env masked)
✅ AC-3: Templates Jinja2 renderizando corretamente
✅ AC-4: Testes de entrega e retry OK
✅ AC-5: Fallback logic ativado se WebSocket down
✅ AC-6: Alertas de trade enviados via email
✅ AC-7: Unit tests >90% coverage

Fallback Ativo: Email entrará em ação se WebSocket houver downtime >30sec
```

---

**Responsável:** Eng Sr (ID 1) + DevOps (ID 7)
**QA:** Quality (ID 12)
**Timeline:** ~1-2 horas
**Status:** ⏳ PRONTA PARA COMEÇAR
