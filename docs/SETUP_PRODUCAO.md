# Setup de Produção — Agente RL com Dados Reais MT5

## Objetivo

Configurar o script `treinar_novo_agente_rl.py` para treinar o
agente de Reinforcement Learning usando dados históricos reais
da conta MetaTrader 5 em produção.

---

## Pré-requisitos

- MetaTrader 5 instalado e aberto no Windows
- Conta ativa (real ou demo) na corretora
- Python 3.11+ com o pacote `MetaTrader5` instalado
- Arquivo `.env` configurado na raiz do projeto

---

## 1. Configurar o arquivo `.env`

Copie o arquivo de exemplo e preencha com suas credenciais:

```bash
cp .env.example .env
```

Edite o `.env` com as variáveis abaixo:

```env
# ── Agente RL — Credenciais MT5 ─────────────────────────────
MT5_LOGIN=123456
MT5_PASSWORD=sua_senha_aqui
MT5_SERVER=NomeDoServidor MT5
```

> **⚠️ Segurança:** Nunca commite o arquivo `.env`.
> Ele já está listado no `.gitignore`.

### Como encontrar o nome do servidor

1. Abra o MetaTrader 5
2. Menu **Arquivo → Conectar à Conta de Corretora**
3. O nome do servidor aparece na lista de conexões

Exemplos comuns (verifique o nome exato no seu MT5):

| Corretora | Servidor (exemplo) |
|-----------|---------|
| Clear | `Clear MT5 - Live` |
| XP Investimentos | `XPInvestimentos-PRD` |
| BTG Pactual | `BTGPactualCorretora-PRD` |
| Rico | `Rico-PRD` |

> **Nota:** Os nomes de servidor acima são exemplos e podem
> mudar. Confirme sempre o nome exato no menu
> **Arquivo → Conectar à Conta de Corretora** do seu MT5.

---

## 2. Instalar dependências

```bash
pip install MetaTrader5 python-dotenv
```

> `python-dotenv` é opcional. Sem ele, as variáveis de
> ambiente precisam ser exportadas manualmente.

---

## 3. Verificar conexão antes de treinar

Antes do treinamento, verifique se a conexão está funcionando:

```bash
python scripts/treinar_novo_agente_rl.py --dados-reais --episodios 1
```

Saída esperada ao conectar com sucesso:

```text
11:00:00 | INFO | Conectado ao MT5: conta 123456 em 'Clear MT5 - Live'
11:00:00 | INFO | Conta REAL | Saldo: R$10.000,00 | Margem livre: ...
11:00:00 | INFO | Dados MT5 carregados: 5000 candles de 'WIN$N'
```

---

## 4. Executar o treinamento

### Treinamento padrão com dados reais

```bash
python scripts/treinar_novo_agente_rl.py \
  --dados-reais \
  --episodios 500
```

### Avaliar modelo existente com dados reais

```bash
python scripts/treinar_novo_agente_rl.py \
  --dados-reais \
  --apenas-avaliar
```

### Treinamento com modelo personalizado

```bash
python scripts/treinar_novo_agente_rl.py \
  --dados-reais \
  --episodios 1000 \
  --modelo meu_modelo \
  --semente 123
```

---

## 5. Validações automáticas

O script executa automaticamente as seguintes validações
antes de baixar os dados:

| Validação | Critério | Ação se falhar |
|-----------|----------|----------------|
| Credenciais | `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` no `.env` | Erro |
| Terminal aberto | MT5 inicializa corretamente | Aviso + fallback |
| Login | Autenticação na corretora | Aviso + fallback |
| Saldo mínimo | `RL_SALDO_MINIMO` (padrão R$5.000) | Erro + instrução |
| Margem livre | >= 10% do saldo mínimo | Erro + instrução |
| Símbolo disponível | `WIN$N` visível no Market Watch | Aviso + fallback |
| Horário de mercado | Seg-Sex 9h-18h (Brasília) | Aviso (não bloqueia) |

> **Nota:** Falhas nas validações fazem o script recair
> automaticamente para dados sintéticos, sem interromper
> o fluxo de trabalho.

---

## 6. Troubleshooting

### Erro: "Terminal MT5 não encontrado"

**Causa:** O MetaTrader 5 não está aberto ou não está
acessível pelo Python.

**Solução:**
1. Abra o MetaTrader 5
2. Aguarde carregar completamente
3. Execute o script novamente

### Erro: "Falha no login MT5"

**Causa:** Credenciais incorretas ou servidor errado.

**Solução:**
1. Verifique `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` no `.env`
2. Confirme o nome exato do servidor no MT5
3. Teste o login manualmente no terminal MT5

### Erro: "Saldo insuficiente"

**Causa:** Saldo menor que R$5.000,00.

**Solução:**
- Use uma conta demo com saldo maior, ou
- Ajuste a constante `_SALDO_MINIMO_BRL` no script
  (não recomendado para produção)

### Erro: "Símbolo WIN$N não disponível"

**Causa:** O símbolo não está nos favoritos do MT5.

**Solução:**
1. No MT5, clique com o botão direito no Market Watch
2. Selecione **Símbolos**
3. Procure por `WIN$N` e clique em **Mostrar**
4. Execute o script novamente

### Aviso: "Pacote MetaTrader5 não instalado"

**Causa:** O pacote Python não foi instalado.

**Solução:**

```bash
pip install MetaTrader5
```

> **Nota:** O pacote `MetaTrader5` só funciona no Windows.
> Em outros sistemas operacionais, o script usará
> automaticamente dados sintéticos.

---

## 7. Segurança

- ✅ Credenciais lidas do `.env` (nunca expostas no log)
- ✅ Apenas o número da conta é exibido nos logs
- ✅ Senha mascarada em todas as mensagens de log
- ✅ `.env` no `.gitignore` (nunca vai para o repositório)
- ✅ Timeout padrão de 60 segundos nas conexões MT5

---

## 8. Referências

### Documentação CORE

- **Arquitetura & Design:** [ARCHITECTURE.md](ARCHITECTURE.md) | [ADRs.md](ADRs.md) | [DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md)
- **Dados & Modelos:** [DATA_MODELS.md](DATA_MODELS.md) | [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md) | [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md)
- **Regras & Padrões:** [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) | [CODING_STANDARDS.md](CODING_STANDARDS.md)
- **Contribuição:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Status & Tarefas:** [BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md) | [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md)

### Scripts & Exemplos

- [Script de treinamento](../scripts/treinar_novo_agente_rl.py)
- [Exemplo de .env](../.env.example)
