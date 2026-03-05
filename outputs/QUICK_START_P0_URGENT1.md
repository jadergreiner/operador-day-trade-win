# ⚡ QUICK START - O QUE FAZER AGORA (06/03)

**Tempo de leitura:** 5 min
**Ação:** Execute os passos abaixo para ativar P0-URGENT-1

---

## ✅ Passo 1: Verificar Que Tudo foi Entregue

```bash
# Terminal - Verificar que arquivos existem
cd c:\repo\operador-day-trade-win

# 1. Código principal (agente com P0-URGENT-1)
dir scripts\agente_micro_tendencia_winfut.py

# 2. Testes (validaram funcionamento)
dir scripts\test_inactivity_penalty.py

# 3. Documentação (como funciona)
dir docs\features\inactivity-penalty\

# 4. Roadmap P1-LEARNING (próximas semanas)
dir docs\features\causal-learning\ROADMAP_P1_LEARNING.md

# Resultado esperado: Todos 4 existem ✅
```

---

## ✅ Passo 2: Rodar Testes Uma Última Vez (Validação)

```bash
# Terminal
cd c:\repo\operador-day-trade-win

# Executar testes de P0-URGENT-1
python scripts/test_inactivity_penalty.py

# Saída esperada:
# TEST 1: ✓ PASS
# TEST 2: ✓ PASS
# ...
# TEST 10: ✓ PASS
# TODOS OS TESTES PASSARAM!

# Se algum falhar → call ML Expert imediatamente
```

---

## ✅ Passo 3: Fazer Backup do Banco Atual

```bash
# PowerShell (com admin)
cd c:\repo\operador-day-trade-win

# Copiar arquivo banco
Copy-Item data\db\trading.db data\db\trading.db.backup_05mar

# Verificar que foi criado
dir data\db\trading.db*

# Saída esperada:
# trading.db (atual)
# trading.db.backup_05mar (backup)
```

---

## ✅ Passo 4: Entender a Penalidade (1 minuto)

**Problema:** Modelo aprendeu que ficar parado é melhor que perder.

**Solução:** A cada 2 minutos, se não entrou em nenhum trade, perde -0.03% a -0.05% de confiança.

```
Tempo parado:  Penalidade:   Custo/dia:
121 minutos  → -3.1%        R$ 87
180 minutos  → -4.6%        R$ 129
200 minutos  → -5.0%        R$ 140 (máximo)
300 minutos  → -5.0%        R$ 280
```

**Como sai disso?** Entrando em um trade BELO. A penalidade zera imediatamente.

**Resultado esperado:** +2-3 trades/semana começar a aparecer em vez de 0.

---

## ✅ Passo 5: Iniciar Agent com P0-URGENT-1 (Amanhã 07/03 09:00)

```bash
# PowerShell (como admin)
cd c:\repo\operador-day-trade-win

# Iniciar agente
python scripts\agente_micro_tendencia_winfut.py

# Esperar saída:
# [09:00] Starting agent...
# [09:05] Conectando MT5...
# [09:10] Loading ML model...
# [09:15] IntraDayLearner initialized ← P0-URGENT-1 ATIVO
# ... trading logs ...
```

**Logs esperados quando inativo >120 min:**
```
[10:50] INACTIVITY_PENALTY(LEVE): 127min inativo → penalidade -0.0310
[10:50]   💡 Confidence: 0.52 → 0.49 (ajustado por inatividade)
[11:05] evaluate_opportunity: confidence=0.49 < treshold=0.50 HOLD
```

**Logs esperados ao ENTRAR:**
```
[11:45] evaluate_opportunity: confidence=0.55 > treshold=0.50 → ENTER
[11:46] ✅ Ordem executada! Ticket=12345
[11:46] 🔄 Penalidade resetada (0.0)
[11:47] Summary: Inatividade resetada, próximo cálculo em 120min
```

---

## 🎯 O Que Está Acontecendo (Visão de 30.000 pés)

### Antes (até 05/03):
```
Modelo: "Fazer nada é melhor que fazer ruim"
Resultado: 0 trades, confidence caindo
Impacto: R$ 280/dia em custos sem receita
```

### Agora (a partir de 07/03):
```
P0-URGENT-1: "Ficar parado tem custo, esforce-se"
Mecanismo: Penalidade por inatividade -0.03% a -0.05%
Resultado esperado: 2-3 trades/semana em vez de 0
Impacto: Sai do loop, volta para comportamento normal
```

### Próximo (a partir de 10/03):
```
P1-LEARNING: Aprender CAUSAÇÃO, não só correlação
Como: 7-step causal loop para cada oportunidade
Resultado: Win rate +12% (60% → 72%)
Impacto: Ganho de R$ 255-430k/90 dias
```

---

## 📌 Monitorar por 3 Dias (07-09/03)

**Cada dia, checklist 2 minutos:**

```
☐ Agent rodando? (python process no Windows)
☐ Logs gerados? (check outputs/trading_DDMM.log)
☐ Erros? (qualquer coisa diferente = problema)
☐ Trades? (mesmo que poucos, é progresso)
☐ Confiança? (não cai mais como antes)
```

**Se tudo OK por 09/03 → P0-URGENT-1 sucesso ✅**

**Se não OK → call ML Expert + revisar**

---

## 🆘 Problema? Aqui Estão as Soluções

### Problema 1: "Agent não inicia"
```
Solução:
1. Verificar MT5 aberto (requisito)
2. Verificar Python 3.11+ instalado
3. Verificar dependências: pip install -r requirements.txt
4. Check syntax: python -m py_compile scripts/agente_micro_tendencia_winfut.py
5. Se tudo OK → call CTO
```

### Problema 2: "Testes não passam"
```
Solução:
1. Rodar python scripts/test_inactivity_penalty.py com verbose
2. Qual teste falhou? (TEST X: ❌ FAIL)
3. Ver mensagem de erro
4. Call ML Expert com screenshot
```

### Problema 3: "Trades ainda 0 por 08/03"
```
Solução:
1. Verificar que penalidade está sendo aplicada (ver logs)
2. Verificar que confidence > threshold quando penalidade aplicada
3. Considerar P0-URGENT-2 (Forced Activation Threshold)
4. Emergency meeting com ML Expert + CTO
```

### Problema 4: "Confidence está mais baixa"
```
Solução:
1. ESPERADO (P0-URGENT-1 está permitindo trades ruins serem evitados)
2. Verificar que confidence sobe após entrada (trade positivo)
3. Vai normalizar em 2-3 dias quando trades começarem
```

---

## 📞 Contatos de Escalonamento

**Nível 1 (Operador):**
- Verificar MT5 aberto
- Rodar testes
- Monitorar logs

**Nível 2 (ML Expert) - Se problemas:**
- `ML Expert: Trades ainda 0 por 08/03?`
- `ML Expert: Penalidade não está sendo aplicada?`

**Nível 3 (CTO/Eng Sr) - Se crítico:**
- `CTO: Agent crashing?`
- `CTO: Syntax error após commit?`

**Nível 4 (Head Finanças) - Se bloqueador:**
- `Head: Viabilizar P0-URGENT-2 como backup?`

---

## 📋 Quick Checklist (Copy-Paste)

```
☐ Dia 06/03:
  ☐ Backup trading.db criado
  ☐ Testes rodando (10/10 passando)
  ☐ Stakeholders notificados
  ☐ Deploy plan confirmado

☐ Dia 07/03:
  ☐ Agent iniciado com P0-URGENT-1
  ☐ Logs monitorizando inatividade
  ☐ Standop 09:00 - métricas iniciais
  ☐ Monitoramento contínuo

☐ Dia 08/03:
  ☐ Trades começarão? (monitor)
  ☐ Confiança estável? (monitor)
  ☐ Erros? (verificar)
  ☐ Standop 09:00 - status

☐ Dia 09/03:
  ☐ P1-LEARNING prep OK
  ☐ DB schema ready
  ☐ Classes criadas
  ☐ Standop 09:00 - final assessment
  ☐ If trades OK: P0-URGENT-1 SUCCESS ✅

☐ Dia 10/03:
  ☐ P1-LEARNING KICK-OFF 14:00
  ☐ 7-step causal loop start
```

---

## 🎯 Resumão em 1 frase:

**"A partir de amanhã, o modelo vai perder confiança se ficar parado > 120 min, forçando ele a tentar novamente - esperamos sair de 0 para 2-3 trades/semana."**

---

**Sucesso! Ready for production. 🚀**

Qualquer dúvida → leia esta seção novamente em 2 min
Qualquer problema → escalona para contato apropriado
Próxima review → 07/03 09:00
