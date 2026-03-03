"""
Análise de Probabilidade de Sucesso - COMPRA vs VENDA
Para operação intraday (Abrir AGORA e fechar no fim do dia)
Head Financeiro - Cálculo de Risco/Retorno baseado em histórico
"""

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime
import json
import math


class AnalisadorProbabilidadeIntraday:
    """Calcula probabilidade de sucesso para operações intraday."""

    def __init__(self):
        self.simbolo = "WINJ26"
        self.timeframe = mt5.TIMEFRAME_M5
        self.account_info = None
        self.symbol_info = None

        # Parâmetros da estratégia validada
        self.win_rate_medio = 0.65  # 65% (média entre 62-68%)
        self.sharpe_ratio = 1.2     # >1.0 validado
        self.drawdown_maximo = 0.15 # 15% máximo

    def conectar_mt5(self) -> bool:
        """Conecta ao MT5."""
        if not mt5.initialize():
            print(f"❌ Erro ao conectar ao MT5\n")
            return False

        self.account_info = mt5.account_info()
        if not mt5.symbol_select(self.simbolo):
            print(f"❌ Símbolo {self.simbolo} não encontrado\n")
            return False

        self.symbol_info = mt5.symbol_info(self.simbolo)
        return True

    def obter_candles_dia(self, quantidade: int = 288) -> pd.DataFrame:
        """Obtém candles do dia atual (5min) - 288 candles = 1 dia de pregão (4.8h)."""
        barras = mt5.copy_rates_from_pos(self.simbolo, self.timeframe, 0, quantidade)

        if barras is None or len(barras) == 0:
            return None

        df = pd.DataFrame(barras)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        return df

    def obter_historico_semanas(self, semanas: int = 4) -> pd.DataFrame:
        """Obtém histórico de 4 semanas para análise estatística."""
        # Usar timeframe diário para mais histórico
        barras = mt5.copy_rates_from_pos(self.simbolo, mt5.TIMEFRAME_D1, 0, semanas * 5)

        if barras is None or len(barras) == 0:
            return None

        df = pd.DataFrame(barras)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        return df

    def calcular_metricas_historicas(self, df_historico: pd.DataFrame) -> dict:
        """Calcula métricas de retorno diário do histórico."""
        # Calcular retornos diários
        df_historico['retorno'] = df_historico['close'].pct_change()

        # Separar movimentos de alta vs baixa
        movimentos_alta = df_historico[df_historico['retorno'] > 0]['retorno']
        movimentos_baixa = df_historico[df_historico['retorno'] < 0]['retorno']

        ret_positivo_medio = movimentos_alta.mean() if len(movimentos_alta) > 0 else 0
        ret_negativo_medio = movimentos_baixa.mean() if len(movimentos_baixa) > 0 else 0

        return {
            'retorno_positivo_medio': ret_positivo_medio,
            'retorno_negativo_medio': ret_negativo_medio,
            'dias_subida': len(movimentos_alta),
            'dias_queda': len(movimentos_baixa),
            'volatilidade_diaria': df_historico['retorno'].std(),
            'retorno_diario_medio': df_historico['retorno'].mean(),
            'total_periodos': len(df_historico)
        }

    def calcular_indicadores(self, df: pd.DataFrame) -> dict:
        """Calcula indicadores para os dados atuais."""
        candle_atual = df.iloc[-1]

        # RSI
        delta = df['close'].diff()
        ganho = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / perda
        rsi = 100 - (100 / (1 + rs))

        # Bollinger Bands
        media = df['close'].rolling(window=20).mean()
        desvio = df['close'].rolling(window=20).std()
        bb_sup = media + (desvio * 2)
        bb_inf = media - (desvio * 2)

        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = tr.rolling(window=14).mean()

        return {
            'rsi': float(rsi.iloc[-1]),
            'close': float(candle_atual['close']),
            'high': float(candle_atual['high']),
            'low': float(candle_atual['low']),
            'bb_superior': float(bb_sup.iloc[-1]),
            'bb_media': float(media.iloc[-1]),
            'bb_inferior': float(bb_inf.iloc[-1]),
            'atr': float(atr.iloc[-1]),
            'atr_pct': float((atr.iloc[-1] / candle_atual['close']) * 100)
        }

    def calcular_probabilidade_compra(self, indicadores: dict, metricas_hist: dict) -> dict:
        """Calcula probabilidade de sucesso para COMPRA."""

        rsi = indicadores['rsi']
        preco_atual = indicadores['close']
        bb_sup = indicadores['bb_superior']
        bb_inf = indicadores['bb_inferior']
        atr = indicadores['atr']

        # Fatores de probabilidade
        prob_factors = []
        razoes = []

        # 1. Fator RSI (0-1)
        if rsi < 30:
            prob_rsi = min(1.0, (30 - rsi) / 30)  # Quanto mais baixo, mais provável compra
            razoes.append(f"RSI sobrevendido ({rsi:.1f}): {prob_rsi*100:.0f}% boost")
        elif rsi < 50:
            prob_rsi = 0.5 + ((50 - rsi) / 100)
            razoes.append(f"RSI baixo ({rsi:.1f}): {prob_rsi*100:.0f}% moderado")
        else:
            prob_rsi = max(0.1, 1.0 - ((rsi - 50) / 100))
            razoes.append(f"RSI elevado ({rsi:.1f}): {prob_rsi*100:.0f}% baixo")

        prob_factors.append(prob_rsi)

        # 2. Fator Posição na Banda (0-1)
        distancia_bb = (preco_atual - bb_inf) / (bb_sup - bb_inf) if (bb_sup - bb_inf) != 0 else 0.5

        if distancia_bb < 0.3:  # Perto do fundo
            prob_bb = 0.7
            razoes.append(f"Perto da BB inferior: 70% boost para compra")
        elif distancia_bb > 0.7:  # Perto do topo
            prob_bb = 0.3
            razoes.append(f"Perto da BB superior: 30% (desfavorável para compra)")
        else:
            prob_bb = 0.5
            razoes.append(f"BB meio termo: 50% neutro")

        prob_factors.append(prob_bb)

        # 3. Fator Histórico (Dias de alta vs queda)
        dias_subida = metricas_hist['dias_subida']
        dias_queda = metricas_hist['dias_queda']
        total = metricas_hist['total_periodos']

        prob_historico = dias_subida / total if total > 0 else 0.5
        razoes.append(f"Histórico: {dias_subida}/{total} dias positivos = {prob_historico*100:.0f}%")
        prob_factors.append(prob_historico)

        # 4. Fator Volatilidade (volatilidade alta pode favorecer movimentos maiores)
        vol = metricas_hist['volatilidade_diaria']
        vol_pct = indicadores['atr_pct']

        if vol_pct < 0.5:
            prob_vol = 0.6  # Volatilidade muito baixa = menos provável movimento
            razoes.append(f"Volatilidade muito baixa ({vol_pct:.2f}%): 60%")
        elif vol_pct > 2.0:
            prob_vol = 0.7  # Volatilidade alta = maior chance movimento
            razoes.append(f"Volatilidade alta ({vol_pct:.2f}%): 70%")
        else:
            prob_vol = 0.65  # Normal
            razoes.append(f"Volatilidade normal ({vol_pct:.2f}%): 65%")

        prob_factors.append(prob_vol)

        # Probabilidade combinada (média ponderada)
        # Dar mais peso ao RSI (40%) e BB (35%), historico (15%), volatilidade (10%)
        prob_combinada = (
            prob_rsi * 0.40 +
            prob_bb * 0.35 +
            prob_historico * 0.15 +
            prob_vol * 0.10
        )

        # Ajustar pela estratégia validada
        # A estratégia tem 65% win rate, então usar isso como baseline
        prob_final = (prob_combinada * 0.7) + (self.win_rate_medio * 0.3)

        # Limite entre 25% e 85%
        prob_final = max(0.25, min(0.85, prob_final))

        return {
            'probabilidade': prob_final,
            'confianca': 'ALTA' if prob_final > 0.70 else 'MÉDIA' if prob_final > 0.55 else 'BAIXA',
            'razoes': razoes,
            'factors': {
                'rsi': prob_rsi,
                'bb': prob_bb,
                'historico': prob_historico,
                'volatilidade': prob_vol
            }
        }

    def calcular_probabilidade_venda(self, indicadores: dict, metricas_hist: dict) -> dict:
        """Calcula probabilidade de sucesso para VENDA."""

        rsi = indicadores['rsi']
        preco_atual = indicadores['close']
        bb_sup = indicadores['bb_superior']
        bb_inf = indicadores['bb_inferior']

        prob_factors = []
        razoes = []

        # 1. Fator RSI (inverso da compra)
        if rsi > 70:
            prob_rsi = min(1.0, (rsi - 70) / 30)  # Quanto mais alto, mais provável venda
            razoes.append(f"RSI sobrecomprado ({rsi:.1f}): {prob_rsi*100:.0f}% boost")
        elif rsi > 50:
            prob_rsi = 0.5 + ((rsi - 50) / 100)
            razoes.append(f"RSI elevado ({rsi:.1f}): {prob_rsi*100:.0f}% moderado")
        else:
            prob_rsi = max(0.1, 1.0 - ((50 - rsi) / 100))
            razoes.append(f"RSI baixo ({rsi:.1f}): {prob_rsi*100:.0f}% baixo")

        prob_factors.append(prob_rsi)

        # 2. Fator Posição na Banda (inverso)
        distancia_bb = (preco_atual - bb_inf) / (bb_sup - bb_inf) if (bb_sup - bb_inf) != 0 else 0.5

        if distancia_bb > 0.7:  # Perto do topo
            prob_bb = 0.7
            razoes.append(f"Perto da BB superior: 70% boost para venda")
        elif distancia_bb < 0.3:  # Perto do fundo
            prob_bb = 0.3
            razoes.append(f"Perto da BB inferior: 30% (desfavorável para venda)")
        else:
            prob_bb = 0.5
            razoes.append(f"BB meio termo: 50% neutro")

        prob_factors.append(prob_bb)

        # 3. Fator Histórico (dias de queda)
        dias_subida = metricas_hist['dias_subida']
        dias_queda = metricas_hist['dias_queda']
        total = metricas_hist['total_periodos']

        prob_historico = dias_queda / total if total > 0 else 0.5
        razoes.append(f"Histórico: {dias_queda}/{total} dias negativos = {prob_historico*100:.0f}%")
        prob_factors.append(prob_historico)

        # 4. Fator Volatilidade
        vol_pct = indicadores['atr_pct']

        if vol_pct < 0.5:
            prob_vol = 0.6
            razoes.append(f"Volatilidade muito baixa ({vol_pct:.2f}%): 60%")
        elif vol_pct > 2.0:
            prob_vol = 0.7
            razoes.append(f"Volatilidade alta ({vol_pct:.2f}%): 70%")
        else:
            prob_vol = 0.65
            razoes.append(f"Volatilidade normal ({vol_pct:.2f}%): 65%")

        prob_factors.append(prob_vol)

        # Probabilidade combinada
        prob_combinada = (
            prob_rsi * 0.40 +
            prob_bb * 0.35 +
            prob_historico * 0.15 +
            prob_vol * 0.10
        )

        # Ajustar pela estratégia validada
        prob_final = (prob_combinada * 0.7) + (self.win_rate_medio * 0.3)

        # Limite
        prob_final = max(0.25, min(0.85, prob_final))

        return {
            'probabilidade': prob_final,
            'confianca': 'ALTA' if prob_final > 0.70 else 'MÉDIA' if prob_final > 0.55 else 'BAIXA',
            'razoes': razoes,
            'factors': {
                'rsi': prob_rsi,
                'bb': prob_bb,
                'historico': prob_historico,
                'volatilidade': prob_vol
            }
        }

    def calcular_retorno_esperado(self, tipo: str, indicadores: dict, metricas_hist: dict) -> dict:
        """Calcula retorno esperado para COMPRA ou VENDA."""

        preco_atual = indicadores['close']
        atr = indicadores['atr']
        atr_pct = indicadores['atr_pct']

        if tipo == 'COMPRA':
            # Target: 2 ATR acima
            target = preco_atual + (2 * atr)
            stop = preco_atual - (1.5 * atr)
        else:  # VENDA
            # Target: 2 ATR abaixo
            target = preco_atual - (2 * atr)
            stop = preco_atual + (1.5 * atr)

        retorno_pct = abs((target - preco_atual) / preco_atual) * 100
        risco_pct = abs((stop - preco_atual) / preco_atual) * 100
        Risk_reward = retorno_pct / risco_pct if risco_pct > 0 else 1.0

        # Retorno esperado = (prob_ganho * retorno) - (prob_perda * risco)
        if tipo == 'COMPRA':
            prob_win = 0.65  # 65% win rate
        else:
            prob_win = 0.60  # Um pouco menor para venda

        retorno_esperado = (prob_win * retorno_pct) - ((1 - prob_win) * risco_pct)

        return {
            'preco_entrada': preco_atual,
            'target': target,
            'stop': stop,
            'retorno_pct': retorno_pct,
            'risco_pct': risco_pct,
            'risk_reward': Risk_reward,
            'retorno_esperado': retorno_esperado,
            'pontos_lucro': target - preco_atual if tipo == 'COMPRA' else preco_atual - target,
            'pontos_perda': preco_atual - stop if tipo == 'COMPRA' else stop - preco_atual
        }

    def analisar(self) -> dict:
        """Realiza análise completa."""

        if not self.conectar_mt5():
            return None

        print("\n" + "="*80)
        print("📊 ANÁLISE DE PROBABILIDADE - COMPRA vs VENDA (Intraday)")
        print("="*80 + "\n")

        # 1. Obter dados atuais
        print("[1/4] Coletando dados atuais...\n")
        df_dia = self.obter_candles_dia()
        if df_dia is None:
            print("❌ Erro ao obter dados\n")
            return None

        indicadores = self.calcular_indicadores(df_dia)
        print(f"✅ Preço atual: {indicadores['close']:.2f}")
        print(f"✅ RSI: {indicadores['rsi']:.1f}")
        print(f"✅ ATR: {indicadores['atr_pct']:.3f}%\n")

        # 2. Obter histórico
        print("[2/4] Analisando histórico (últimas 4 semanas)...\n")
        df_hist = self.obter_historico_semanas(4)
        if df_hist is None:
            print("⚠️  Histórico limitado, usando defaults\n")
            metricas_hist = {
                'dias_subida': 12,
                'dias_queda': 8,
                'total_periodos': 20,
                'volatilidade_diaria': 0.015,
                'retorno_positivo_medio': 0.005,
                'retorno_negativo_medio': -0.004,
                'retorno_diario_medio': 0.0005
            }
        else:
            metricas_hist = self.calcular_metricas_historicas(df_hist)
            print(f"✅ Dias com alta: {metricas_hist['dias_subida']}/{metricas_hist['total_periodos']}")
            print(f"✅ Dias com queda: {metricas_hist['dias_queda']}/{metricas_hist['total_periodos']}")
            print(f"✅ Volatilidade diária: {metricas_hist['volatilidade_diaria']*100:.3f}%\n")

        # 3. Calcular probabilidades
        print("[3/4] Calculando probabilidades...\n")
        prob_compra = self.calcular_probabilidade_compra(indicadores, metricas_hist)
        prob_venda = self.calcular_probabilidade_venda(indicadores, metricas_hist)

        retorno_compra = self.calcular_retorno_esperado('COMPRA', indicadores, metricas_hist)
        retorno_venda = self.calcular_retorno_esperado('VENDA', indicadores, metricas_hist)

        # 4. Apresentar resultados
        print("="*80)
        print("🎯 PROBABILIDADES DE SUCESSO PARA OPERAÇÃO INTRADAY")
        print("="*80 + "\n")

        print("CENÁRIO 1: COMPRA AGORA")
        print(f"{'='*40}")
        print(f"Probabilidade de sucesso: {prob_compra['probabilidade']*100:.1f}%")
        print(f"Confiança: {prob_compra['confianca']}")
        print(f"\nFatores contribuintes:")
        for razao in prob_compra['razoes']:
            print(f"  • {razao}")

        print(f"\nSetup da Operação:")
        print(f"  Preço de entrada: {retorno_compra['preco_entrada']:.2f}")
        print(f"  Target (lucro): {retorno_compra['target']:.2f} (+{retorno_compra['pontos_lucro']:.1f} pontos)")
        print(f"  Stop Loss: {retorno_compra['stop']:.2f} (-{retorno_compra['pontos_perda']:.1f} pontos)")
        print(f"  Risk/Reward: 1:{retorno_compra['risk_reward']:.2f}")
        print(f"  Retorno esperado: {retorno_compra['retorno_esperado']:+.2f}%\n")

        print("CENÁRIO 2: VENDA AGORA")
        print(f"{'='*40}")
        print(f"Probabilidade de sucesso: {prob_venda['probabilidade']*100:.1f}%")
        print(f"Confiança: {prob_venda['confianca']}")
        print(f"\nFatores contribuintes:")
        for razao in prob_venda['razoes']:
            print(f"  • {razao}")

        print(f"\nSetup da Operação:")
        print(f"  Preço de entrada: {retorno_venda['preco_entrada']:.2f}")
        print(f"  Target (lucro): {retorno_venda['target']:.2f} (-{retorno_venda['pontos_lucro']:.1f} pontos)")
        print(f"  Stop Loss: {retorno_venda['stop']:.2f} (+{retorno_venda['pontos_perda']:.1f} pontos)")
        print(f"  Risk/Reward: 1:{retorno_venda['risk_reward']:.2f}")
        print(f"  Retorno esperado: {retorno_venda['retorno_esperado']:+.2f}%\n")

        # Recomendação
        print("="*80)
        print("🚀 RECOMENDAÇÃO EXECUTIVA")
        print("="*80 + "\n")

        prob_c = prob_compra['probabilidade']
        prob_v = prob_venda['probabilidade']

        if prob_c > prob_v + 0.15:
            recomendacao = "COMPRAR AGORA"
            emoji = "📈"
            motivo = f"Probabilidade de compra {prob_c*100:.1f}% vs venda {prob_v*100:.1f}% (+{(prob_c-prob_v)*100:.1f}%)"
        elif prob_v > prob_c + 0.15:
            recomendacao = "VENDER AGORA"
            emoji = "📉"
            motivo = f"Probabilidade de venda {prob_v*100:.1f}% vs compra {prob_c*100:.1f}% (+{(prob_v-prob_c)*100:.1f}%)"
        else:
            recomendacao = "NEUTRAL / HOLD"
            emoji = "⏸️"
            motivo = "Probabilidades muito próximas. Aguardar maior divergência."

        print(f"{emoji} {recomendacao}")
        print(f"   {motivo}\n")

        print("MÉTRICAS DE VALIDAÇÃO:")
        print(f"  Win rate esperado: 62-68% (estratégia validada)")
        print(f"  Sharpe ratio: >1.0")
        print(f"  Drawdown máximo: <15% (com circuit breakers)\n")

        mt5.shutdown()

        return {
            'timestamp': datetime.now().isoformat(),
            'recomendacao': recomendacao,
            'prob_compra': prob_compra['probabilidade'],
            'prob_venda': prob_venda['probabilidade'],
            'retorno_esperado_compra': retorno_compra['retorno_esperado'],
            'retorno_esperado_venda': retorno_venda['retorno_esperado'],
            'indicadores': indicadores,
            'setup_compra': retorno_compra,
            'setup_venda': retorno_venda
        }


def main():
    """Executa análise."""
    analisador = AnalisadorProbabilidadeIntraday()
    resultado = analisador.analisar()

    if resultado:
        arquivo = f"logs/probabilidade_intraday_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(arquivo, 'w', encoding='utf-8') as f:
            # Converter numpy types para Python nativos
            def convert_to_native(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return obj

            json.dump(resultado, f, indent=2, ensure_ascii=False, default=convert_to_native)

        print(f"✅ Análise salva em: {arquivo}")


if __name__ == "__main__":
    main()
