# ⚙️ Configuração Paralela - Dois Agentes com Estratégias Distintas

**Data:** 16/03/2026
**Status:** ✅ Implementado
**Objetivo:** Operar dois agentes em paralelo, cada um com estratégia de SL/TP diferente

---

## 📋 Resumo da Mudança

### Antes
- Um único agente rodava com SL/TP fixo OU dinâmico
- Não havia diferenciacão entre qual agente abriu a posição

### Agora
- **2 agentes autônomos** rodando em paralelo
- Cada um com **estratégia SL/TP própria**
- **Posições diferenciadas** no banco de dados
- **Logs identificam** qual agente fez cada operação

---

## 🎯 Configuração de Cada Agente

### **Agente 1: DINAMICO**
```batch
INICIAR_AGENTE_RL_5000.bat
└─ Opção [2]
```

**Características:**
- ✅ SL/TP **DINÂMICO** (adapta aos topos/fundos)
- ✅ Analisa últimas 20 velas
- ✅ Garante RR mínimo = 1:1.5
- ✅ Mais **adaptativo** ao mercado
- 📊 Modo: `dinamico`

**Comando direto:**
```bash
python scripts/operar_novo_agente_rl_real_antiovertrading.py --sl-tp-mode dinamico
```

---

### **Agente 2: FIXO**
```batch
INICIAR_AGENTE_RL_DIRETO.bat
```

**Características:**
- ✅ SL/TP **FIXO** (150/300 pontos)
- ✅ **Previsível** e sem complexidade
- ✅ Rápido de executar
- ✅ Perfeito para **roboadas rápidas**
- 📊 Modo: `fixo`

**Comando direto:**
```bash
python scripts/agente_com_supervision.py --sl-tp-mode fixo
```

---

## 🚀 Como Rodar em Paralelo

### Opção 1: Dois Terminais (Recomendado)

**Terminal 1: Agente DINÂMICO**
```bash
cd c:\repo\operador-day-trade-win
INICIAR_AGENTE_RL_5000.bat
# Escolha opção [2]
```

**Terminal 2: Agente FIXO**
```bash
cd c:\repo\operador-day-trade-win
INICIAR_AGENTE_RL_DIRETO.bat
```

**Resultado:**
- Ambos rodando **simultaneamente**
- Cada um gerencia suas próprias posições
- Logs separados: `outputs/agente_supervision.log`
- P&L combinado ou separado per agente

---

### Opção 2: Batch Jobs (Windows Task Scheduler)

**Tarefa 1: Agente DINÂMICO**
```batch
Program: cmd.exe
Arguments: /c "C:\repo\operador-day-trade-win\INICIAR_AGENTE_RL_5000.bat"
Start in: C:\repo\operador-day-trade-win
Trigger: 09:00 (horário de abertura)
```

**Tarefa 2: Agente FIXO**
```batch
Program: cmd.exe
Arguments: /c "C:\repo\operador-day-trade-win\INICIAR_AGENTE_RL_DIRETO.bat"
Start in: C:\repo\operador-day-trade-win
Trigger: 09:05 (5 min depois)
```

---

## 📊 Diferenciação no Banco de Dados

Cada operação é registrada com:

```
[ENVIO] Enviando: Comprar @ 103.800 (SL: 103.180, TP: 104.530, Vol: 0.100%)
        [Agente: agente_dinamico_20260316_100530, Modo: DINAMICO]

[ENVIO] Enviando: Vender @ 104.200 (SL: 104.350, TP: 103.900, Vol: 0.100%)
        [Agente: agente_fixo_20260316_101015, Modo: FIXO]
```

### ID Único do Agente

```python
AGENTE_ID = f"agente_{SL_TP_MODE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
# Exemplo: agente_dinamico_20260316_100530
```

**Valor:**
- ✅ Diferencia qual agente abriu cada posição
- ✅ Permite rastrear estratégia por operação
- ✅ Facilita análise de desempenho isolado

---

## 📈 Exemplo de Execução Paralela

```
09:00:00 → AGENTE DINAMICO inicia
09:00:05 → MT5 conectado (DINAMICO)
09:00:10 → Modelo RL carregado (DINAMICO)
09:00:15 → [CICLO 1] DINAMICO começando

09:05:00 → AGENTE FIXO inicia
09:05:05 → MT5 conectado (FIXO)
09:05:10 → Modelo RL carregado (FIXO)
09:05:15 → [CICLO 1] FIXO começando

09:10:00 → [CICLO 2] DINAMICO
          [DINAMICO] Topos/Fundos últimas 20 velas: Topo=104.500, Fundo=103.200
          [DINAMICO] SL/TP calculados: SL=103.180, TP=104.730
          [ENVIO] Enviando: Comprar @ 103.800 [Agente: agente_dinamico_..., Modo: DINAMICO]

09:10:05 → [CICLO 2] FIXO
          [FIXO] Usando SL/TP fixo para Comprar
          [ENVIO] Enviando: Comprar @ 103.750 [Agente: agente_fixo_..., Modo: FIXO]

09:15:00 → [PROGRESSO] DINAMICO: [=====----- +120.50 / 140.00 (86.1%)]
09:15:02 → [PROGRESSO] FIXO: [====------ +100.00 / 140.00 (71.4%)]

09:20:00 → [TARGET] ATINGIDO (DINAMICO): R$140.50 - ENCERRANDO
          [FIXO] Continuando... P&L: +R$105.00
```

---

## 🔍 Monitoramento

### Logs Separados

Ambos agentes escrevem no **mesmo arquivo** mas com tags identificáveis:

```
outputs/agente_supervision.log

2026-03-16 09:00:00 [INFO] [DINAMICO] Modo SL/TP: DINAMICO
2026-03-16 09:00:00 [INFO] [DINAMICO] ID do Agente: agente_dinamico_20260316_090000
2026-03-16 09:05:00 [INFO] [FIXO] Modo SL/TP: FIXO
2026-03-16 09:05:00 [INFO] [FIXO] ID do Agente: agente_fixo_20260316_090500
```

### Dashboard de Status

```bash
# Terminal 3: Monitorar ambos
Get-Content outputs/agente_supervision.log -Wait -Tail 50
```

Você verá alternadamente:
```
[DINAMICO] [CICLO X] ...
[FIXO] [CICLO Y] ...
[DINAMICO] [CICLO X+1] ...
```

---

## 🎯 Estratégias Recomendadas

### Cenário 1: Scalping

- **FIXO:** Roboadas rápidas (SL 150 pts, TP 300 pts)
- **DINAMICO:** Buffer maior, protege ganhos progressivos
- **Resultado:** Captura movimento rápido + proteção estratégica

### Cenário 2: Day Trading

- **FIXO:** Operações horárias (SL/TP fixo)
- **DINAMICO:** Posições trend (adapta à volatilidade)
- **Resultado:** Diversificação de horizonte temporal

### Cenário 3: Testagem

- **FIXO:** Estratégia conservadora (testa segurança)
- **DINAMICO:** Estratégia agressiva (testa potencial)
- **Resultado:** A/B testing automatizado

---

## ⚠️ Gestão de Risco

### Cada agentetem seus próprios limites:

```python
TARGET_LUCRO_DIARIO = 140.00        # Meta individual
STOP_PERDA_DIARIA = -250.00        # Stop individual
COOLDOWN_SECONDS = 300              # 5 min independente de qual agente
```

### Risk Total = DINAMICO + FIXO

```
Agente DINAMICO: Max Loss = -250
Agente FIXO: Max Loss = -250
────────────────────────────
RISCO TOTAL: -500 por dia
```

**Recomendação:** Monitorar P&L combinado. Se atingir -300, pausar um deles.

---

## 🔧 Troubleshooting

| Problema | Solução |
|----------|---------|
| Dois agentes usando mesma posição | Cada um tem `AGENTE_ID` único - MT5 controla separação |
| Conflito de SL/TP | Dinâmico ajusta independente, Fixo mantém valor |
| Perda muito rápida | Pausar um agente temporariamente |
| Logs misturados | Procurar por `[DINAMICO]` ou `[FIXO]` nos logs |
| Terminal fechou | Verificar `outputs/agente_supervision.log` para erro |

---

## 📝 Próximos Passos

### Fase 1: Validação (Hoje)
- [ ] Rodar DINAMICO por 1 hora
- [ ] Rodar FIXO por 1 hora
- [ ] Verificar logs

### Fase 2: Paralelo (Amanhã)
- [ ] Rodar ambos simultaneamente
- [ ] Monitorar P&L individual
- [ ] Validar backslash de posições

### Fase 3: Produção (Semana Próx)
- [ ] Configurar Task Scheduler
- [ ] Alertas de P&L
- [ ] Dashboard de monitoramento em tempo real

---

## 📞 Referências

**Modo DINAMICO:**
- Baseado em: `calcular_sl_tp_dinamico()`
- Referência: Últimas 20 velas
- Vantagem: Adaptabilidade

**Modo FIXO:**
- Baseado em: Valores pré-configurados (150/300)
- Referência: Padronizado
- Vantagem: Previsibilidade

**Agente ID:**
- Formato: `agente_{modo}_{timestamp}`
- Uso: Rastreamento em banco de dados
- Granularidade: Até segundos

---

**Status:** ✅ Pronto para uso em paralelo
**Commit:** [Hash do commit que implementou isso]
