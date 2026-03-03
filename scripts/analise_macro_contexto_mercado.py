"""
Análise Macro - COMPRA vs VENDA com Contexto de Mercado
Análise de correlação entre Mini Índice, Dólar e Curva de Juros
Head Financeiro - Macro + Micro Strategy
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from scipy import stats


class AnalisadorMacroIndice:
    """Analisa probabilidades considerando contexto macro."""

    def __init__(self):
        self.win_rate_medio = 0.65
        self.sharpe_ratio = 1.2
        self.drawdown_maximo = 0.15

        # Símbolos principais
        self.simbolos = {
            'mini_indice': "WINJ26",
            'ibovespa': "IBOV",
            'taxa_curta': "DI1U26",  # DI futuro - taxa de juros
        }

        self.dados_atuais = {}

    def conectar_mt5(self) -> bool:
        """Conecta ao MT5."""
        if not mt5.initialize():
            print(f"❌ Erro ao conectar ao MT5\n")
            return False

        self.account_info = mt5.account_info()
        return True

    def obter_cotacao_atual(self, simbolo: str) -> dict:
        """Obtém cotação atual de um símbolo."""
        try:
            if not mt5.symbol_select(simbolo):
                print(f"⚠️  {simbolo} não disponível")
                return None

            info = mt5.symbol_info(simbolo)
            if info:
                return {
                    'simbolo': simbolo,
                    'bid': info.bid,
                    'ask': info.ask,
                    'spreead': info.ask - info.bid
                }
        except:
            pass

        return None

    def obter_candles(self, simbolo: str, quantidade: int = 100,
                     timeframe = mt5.TIMEFRAME_D1) -> pd.DataFrame:
        """Obtém candles históricos."""
        try:
            if not mt5.symbol_select(simbolo):
                return None

            barras = mt5.copy_rates_from_pos(simbolo, timeframe, 0, quantidade)

            if barras is None or len(barras) == 0:
                return None

            df = pd.DataFrame(barras)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df['retorno'] = df['close'].pct_change() * 100

            return df
        except:
            return None

    def analisar_tendencia(self, df: pd.DataFrame, nome: str) -> dict:
        """Analisa tendência de um ativo."""
        if df is None or len(df) < 5:
            return None

        # Últimos 5 dias
        fechamentos = df['close'].tail(20).values

        # Tendência simples (close atual vs média 10 dias)
        media_10 = df['close'].tail(10).mean()
        close_atual = fechamentos[-1]
        tendencia_pct = ((close_atual - media_10) / media_10) * 100

        # Momentum (força da tendência)
        retornos = df['retorno'].tail(10).values
        momentum = retornos.mean()
        volatilidade_retorno = retornos.std()

        # Trend strength (RSI simplificado usando retornos)
        positivos = len(retornos[retornos > 0])
        negativos = len(retornos[retornos < 0])

        return {
            'nome': nome,
            'preco_atual': float(close_atual),
            'media_10d': float(media_10),
            'tendencia_pct': float(tendencia_pct),
            'momentum': float(momentum),
            'volatilidade_retorno': float(volatilidade_retorno),
            'dias_positivos': int(positivos),
            'dias_negativos': int(negativos),
            'sentimento': 'ALTA' if tendencia_pct > 1.0 else 'BAIXA' if tendencia_pct < -1.0 else 'NEUTRO'
        }

    def calcular_correlacoes(self, df_mini: pd.DataFrame, df_ibov: pd.DataFrame,
                            df_taxa: pd.DataFrame) -> dict:
        """Calcula correlações entre ativos."""
        correlacoes = {}

        try:
            if df_mini is not None and df_ibov is not None:
                # Correlação positiva esperada (índices acompanham-se)
                corr_mini_ibov = df_mini['retorno'].corr(df_ibov['retorno'])
                correlacoes['mini_vs_ibov'] = float(corr_mini_ibov)

            if df_mini is not None and df_taxa is not None:
                # Correlação negativa esperada (juros altos = índice cai)
                corr_mini_taxa = df_mini['retorno'].corr(df_taxa['retorno'])
                correlacoes['mini_vs_taxa'] = float(corr_mini_taxa)

            if df_ibov is not None and df_taxa is not None:
                corr_ibov_taxa = df_ibov['retorno'].corr(df_taxa['retorno'])
                correlacoes['ibov_vs_taxa'] = float(corr_ibov_taxa)
        except:
            pass

        return correlacoes

    def analisar_cenario_macro(self, tendencias: dict, correlacoes: dict) -> dict:
        """Analisa cenário macro consolidado."""

        mini = tendencias.get('mini_indice')
        ibov = tendencias.get('ibovespa')
        taxa = tendencias.get('taxa_curta')

        print("\n" + "="*80)
        print("📊 ANÁLISE MACRO - Contexto de Mercado")
        print("="*80 + "\n")

        # Cenários macro
        cenarios = []
        pontuacao_compra = 0
        pontuacao_venda = 0

        # 1. Índice Bovespa (referência geral)
        print("1️⃣  ÍNDICE BOVESPA (IBOV):")
        if ibov:
            print(f"   Preço: {ibov['preco_atual']:.2f}")
            print(f"   Tendência: {ibov['tendencia_pct']:+.2f}%")
            print(f"   Sentimento: {ibov['sentimento']}")

            if ibov['sentimento'] == 'ALTA':
                print(f"   ✅ Bovespa em alta → Favorável para índices (COMPRA +)")
                pontuacao_compra += 2
                cenarios.append("Bovespa em alta")
            elif ibov['sentimento'] == 'BAIXA':
                print(f"   ⚠️  Bovespa em baixa → Desfavorável para índices (VENDA +)")
                pontuacao_venda += 2
                cenarios.append("Bovespa em queda")
            else:
                print(f"   ➡️  Bovespa neutro")
                cenarios.append("Bovespa estável")

        print()

        # 2. Curva de Juros (taxa DI/SELIC)
        print("2️⃣  TAXA DE JUROS (DI - Proxy SELIC):")
        if taxa:
            print(f"   Preço: {taxa['preco_atual']:.2f}")
            print(f"   Tendência: {taxa['tendencia_pct']:+.2f}%")
            print(f"   Sentimento: {taxa['sentimento']}")

            if taxa['sentimento'] == 'ALTA':
                print(f"   📈 Taxa subindo → Renda fixa melhor, ações menos atrativas (VENDA +)")
                pontuacao_venda += 2
                cenarios.append("Juros em alta (inflacionário)")
            elif taxa['sentimento'] == 'BAIXA':
                print(f"   📉 Taxa caindo → Ações mais atrativas (COMPRA +)")
                pontuacao_compra += 2
                cenarios.append("Juros em queda (estimulante)")
            else:
                print(f"   ➡️  Taxa estável")
                cenarios.append("Juros estáveis")

        print()

        # 3. Mini Índice
        print("3️⃣  MINI ÍNDICE (WINJ26):")
        if mini:
            print(f"   Preço: {mini['preco_atual']:.2f}")
            print(f"   Tendência: {mini['tendencia_pct']:+.2f}%")
            print(f"   Sentimento: {mini['sentimento']}")

            if mini['sentimento'] == 'ALTA':
                print(f"   ⬆️  Mini em tendência de alta")
                pontuacao_compra += 1
            elif mini['sentimento'] == 'BAIXA':
                print(f"   ⬇️  Mini em tendência de baixa")
                pontuacao_venda += 1

        print()

        # 4. Correlações
        print("4️⃣  CORRELAÇÕES ENTRE ATIVOS:")
        if correlacoes:
            tem_analise = False
            for chave, valor in correlacoes.items():
                if not np.isnan(valor):
                    tem_analise = True
                    print(f"   {chave}: {valor:+.3f}")

                    if abs(valor) > 0.7:
                        print(f"      → FORTE dependência")
                    elif abs(valor) > 0.4:
                        print(f"      → Dependência moderada")

            if not tem_analise:
                print(f"   ⚠️  Correlações indisponíveis")

        print()

        # Decisão macro
        print("="*80)
        print("🎯 DIAGNÓSTICO MACRO")
        print("="*80 + "\n")

        if len(cenarios) > 0:
            print("Fatores identificados:")
            for i, cenario in enumerate(cenarios, 1):
                print(f"  {i}. {cenario}")

        print()
        print(f"Pontuação COMPRA: {pontuacao_compra}/6")
        print(f"Pontuação VENDA: {pontuacao_venda}/6\n")

        # Determinação do cenário macro
        if pontuacao_compra > pontuacao_venda + 1:
            sentimento_macro = 'BULLISH'
            sinal = "📈 FAVORÁVEL PARA COMPRA"
            boost_compra = 0.15  # +15% de boost
            boost_venda = -0.10  # -10% de penalidade
        elif pontuacao_venda > pontuacao_compra + 1:
            sentimento_macro = 'BEARISH'
            sinal = "📉 FAVORÁVEL PARA VENDA"
            boost_compra = -0.10
            boost_venda = 0.15
        else:
            sentimento_macro = 'NEUTRAL'
            sinal = "⏸️  CENÁRIO EQUILIBRADO"
            boost_compra = 0.0
            boost_venda = 0.0

        print(sinal)

        return {
            'sentimento_macro': sentimento_macro,
            'pontuacao_compra': pontuacao_compra,
            'pontuacao_venda': pontuacao_venda,
            'boost_compra': boost_compra,
            'boost_venda': boost_venda,
            'tendencias': tendencias,
            'correlacoes': correlacoes
        }

    def recalcular_probabilidades_com_macro(self, prob_micro: dict,
                                            analise_macro: dict) -> dict:
        """Recalcula probabilidades incorporando análise macro."""

        prob_compra_original = prob_micro['prob_compra']
        prob_venda_original = prob_micro['prob_venda']

        boost_c = analise_macro['boost_compra']
        boost_v = analise_macro['boost_venda']

        print("\n" + "="*80)
        print("🔄 RECALCULANDO PROBABILIDADES COM MACRO")
        print("="*80 + "\n")

        print("CENÁRIO 1: COMPRA")
        print(f"  Probabilidade micro (técnica): {prob_compra_original*100:.1f}%")
        print(f"  Ajuste macro: {boost_c:+.2%}")

        prob_compra_nova = prob_compra_original + boost_c
        prob_compra_nova = max(0.20, min(0.90, prob_compra_nova))  # Limitar entre 20-90%

        print(f"  Probabilidade com macro: {prob_compra_nova*100:.1f}%")
        print(f"  Diferença: {(prob_compra_nova - prob_compra_original)*100:+.1f}pp\n")

        print("CENÁRIO 2: VENDA")
        print(f"  Probabilidade micro (técnica): {prob_venda_original*100:.1f}%")
        print(f"  Ajuste macro: {boost_v:+.2%}")

        prob_venda_nova = prob_venda_original + boost_v
        prob_venda_nova = max(0.20, min(0.90, prob_venda_nova))

        print(f"  Probabilidade com macro: {prob_venda_nova*100:.1f}%")
        print(f"  Diferença: {(prob_venda_nova - prob_venda_original)*100:+.1f}pp\n")

        return {
            'prob_compra_original': prob_compra_original,
            'prob_venda_original': prob_venda_original,
            'prob_compra_com_macro': prob_compra_nova,
            'prob_venda_com_macro': prob_venda_nova,
            'delta_compra': prob_compra_nova - prob_compra_original,
            'delta_venda': prob_venda_nova - prob_venda_original
        }

    def analisar(self, prob_micro: dict) -> dict:
        """Realiza análise macro completa."""

        if not self.conectar_mt5():
            return None

        print("\n" + "="*80)
        print("🌍 ANÁLISE MACRO - Índice, Dólar, Curva de Juros")
        print("="*80 + "\n")

        # 1. Obter candles de cada ativo
        print("[1/4] Coletando dados dos ativos macro...\n")

        df_mini = self.obter_candles(self.simbolos['mini_indice'], quantidade=20)
        df_ibov = self.obter_candles(self.simbolos['ibovespa'], quantidade=20)
        df_taxa = self.obter_candles(self.simbolos['taxa_curta'], quantidade=20)

        if df_mini is None:
            print("❌ Erro ao obter dados do Mini Índice\n")
            mt5.shutdown()
            return None

        print(f"✅ Mini Índice: {len(df_mini)} dias")
        if df_ibov is not None:
            print(f"✅ Índice Bovespa: {len(df_ibov)} dias")
        else:
            print(f"⚠️  Índice Bovespa: indisponível")

        if df_taxa is not None:
            print(f"✅ Taxa DI: {len(df_taxa)} dias")
        else:
            print(f"⚠️  Taxa DI: indisponível")

        print()

        # 2. Analisar tendências
        print("[2/4] Analisando tendências de cada ativo...\n")

        tendencias = {}
        tendencias['mini_indice'] = self.analisar_tendencia(df_mini, "Mini Índice")
        if df_ibov is not None:
            tendencias['ibovespa'] = self.analisar_tendencia(df_ibov, "Índice Bovespa")
        if df_taxa is not None:
            tendencias['taxa_curta'] = self.analisar_tendencia(df_taxa, "Taxa DI")

        # 3. Calcular correlações
        print("[3/4] Calculando correlações entre ativos...\n")
        correlacoes = self.calcular_correlacoes(df_mini, df_ibov, df_taxa)

        # 4. Analisar cenário macro
        print("[4/4] Consolidando análise macro...\n")
        analise_macro = self.analisar_cenario_macro(tendencias, correlacoes)

        # 5. Recalcular probabilidades
        prob_ajustadas = self.recalcular_probabilidades_com_macro(prob_micro, analise_macro)

        # Recomendação final
        print("\n" + "="*80)
        print("🎯 RECOMENDAÇÃO FINAL - COM ANÁLISE MACRO")
        print("="*80 + "\n")

        prob_c = prob_ajustadas['prob_compra_com_macro']
        prob_v = prob_ajustadas['prob_venda_com_macro']

        if prob_c > prob_v + 0.10:
            recomendacao = "COMPRAR"
            emoji = "📈 BUY"
            motivo = f"Probabilidade COMPRA {prob_c*100:.1f}% ainda favorável"
        elif prob_v > prob_c + 0.10:
            recomendacao = "VENDER"
            emoji = "📉 SELL"
            motivo = f"Probabilidade VENDA {prob_v*100:.1f}% favorável com macro"
        else:
            recomendacao = "HOLD / AGUARDAR"
            emoji = "⏸️  WAIT"
            motivo = "Ainda sem divergência clara mesmo com macro"

        print(f"{emoji} {recomendacao}")
        print(f"   {motivo}\n")

        print("COMPARATIVO ANTES vs DEPOIS:")
        print(f"  COMPRA: {prob_ajustadas['prob_compra_original']*100:.1f}% → {prob_c*100:.1f}% ({prob_ajustadas['delta_compra']:+.1f}pp)")
        print(f"  VENDA:  {prob_ajustadas['prob_venda_original']*100:.1f}% → {prob_v*100:.1f}% ({prob_ajustadas['delta_venda']:+.1f}pp)\n")

        print("CONTEXTO MACRO:")
        print(f"  Sentimento: {analise_macro['sentimento_macro']}")
        print(f"  Fatores: Bovespa ({tendencias['ibovespa']['sentimento'] if 'ibovespa' in tendencias else 'N/A'}), " +
              f"Juros ({tendencias['taxa_curta']['sentimento'] if 'taxa_curta' in tendencias else 'N/A'}), " +
              f"Índice ({tendencias['mini_indice']['sentimento']})\n")

        mt5.shutdown()

        return {
            'timestamp': datetime.now().isoformat(),
            'recomendacao': recomendacao,
            'probabilidades': prob_ajustadas,
            'analise_macro': analise_macro,
            'tendencias': tendencias
        }


def main():
    """Executa análise macro."""

    # Primeiro, obter probabilidades micro (técnicas)
    print("📊 PASSO 1: OBTENDO PROBABILIDADES TÉCNICAS (MICRO)...\n")

    from probabilidade_compra_venda_intraday import AnalisadorProbabilidadeIntraday

    analisador_micro = AnalisadorProbabilidadeIntraday()
    resultado_micro = analisador_micro.analisar()

    if not resultado_micro:
        print("❌ Erro ao obter análise técnica\n")
        return

    prob_micro = {
        'prob_compra': resultado_micro['prob_compra'],
        'prob_venda': resultado_micro['prob_venda']
    }

    # Depois, analisar macro
    print("\n\n" + "="*80)
    print("📊 PASSO 2: ANALISANDO CONTEXTO MACRO...\n")
    print("="*80 + "\n")

    analisador_macro = AnalisadorMacroIndice()
    resultado_macro = analisador_macro.analisar(prob_micro)

    if resultado_macro:
        arquivo = f"logs/analise_macro_intraday_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Preparar resultado para JSON (converter numpy types)
        def converter_numpy(obj):
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj) if isinstance(obj, np.floating) else int(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: converter_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [converter_numpy(item) for item in obj]
            return obj

        resultado_clean = converter_numpy(resultado_macro)

        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(resultado_clean, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Análise salva em: {arquivo}")


if __name__ == "__main__":
    main()
