"""
Configuracao de backtest para P0-2 validacao.

Este modulo carrega configuracoes via YAML e valida parametros.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class BacktestConfigYAML:
    """Configuracao de backtest carregada de YAML."""

    dataset_path: str
    lookback_period: int
    test_split: float
    cv_folds: int
    features_count: int
    output_path: str
    model_path: Optional[str]

    # Gate 2 criteria
    sharpe_target: float
    win_rate_target: float
    max_drawdown_target: float
    consistency_sigma_target: float

    # Executors
    enable_walk_forward: bool
    enable_shap_analysis: bool
    enable_regime_analysis: bool

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "BacktestConfigYAML":
        """Carrega configuracao de arquivo YAML."""
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)

        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Retorna configuracao como dict."""
        return {
            'dataset_path': self.dataset_path,
            'lookback_period': self.lookback_period,
            'test_split': self.test_split,
            'cv_folds': self.cv_folds,
            'features_count': self.features_count,
            'output_path': self.output_path,
            'model_path': self.model_path,
            'sharpe_target': self.sharpe_target,
            'win_rate_target': self.win_rate_target,
            'max_drawdown_target': self.max_drawdown_target,
            'consistency_sigma_target': self.consistency_sigma_target,
            'enable_walk_forward': self.enable_walk_forward,
            'enable_shap_analysis': self.enable_shap_analysis,
            'enable_regime_analysis': self.enable_regime_analysis,
        }


# Configuracao padrao (default)
DEFAULT_CONFIG = {
    'dataset_path': 'data/training_dataset.csv',
    'lookback_period': 252,
    'test_split': 0.2,
    'cv_folds': 5,
    'features_count': 24,
    'output_path': 'data/backtest',
    'model_path': None,

    'sharpe_target': 1.0,
    'win_rate_target': 0.59,
    'max_drawdown_target': 0.15,
    'consistency_sigma_target': 0.30,

    'enable_walk_forward': True,
    'enable_shap_analysis': True,
    'enable_regime_analysis': True,
}


def load_config(yaml_path: Optional[str] = None) -> BacktestConfigYAML:
    """
    Carrega configuracao de arquivo YAML ou usa default.

    Args:
        yaml_path: Caminho para YAML (usa default se None)

    Returns:
        Configuracao carregada
    """
    if yaml_path and Path(yaml_path).exists():
        return BacktestConfigYAML.from_yaml(yaml_path)
    else:
        return BacktestConfigYAML(**DEFAULT_CONFIG)
