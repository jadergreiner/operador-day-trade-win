<!-- pyml disable md040 -->
<!-- pyml disable md022 -->
<!-- pyml disable md026 -->
<!-- pyml disable md032 -->
<!-- pyml disable md029 -->
<!-- pyml disable md009 -->

# Sistema Automatizado de Diários

Sistema inteligente que gera automaticamente dois tipos de diário durante o pregão.

## 📔 Os Dois Diários

### 1. Diário de Trading Storytelling (15 minutos)
Narrativa do mercado em formato jornalístico:
- Manchetes tipo jornal financeiro
- Sentimento do mercado (PANIC, GREEDY, FEARFUL, CALM, etc.)
- Decisão operacional (BUY/SELL/HOLD)
- Contexto multidimensional
- Tags para aprendizagem de máquina

**Exemplo:**

```
MANCHETE: WING26 em PANICO: Vendedores dominam com forca total
SENTIMENTO: PANIC
DECISAO: HOLD (30% confiança)
```

### 2. Diário de Reflexão da IA (10 minutos)
Auto-crítica sincera e humorada da IA:
- Avaliação honesta: "Estou útil ou só gerando ruído?"
- Correlação dados x preço: "Meus dados movem o preço?"
- Feedback sobre humano: "Você está ajudando ou atrapalhando?"
- Sugestões: "O que funcionaria melhor?"

**Exemplo:**

```
HUMOR: CONFUSO
FRASE: "Quatro cerebros pensando, zero conclusoes claras."

AVALIACAO: "Honestamente? Neste momento estou so gerando ruido.
Um trader olhando o grafico seria mais util."

CORRELACAO: "FRACA - Meus dados nao capturam o que move o preco."
```

## 🚀 Como Usar

### Opção 1: Duplo Clique (Mais Fácil)

```
Duplo clique em: INICIAR_DIARIOS.bat
```

Pronto! Os diários começam automaticamente.

### Opção 2: Python Diretamente

```bash
python scripts/quick_start_journals.py
```

### Opção 3: Com Horário de Mercado (Inicia automaticamente às 09:00)

```bash
python scripts/start_automated_journals.py
```

Este script:
- Aguarda abertura do mercado (09:00)
- Inicia os diários automaticamente
- Monitora e reinicia se algum processo falhar
- Para automaticamente no fechamento (17:30)

## 📊 Acompanhamento

Cada diário roda em sua própria janela de console. Você verá:

**Janela 1 - Trading Storytelling:**

```
[10:15:00] NOVA ENTRADA
Manchete: WING26 em queda livre...
Sentimento: FEARFUL
Decisao: SELL (75% confiança)
```

**Janela 2 - AI Reflection:**

```
[10:20:00] REFLEXAO DA IA
Humor: CONFIANTE
"Todas dimensoes alinhadas. Agora eh so o mercado cooperar..."
Correlacao: FORTE - Dados funcionando!
```

## 🎯 Para Aprendizagem por Reforço

Ao final do dia, você terá:
- ~34 entradas de narrativa storytelling (cada 15min)
- ~50 reflexões da IA (cada 10min)

Todos os dados ficam salvos na memória dos serviços e podem ser exportados:

```python
from src.application.services.trading_journal import TradingJournalService
from src.application.services.ai_reflection_journal import AIReflectionJournalService

# Carregar dados do dia
trading = TradingJournalService()
ai_journal = AIReflectionJournalService()

# Exportar para ML
trading_data = trading.export_for_learning()
ai_data = ai_journal.export_for_learning()

# Analise de resultados
# Compare decisoes vs resultados reais
# Treine modelo de reforco com outcomes
```

## ⚙️ Configuração

### Intervalos de Tempo
Edite os scripts se quiser mudar frequência:

**continuous_journal.py** (linha ~156):

```python
time.sleep(900)  # 900 segundos = 15 minutos
```

**ai_reflection_continuous.py** (linha ~209):

```python
time.sleep(600)  # 600 segundos = 10 minutos
```

### Horário de Mercado
**start_automated_journals.py** (linha ~149):

```python
market_open = dt_time(9, 0)    # 09:00
market_close = dt_time(17, 30)  # 17:30
```

## 🛑 Como Parar

Feche as janelas dos diários ou pressione Ctrl+C em cada uma.

## 📝 Arquivos Gerados

Os diários salvam dados em memória durante execução. Para persistir:

1. **SQLite Database** (futuro)
   - Todas as entradas com timestamp
   - Decisões e outcomes
   - Correlações e métricas

2. **JSON Export** (disponível agora)

```python
   journal.export_for_learning()  # Retorna lista de dicts
   ```

3. **Análise End-of-Day** (próximo passo)
   - Compara todas as decisões com resultados
   - Identifica padrões de acerto/erro
   - Gera dataset para treinamento

## 🧠 Uso dos Dados

### Perguntas que os dados respondem:

**Do Trading Journal:**
- Quando a IA disse BUY/SELL, o que aconteceu depois?
- Qual sentimento (PANIC, GREEDY) teve melhor acerto?
- Alta confiança correlaciona com sucesso?
- Alinhamento > 70% significa melhor resultado?

**Da Reflexão da IA:**
- Quando a IA disse "correlação FORTE", estava certa?
- "Estou gerando ruído" = momento de não operar?
- Que humor (CONFUSO, CONFIANTE) teve melhores trades?
- Sugestões da IA ("usar price action") funcionam?

## 🎓 Próximos Passos

1. ✅ Sistema automatizado funcionando
2. ⏭️ Persistência em banco de dados
3. ⏭️ Análise end-of-day automatizada
4. ⏭️ Dashboard de visualização
5. ⏭️ Modelo de aprendizagem por reforço
6. ⏭️ Feedback loop: IA aprende com próprios erros

## 💡 Dicas

- **Deixe rodar o dia todo**: Quanto mais dados, melhor o aprendizado
- **Leia as reflexões**: A IA pode identificar problemas que você não viu
- **Compare sentimentos**: PANIC vs GREEDY - qual teve melhor timing?
- **Observe correlações**: Quando dados movem o preço, quando não movem
- **Use para decisões**: Se IA diz "correlação fraca", talvez esperar seja melhor

---

**Sistema desenvolvido para aprendizagem contínua e melhoria constante.**
**A IA aprende. Você aprende. Juntos melhoram.**
