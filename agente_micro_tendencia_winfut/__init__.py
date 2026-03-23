# -*- coding: utf-8 -*-
"""
Pacote agente_micro_tendencia_winfut

Re-exporta componentes do script principal para compatibilidade de imports.
Usa importlib para evitar conflito de namespace com a pasta.
"""

import importlib.util
import os
import sys

# Caminho do script original
_script_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "scripts",
    "agente_micro_tendencia_winfut.py"
)

# Carrega o modulo diretamente do arquivo
_spec = importlib.util.spec_from_file_location(
    "agente_micro_tendencia_winfut_script",
    _script_path
)
_module = importlib.util.module_from_spec(_spec)
sys.modules["agente_micro_tendencia_winfut_script"] = _module
_spec.loader.exec_module(_module)

# Re-exporta os componentes principais
MicroTradingManager = _module.MicroTradingManager
main = _module.main
_connect_mt5 = _module._connect_mt5
_get_config = _module._get_config
AUTO_TRADING_ENABLED = _module.AUTO_TRADING_ENABLED
SYMBOL = _module.SYMBOL
_calc_vwap_from_candles = _module._calc_vwap_from_candles
_calc_pivot_levels = _module._calc_pivot_levels
_get_prev_day_hlc = _module._get_prev_day_hlc
_calc_momentum = _module._calc_momentum
_detect_smc = _module._detect_smc
_create_micro_trend_tables = _module._create_micro_trend_tables

__all__ = [
    "MicroTradingManager",
    "main",
    "_connect_mt5",
    "_get_config",
    "AUTO_TRADING_ENABLED",
    "SYMBOL",
    "_calc_vwap_from_candles",
    "_calc_pivot_levels",
    "_get_prev_day_hlc",
    "_calc_momentum",
    "_detect_smc",
    "_create_micro_trend_tables",
]

