#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de Análise Técnica Avançada para OPERADOR
- Market Strength (Força do Mercado)
- Buy/Sell Probability (Probabilidade Comprador/Vendedor)
- SMC Calculations (Smart Money Concepts)
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime

class AnaliseTecnica:
    """Análise técnica avançada com SMC e Market Strength"""
    
    def __init__(self):
        self.velas = []
        self.load_velas()
    
    def load_velas(self):
        """Carrega as velas mais recentes para análise"""
        # Simula dados de velas (em produção: viria do MT5)
        # Usando backtest_labeled_results.json como fonte
        try:
            if Path('backtest_labeled_results.json').exists():
                with open('backtest_labeled_results.json', 'r') as f:
                    data = json.load(f)
                    self.velas = data.get('labels', [])[:50]  # Últimas 50 velas
        except:
            self.velas = []
    
    def calcular_market_strength(self):
        """
        Calcula força do mercado (0-100)
        Combina: Trend strength + Volume strength + Volatility
        """
        
        # Trend Strength (RSI simplified)
        trend_strength = self._calcular_trend_strength()
        
        # Volume Strength (momentum)
        volume_strength = self._calcular_volume_strength()
        
        # Volatility Index
        volatility_idx = self._calcular_volatility_index()
        
        # Score agregado
        market_strength = (trend_strength * 0.4 + 
                          volume_strength * 0.4 + 
                          volatility_idx * 0.2)
        
        # Classificação
        if market_strength >= 80:
            classificacao = "FORTE"
            cor = "🟢"
        elif market_strength >= 50:
            classificacao = "MODERADO"
            cor = "🟡"
        else:
            classificacao = "FRACO"
            cor = "🔴"
        
        return {
            'trend_strength': int(trend_strength),
            'volume_strength': int(volume_strength),
            'volatility_index': int(volatility_idx),
            'overall': int(market_strength),
            'classificacao': classificacao,
            'emoji': cor
        }
    
    def _calcular_trend_strength(self):
        """RSI simplified (0-100)"""
        if len(self.velas) < 14:
            return 50
        
        changes = np.diff([v if isinstance(v, (int, float)) else 0 for v in self.velas[-14:]])
        gains = np.sum([c for c in changes if c > 0]) / 14 * 100
        losses = np.sum([-c for c in changes if c < 0]) / 14 * 100
        
        # Simula RSI
        if losses == 0:
            rsi = 100
        else:
            rs = gains / (losses if losses > 0 else 1)
            rsi = 100 - (100 / (1 + rs))
        
        return min(100, max(0, rsi))
    
    def _calcular_volume_strength(self):
        """Força baseada em volume (0-100)"""
        # Simula análise de volume
        # Em produção: viria do OBV (On Balance Volume)
        return 50 + np.random.randint(-20, 20)
    
    def _calcular_volatility_index(self):
        """Índice de volatilidade (0-100)"""
        # Simula volatilidade
        # Em produção: ATR / Close * 100
        return 30 + np.random.randint(-10, 30)
    
    def calcular_probability_buyer_seller(self):
        """
        Calcula probabilidade de comprador vs vendedor (0-100%)
        """
        
        # Sinais de compra
        buy_signals = self._contar_buy_signals()
        
        # Sinais de venda
        sell_signals = self._contar_sell_signals()
        
        # Sinais neutros
        total_signals = buy_signals + sell_signals + 10  # +10 para neutros
        
        buy_prob = (buy_signals / total_signals) * 100 if total_signals > 0 else 50
        sell_prob = (sell_signals / total_signals) * 100 if total_signals > 0 else 50
        neutral_prob = 100 - buy_prob - sell_prob
        
        # Primary signal
        if buy_prob > sell_prob:
            primary_signal = "BUY 🟢"
            strength = "Forte" if buy_prob > 65 else "Moderado"
        elif sell_prob > buy_prob:
            primary_signal = "SELL 🔴"
            strength = "Forte" if sell_prob > 65 else "Moderado"
        else:
            primary_signal = "NEUTRO 🟡"
            strength = "Indefinido"
        
        return {
            'buy_probability': int(buy_prob),
            'sell_probability': int(sell_prob),
            'neutral_probability': int(neutral_prob),
            'primary_signal': primary_signal,
            'strength': strength
        }
    
    def _contar_buy_signals(self):
        """Conta sinais de compra (simplificado)"""
        # Em produção: MA crossover, RSI < 30, Volume spike, etc
        return 6 + np.random.randint(-2, 3)
    
    def _contar_sell_signals(self):
        """Conta sinais de venda (simplificado)"""
        return 4 + np.random.randint(-2, 3)
    
    def calcular_smc_levels(self):
        """
        Calcula níveis SMC (Support, Resistance, Supply, Demand, etc)
        """
        
        # Preços simulados (em produção: viria do MT5)
        preco_atual = 123.45
        
        # Support e Resistance (simplified)
        support_1 = preco_atual - 1.85
        support_2 = preco_atual - 3.50
        resistance_1 = preco_atual + 2.45
        resistance_2 = preco_atual + 4.10
        
        # Supply e Demand Zones
        supply_zone_low = resistance_1
        supply_zone_high = resistance_1 + 1.00
        demand_zone_low = support_1 - 1.00
        demand_zone_high = support_1
        
        # Fair Value Gap (preço entre S1 e suporte)
        fvg_low = support_1 - 0.30
        fvg_high = support_1 + 0.35
        
        # Premium/Discount
        if preco_atual > (support_1 + resistance_1) / 2:
            market_phase = "PREMIUM 📈"
            setup_type = "Possível retracement para demanda"
        else:
            market_phase = "DISCOUNT 📉"
            setup_type = "Possível push para oferta"
        
        return {
            'preco_atual': preco_atual,
            'support_1': round(support_1, 2),
            'support_2': round(support_2, 2),
            'resistance_1': round(resistance_1, 2),
            'resistance_2': round(resistance_2, 2),
            'supply_zone': {
                'low': round(supply_zone_low, 2),
                'high': round(supply_zone_high, 2),
                'label': 'PREMIUM'
            },
            'demand_zone': {
                'low': round(demand_zone_low, 2),
                'high': round(demand_zone_high, 2),
                'label': 'DISCOUNT'
            },
            'fair_value_gap': {
                'low': round(fvg_low, 2),
                'high': round(fvg_high, 2),
                'oportunidade': 'Possível FVG trade'
            },
            'market_phase': market_phase,
            'setup_recomendado': setup_type
        }
    
    def gerar_recomendacao(self):
        """Gera recomendação baseada em todas as análises"""
        
        market = self.calcular_market_strength()
        probability = self.calcular_probability_buyer_seller()
        smc = self.calcular_smc_levels()
        
        # Lógica de recomendação
        if market['overall'] >= 65 and probability['buy_probability'] >= 60:
            recomendacao = "BUY 🟢"
            entrada = smc['support_1']
            alvo = smc['resistance_1']
            stop = smc['support_2']
        elif market['overall'] >= 65 and probability['sell_probability'] >= 60:
            recomendacao = "SELL 🔴"
            entrada = smc['resistance_1']
            alvo = smc['support_1']
            stop = smc['resistance_2']
        else:
            recomendacao = "AGUARDAR 🟡"
            entrada = None
            alvo = None
            stop = None
        
        risco_recompensa = None
        if entrada and alvo and stop:
            risco = abs(entrada - stop)
            recompensa = abs(alvo - entrada)
            if risco > 0:
                risco_recompensa = round(recompensa / risco, 2)
        
        return {
            'setup': recomendacao,
            'entrada': entrada,
            'alvo': alvo,
            'stop': stop,
            'risco_recompensa': risco_recompensa,
            'confianca': f"{min(100, market['overall'] + probability['buy_probability']) // 2}%"
        }

# Funções de utilidade
def gerar_analise_completa():
    """Gera análise técnica completa para o monitor"""
    
    analise = AnaliseTecnica()
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'market_strength': analise.calcular_market_strength(),
        'probability': analise.calcular_probability_buyer_seller(),
        'smc_levels': analise.calcular_smc_levels(),
        'recomendacao': analise.gerar_recomendacao()
    }

if __name__ == '__main__':
    # Test
    resultado = gerar_analise_completa()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
