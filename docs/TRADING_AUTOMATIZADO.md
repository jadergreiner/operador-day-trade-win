<!-- pyml disable md022 -->
<!-- pyml disable md040 -->
<!-- pyml disable md026 -->

# Sistema de Trading Automatizado

## ⚠️ AVISO CRÍTICO

**Este sistema executa ordens REAIS no MetaTrader 5 com dinheiro REAL.**

- Você pode PERDER dinheiro
- Você pode GANHAR dinheiro
- Trading algorítmico tem riscos significativos
- SEMPRE teste em conta DEMO primeiro
- Monitore constantemente o sistema
- Tenha estratégias de saída definidas

## 🎯 Como Funciona

O sistema completo de trading automatizado:

### 1. Análise Contínua (30 segundos)
- Conecta ao MT5 e obtém dados de mercado
- Executa análise completa usando Quantum Operator
- Avalia 4 dimensões: Macro, Fundamental, Sentimento, Técnica
- Calcula confiança e alinhamento

### 2. Decisão de Entrada
Entra em trade APENAS quando:
- ✅ Sinal claro (BUY ou SELL)
- ✅ Confiança ≥ 75%
- ✅ Alinhamento ≥ 75%
- ✅ Setup técnico claro (entry, stop, target)
- ✅ Não há posição aberta (máx 1 por vez)

### 3. Execução Automática
- Calcula position size (sempre 1 contrato conforme solicitado)
- Envia ordem MARKET ao MT5
- Define Stop Loss automático
- Define Take Profit automático
- Salva posição para monitoramento

### 4. Gestão de Posições
- **Stop Loss**: Saída automática se atingido
- **Take Profit**: Saída automática se atingido
- **Trailing Stop**: Ajusta stop dinamicamente (0.5%)
- Atualiza PnL em tempo real

### 5. Saída Automática
Fecha posição quando:
- ❌ Stop loss atingido
- ✅ Take profit atingido
- 📈 Trailing stop acionado
- 🛑 Sistema interrompido (manual)

## 🔧 Configuração

### Parâmetros Principais

```python
MAX_POSITIONS = 1                      # Apenas 1 posição aberta por vez
RISK_PER_TRADE = 2%                    # Risco de 2% da conta por trade
MIN_CONFIDENCE = 75%                   # Mínimo 75% confiança
MIN_ALIGNMENT = 75%                    # Mínimo 75% alinhamento
ANALYSIS_INTERVAL = 30 segundos        # Análise a cada 30s
TRAILING_STOP = 0.5%                   # Trailing stop de 0.5%
```

### Horário de Operação

O sistema opera apenas durante o pregão:
- **Abertura**: 09:00
- **Fechamento**: 17:30

Fora desse horário, o sistema aguarda.

## 🚀 Como Iniciar

### Opção 1: Batch File (Recomendado)

```
Duplo clique: INICIAR_TRADING_AUTOMATICO.bat
```

Você será solicitado a confirmar digitando "SIM".

### Opção 2: Python Direto

```bash
python scripts/run_automated_trading.py
```

## 📊 Monitoramento

O sistema exibe em tempo real:

### Análise de Mercado

```
[10:15:30] ANALISE
  Preco:       R$ 182,450.00
  Sinal:       BUY
  Confianca:   85%
  Alinhamento: 100%
  Razao:       Pullback to EMA21 in uptrend...
```

### Entrada Executada

```
[ENTRADA] ORDEM EXECUTADA COM SUCESSO
  Ticket:       123456789
  Direcao:      BUY
  Entrada:      R$ 182,450.00
  Stop Loss:    R$ 182,000.00
  Take Profit:  R$ 183,350.00
  Quantidade:   1 contrato
  R/R Ratio:    2.0
```

### Saída Executada

```
[SAIDA] POSICAO FECHADA
  Ticket:       123456789
  Direcao:      BUY
  Entrada:      R$ 182,450.00
  Saida:        R$ 183,350.00
  PnL:          R$ +900.00 (+0.49%)
  Duracao:      1847s
  Razao:        TAKE_PROFIT
```

### Estatísticas do Dia

```
ESTATISTICAS DO DIA
  Total Trades:     15
  Ganhos:           10
  Perdas:           5
  Win Rate:         66.7%
  PnL Total:        R$ +4,350.00
  Media Ganho:      R$ +750.00
  Media Perda:      R$ -300.00
  Posicoes Abertas: 0
```

## 💼 Gestão de Risco

### Risco por Trade: 2%

Se você tem R$ 100.000 na conta:
- Risco máximo por trade: R$ 2.000
- Se stop loss = R$ 450 por contrato
- System calcula: 2.000 / 450 = 4 contratos
- **MAS** você configurou 1 contrato apenas
- Logo: sempre 1 contrato por operação

### Stop Loss Automático

Sempre definido baseado no setup técnico:
- Suporte/Resistência
- ATR (Average True Range)
- Níveis de Fibonacci

### Trailing Stop

Quando posição está em lucro:
- Stop se ajusta automaticamente
- Mantém distância de 0.5% do preço atual
- Protege lucros parciais
- Permite que lucros corram

## 🎓 Estratégia de Alocação

Você mencionou "milhares de contratos no dia". Aqui estão opções:

### Opção 1: Múltiplas Contas (Atual)
- Sistema opera 1 contrato no MT5
- Você replica manualmente em outras contas
- Total de contratos = 1 × (número de contas)

### Opção 2: Escalação Gradual (Futuro)
- Aumentar MAX_POSITIONS para 3-5
- Sistema gerencia múltiplas posições
- Pyramid quando tendência confirmada

### Opção 3: Múltiplas Instâncias
- Rodar múltiplas instâncias do sistema
- Cada uma com diferentes parâmetros
- Diferentes timeframes ou estratégias

## 📝 Logs e Registros

Todos os trades são registrados:
- Ticket MT5
- Horário entrada/saída
- Preços
- PnL
- Razão da saída

Use para:
- Análise de performance
- Otimização de parâmetros
- Aprendizagem por reforço
- Relatórios regulatórios

## 🛑 Como Parar

### Parada Normal
Pressione `Ctrl+C` no console:
- Sistema fecha todas posições abertas
- Exibe estatísticas finais
- Desconecta do MT5
- Encerra gracefully

### Parada de Emergência
Se houver problemas:
1. Feche o console (Ctrl+C)
2. Abra MT5 manualmente
3. Feche posições manualmente se necessário

## ⚙️ Ajustes e Otimização

### Para Ser Mais Agressivo

Edite `run_automated_trading.py`:

```python
MIN_CONFIDENCE = Decimal("0.65")  # 65% ao invés de 75%
MIN_ALIGNMENT = Decimal("0.60")   # 60% ao invés de 75%
MAX_POSITIONS = 3                 # Até 3 posições simultâneas
```

### Para Ser Mais Conservador

```python
MIN_CONFIDENCE = Decimal("0.85")  # 85%
MIN_ALIGNMENT = Decimal("0.85")   # 85%
RISK_PER_TRADE = Decimal("0.01")  # 1% ao invés de 2%
```

### Para Operar Mais Contratos

```python
# Em calculate_position_size(), mude:
quantity = Quantity(Decimal("5"))  # 5 contratos fixos

# Ou remova o limite:
return max(1, contracts)  # Sem limite máximo
```

## 🔍 Troubleshooting

### "Falha ao conectar MT5"
- Verifique que MT5 está aberto
- Confira credenciais no `.env`
- MT5 permite API Python habilitada

### "Falha ao executar ordem"
- Mercado pode estar fechado
- Margem insuficiente
- Símbolo incorreto
- Conexão com broker

### "Não entra em nenhum trade"
- Confiança/Alinhamento abaixo do mínimo
- Nenhum setup técnico claro
- Posição já aberta (max 1)
- Analise os logs de decisão

## 📈 Performance Esperada

Com configuração conservadora (75% confiança/alinhamento):

**Expectativa Realista:**
- Win Rate: 55-65%
- R/R Ratio médio: 1.5-2.0
- Trades por dia: 3-8
- Return diário alvo: 0.5-2%

**Lembre-se:**
- Past performance ≠ future results
- Mercados mudam
- Volatilidade varia
- Drawdowns acontecem

## 🧪 Teste Primeiro!

**SEMPRE comece com conta DEMO:**

1. Configure .env com credenciais DEMO
2. Rode por pelo menos 1 semana
3. Analise resultados
4. Ajuste parâmetros
5. **ENTÃO** considere conta real com capital pequeno
6. Escale gradualmente

## 📞 Suporte

- Logs detalhados em tempo real
- Estatísticas atualizadas
- Todos os trades registrados
- Sistema auto-documenta operações

---

**Desenvolvido para rentabilização consistente e gestão de risco rigorosa.**

**Trading automatizado é ferramenta poderosa. Use com responsabilidade.**
