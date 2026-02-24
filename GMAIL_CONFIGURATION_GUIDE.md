# 📧 CONFIGURAÇÃO EMAIL - GMAIL (PASSO-A-PASSO)

**Objetivo:** Configurar envio de emails via Gmail para alertas do Operador Quântico
**Serviço:** Gmail SMTP
**Tipo de Autenticação:** App Password (Seguro)
**Tempo:** 10 minutos

---

## 1️⃣ CRIAR APP PASSWORD NO GMAIL (5 minutos)

### Pré-requisitos:
- ✅ Email Gmail ativo
- ✅ Autenticação 2-Fatores **ativada** (obrigatório!)

### Passo-a-Passo:

**PASSO 1:** Acesse Google Account
- Vá para: https://myaccount.google.com
- Faça login com seu email do Gmail

**PASSO 2:** Navegue até "Segurança"
- Menu esquerdo → "Segurança" (Security)
- Se não vê 2FA, ative primeiro:
  - "Verificação em duas etapas" → Siga passos

**PASSO 3:** Crie App Password
- Em "Como você faz login no Google" → "Senhas de app"
- "Selecione app" → "Correio" (Mail)
- "Selecione dispositivo" → "Windows/Mac/Linux"
- Google gera uma **senha de 16 caracteres**

**EXEMPLO DE APP PASSWORD GERADO:**
```
abcd efgh ijkl mnop
(sem espaços na prática: abcdefghijklmnop)
```

**⚠️ IMPORTANTE:**
- Copie e guarde essa senha em local seguro
- Não compartilhe com ninguém
- Use APENAS para esta aplicação

---

## 2️⃣ CRIAR ARQUIVO .env (2 minutos)

**Arquivo:** `.env` (na raiz do projeto)

```bash
# ============================================================
# EMAIL CONFIGURATION - GMAIL SMTP
# ============================================================

# Gmail SMTP Server
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Seu email do Gmail
FROM_EMAIL=seu_email@gmail.com

# App Password gerado no Google
PASSWORD=abcdefghijklmnop

# Email de destino (notificações)
ALERT_EMAIL=seu_email@gmail.com

# Configurações opcionais
EMAIL_NAME="Operador Quantico"
EMAIL_TIMEOUT=10
EMAIL_MAX_RETRIES=3
```

**⚠️ NUNCA commitar .env para Git:**
```bash
# Arquivo .gitignore (já deveria existir)
.env
.env.local
*.password
secrets/
```

---

## 3️⃣ CONFIGURAR alertas_email.yaml

**Arquivo:** `config/alertas_email.yaml`

```yaml
email:
  smtp:
    # Gmail SMTP configuration
    host: ${SMTP_HOST:smtp.gmail.com}          # Lê do .env, default: smtp.gmail.com
    port: ${SMTP_PORT:587}                     # Lê do .env, default: 587 (TLS)
    from_email: ${FROM_EMAIL}                  # Lê do .env (obrigatório)
    password: ${PASSWORD}                      # Lê do .env (obrigatório - App Password)

    # TLS Configuration (para port 587)
    use_tls: true                              # ✅ SEMPRE true para Gmail
    use_ssl: false                             # ❌ false (TLS já fornece segurança)

    timeout: ${EMAIL_TIMEOUT:10}               # Timeout em segundos

  sender:
    name: ${EMAIL_NAME:Operador Quantico}      # Nome do remetente
    email: ${FROM_EMAIL}                       # Email do remetente (mesmo que from_email)

  recipient:
    alert_email: ${ALERT_EMAIL}                # Email para receber alertas

  retry:
    max_attempts: ${EMAIL_MAX_RETRIES:3}       # Tentativas se falhar
    backoff_seconds: [1, 2, 4]                 # Exponential: 1s, 2s, 4s

  rate_limit:
    max_per_minute: 60                         # Máximo 60 emails/minuto
    cooldown_seconds: 1

# Logging
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

---

## 4️⃣ PYTHON - CÓDIGO DE TESTE

**Arquivo:** `test_gmail_config.py` (na raiz)

```python
#!/usr/bin/env python3
"""
Teste de configuração Gmail SMTP
Verifica se a conexão está funcionando
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

def test_gmail_connection():
    """Testa conexão com Gmail SMTP"""

    # Lê variáveis de ambiente
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    FROM_EMAIL = os.getenv('FROM_EMAIL')
    PASSWORD = os.getenv('PASSWORD')

    print("=" * 60)
    print("🔍 TESTE DE CONFIGURAÇÃO GMAIL SMTP")
    print("=" * 60)

    # Validação básica
    if not FROM_EMAIL:
        print("❌ ERRO: FROM_EMAIL não configurado no .env")
        return False

    if not PASSWORD:
        print("❌ ERRO: PASSWORD não configurado no .env")
        return False

    print(f"✅ SMTP_HOST: {SMTP_HOST}")
    print(f"✅ SMTP_PORT: {SMTP_PORT}")
    print(f"✅ FROM_EMAIL: {FROM_EMAIL}")
    print(f"✅ PASSWORD: {'*' * len(PASSWORD)}")

    try:
        print("\n📡 Conectando ao Gmail SMTP...")

        # Cria conexão SMTP com TLS
        smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        print(f"✅ Conexão estabelecida")

        # Inicia TLS
        print("🔒 Iniciando TLS...")
        smtp.starttls()
        print("✅ TLS ativado")

        # Faz login
        print(f"🔑 Autenticando com {FROM_EMAIL}...")
        smtp.login(FROM_EMAIL, PASSWORD)
        print("✅ Autenticação bem-sucedida!")

        # Fecha conexão
        smtp.quit()
        print("\n✅ CONEXÃO GMAIL TESTADA COM SUCESSO!")
        print("=" * 60)
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ ERRO DE AUTENTICAÇÃO:")
        print("   - Email ou App Password incorretos")
        print("   - Verifique se 2FA está ativado no Google")
        print("   - Regenere o App Password e tente novamente")
        return False

    except smtplib.SMTPException as e:
        print(f"❌ ERRO SMTP: {str(e)}")
        return False

    except Exception as e:
        print(f"❌ ERRO GERAL: {str(e)}")
        return False

def send_test_email():
    """Envia email de teste"""

    FROM_EMAIL = os.getenv('FROM_EMAIL')
    PASSWORD = os.getenv('PASSWORD')
    ALERT_EMAIL = os.getenv('ALERT_EMAIL', FROM_EMAIL)

    print("\n" + "=" * 60)
    print("📧 ENVIANDO EMAIL DE TESTE")
    print("=" * 60)

    try:
        # Cria email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "✅ Teste Email - Operador Quântico"
        msg['From'] = FROM_EMAIL
        msg['To'] = ALERT_EMAIL

        # Conteúdo em HTML
        html = """
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #1a1a1a;">✅ Teste de Email Bem-Sucedido!</h2>
                <p>Se você recebeu este email, a configuração do Gmail SMTP está <strong>funcionando corretamente</strong>.</p>

                <div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #51cf66;">
                    <p><strong>Detalhes do Teste:</strong></p>
                    <ul>
                        <li>📧 De: {from_email}</li>
                        <li>📬 Para: {to_email}</li>
                        <li>⏰ Hora: {timestamp}</li>
                    </ul>
                </div>

                <p>Você está pronto para receber alertas do Operador Quântico! 🚀</p>

                <hr>
                <p style="color: #999; font-size: 0.9em;">
                    Mensagem automática gerada por Operador Quântico v1.1
                </p>
            </body>
        </html>
        """

        from datetime import datetime
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        html = html.format(
            from_email=FROM_EMAIL,
            to_email=ALERT_EMAIL,
            timestamp=timestamp
        )

        msg.attach(MIMEText(html, 'html'))

        # Envia email
        print(f"📤 Enviando para {ALERT_EMAIL}...")
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.starttls()
        smtp.login(FROM_EMAIL, PASSWORD)
        smtp.sendmail(FROM_EMAIL, [ALERT_EMAIL], msg.as_string())
        smtp.quit()

        print("✅ EMAIL ENVIADO COM SUCESSO!")
        print(f"   Verifique sua caixa de entrada em {ALERT_EMAIL}")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ ERRO AO ENVIAR: {str(e)}")
        return False

if __name__ == "__main__":
    # Testa conexão
    if test_gmail_connection():
        # Se conexão OK, tenta enviar email de teste
        send_test_email()
    else:
        print("\n❌ Falha na conexão. Verifique .env e tente novamente.")
```

**Executar teste:**
```bash
python test_gmail_config.py
```

---

## 5️⃣ ESTRUTURA DE PASTAS

Após configurar, seu projeto deve ter:

```
operador-day-trade-win/
├── .env                              ← Suas credenciais Gmail
├── .gitignore                        ← Com .env adicionado
├── config/
│   └── alertas_email.yaml            ← Configuração YAML
├── templates/
│   └── alert_email.html              ← Template do email
├── src/
│   └── application/
│       └── services/
│           └── email_service.py      ← Serviço de email
├── tests/
│   └── test_email_service.py         ← Testes unitários
└── test_gmail_config.py              ← Teste de conexão
```

---

## 6️⃣ TROUBLESHOOTING

### ❌ Erro: "Username and Password not accepted"

**Causa:** Usando senha normal do Gmail, não App Password

**Solução:**
1. Ative 2FA no Google Account
2. Vá em https://myaccount.google.com/apppasswords
3. Selecione "Mail" e "Windows/Mac/Linux"
4. Copie a senha de 16 caracteres
5. Cole em PASSWORD no .env

### ❌ Erro: "SMTP connection timeout"

**Causa:** Firewall bloqueando porta 587

**Solução:**
- Tente port 465 (SSL) em vez de 587 (TLS)
- Mude `SMTP_PORT=465` no .env
- Mude `use_tls: false` → `use_ssl: true` no YAML

### ❌ Erro: "530 5.7.0 Authentication required"

**Causa:** 2FA não está ativado no Gmail

**Solução:**
1. Acesse https://myaccount.google.com/security
2. Ative "Verificação em duas etapas"
3. Depois crie o App Password

### ❌ Email vai para Spam

**Motivo:** Gmail é rigoroso com remetentes

**Solução:**
- Envie um email do Gmail para você mesmo para marcar como "Confiável"
- Configure SPF/DKIM (se usar domínio customizado)
- Use template HTML bem formatado (feito ✅)

---

## 7️⃣ VARIÁVEIS DE AMBIENTE - RESUMO

**Arquivo `.env`:**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
FROM_EMAIL=seu_email@gmail.com
PASSWORD=suaasenha16caracteres
ALERT_EMAIL=seu_email@gmail.com
EMAIL_NAME=Operador Quantico
EMAIL_TIMEOUT=10
EMAIL_MAX_RETRIES=3
```

**Código para carregar:**
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Carrega .env
email = os.getenv('FROM_EMAIL')
password = os.getenv('PASSWORD')
```

---

## 8️⃣ CHECKLIST FINAL

```
✅ Passo 1: App Password gerado no Google
✅ Passo 2: .env criado com credenciais
✅ Passo 3: alertas_email.yaml configurado
✅ Passo 4: test_gmail_config.py rodou com sucesso
✅ Passo 5: Email de teste recebido
✅ Passo 6: .gitignore protege .env
✅ Passo 7: Email service pronto para usar
```

---

## 9️⃣ USAR NO CÓDIGO

Após configurado, use assim:

```python
from src.application.services.email_service import EmailService
import asyncio

# Initialize
email_service = EmailService("config/alertas_email.yaml")

# Send email
success = asyncio.run(email_service.send_email_with_retry(
    to_email="seu_email@gmail.com",
    subject="Alerta Volatilidade",
    action="BUY",
    symbol="WIN$N",
    price="194.50",
    timestamp="23/02/2026 14:30:00",
    pattern_type="Z-score >2σ",
    confidence=85,
    volatility="2.1σ",
    rsi=75,
    volume="1.2M",
    recommendation="Compra conservadora com SL",
    timestamp_iso="2026-02-23T14:30:00Z"
))

if success:
    print("✅ Email enviado com sucesso!")
else:
    print("❌ Falha ao enviar email após 3 tentativas")
```

---

## 🔟 SEGURANÇA - BOAS PRÁTICAS

```
✅ FAÇA:
  - Use App Password (não senha normal)
  - Guarde .env em lugar seguro
  - Não commit .env para Git
  - Regenere App Password mensalmente
  - Use variáveis de ambiente em produção

❌ NUNCA FAÇA:
  - Hardcode credenciais no código
  - Compartilhe App Password
  - Commit .env para repositório público
  - Use senha normal do Gmail
  - Reutilize passwords entre serviços
```

---

## 📞 SUPORTE

Se tiver dúvidas:
1. Verifique logs em `test_gmail_config.py`
2. Confirme App Password no Google Account
3. Teste manualmente a conexão SMTP
4. Escalate para CTO se problema persistir

---

**Configuração Gmail:** ✅ COMPLETA
**Pronto para usar:** ✅ SIM
**Tempo total:** ~10 minutos
**Segurança:** ✅ Ambiente variables (sem hardcode)

🎉 **Seus alertas do Operador Quântico agora vão via Email Gmail!**
