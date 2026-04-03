"""
Singleton Loader para configurações de Profit Protection.

Responsabilidades:
- Carregar e validar o arquivo YAML de configuração.
- Fornecer um ponto de acesso único (singleton) para a configuração.
- Implementar cache para evitar leituras repetidas do arquivo.
- Detectar mudanças no arquivo para recarregamento automático.
- Fornecer fallback seguro para configurações padrão se o arquivo falhar.
- Resolver perfis com precedência (defaults -> profile -> override).

ADR: ADR-018
"""
import logging
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError

from src.infrastructure.config.profit_protection_config import (
    ProfitProtectionConfig,
    ProfitProtectionProfile,
    _DEFAULTS_BUILTIN,
)

logger = logging.getLogger(__name__)

_YAML_PATH_DEFAULT = (
    Path(__file__).parent.parent.parent.parent / "config" / "profit_protection.yaml"
)


class ConfigLoader:
    """
    Singleton thread-safe para carregar, validar e fornecer perfis de Profit Protection.
    """
    _instance: Optional["ConfigLoader"] = None
    _lock = threading.Lock()

    def __init__(self, yaml_path: Optional[Path] = None):
        if not hasattr(self, 'initialized'):
            self.yaml_path = yaml_path or _YAML_PATH_DEFAULT
            self._last_mtime: Optional[float] = None
            self._config: Optional[ProfitProtectionConfig] = None
            self.initialized = True
            logger.info(f"[ConfigLoader] Singleton inicializado | yaml_path={self.yaml_path}")

    @classmethod
    def get_instance(cls, yaml_path: Optional[Path] = None) -> "ConfigLoader":
        """Retorna a instância singleton do ConfigLoader."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(yaml_path)
        return cls._instance

    def _carregar_e_validar_yaml(self) -> ProfitProtectionConfig:
        """
        Carrega o arquivo YAML, valida com Pydantic e retorna o objeto de configuração.
        Usa fallback seguro se o arquivo não existir ou for inválido.
        """
        try:
            if not self.yaml_path.exists():
                logger.warning(f"Arquivo de configuração não encontrado em {self.yaml_path}. Usando defaults builtin.")
                return ProfitProtectionConfig(profiles={"baseline": ProfitProtectionProfile(**_DEFAULTS_BUILTIN, nome="Baseline (builtin)")})

            with open(self.yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not data:
                    raise ValueError("Arquivo YAML está vazio.")

                config = ProfitProtectionConfig(**data)
                logger.info(f"Configuração '{self.yaml_path}' carregada e validada com sucesso. Versão: {config.version}")
                return config

        except (ValidationError, yaml.YAMLError, ValueError) as e:
            logger.error(f"Erro ao carregar ou validar {self.yaml_path}: {e}. Usando defaults builtin.")
            return ProfitProtectionConfig(profiles={"baseline": ProfitProtectionProfile(**_DEFAULTS_BUILTIN, nome="Baseline (builtin)")})

    def _get_config(self) -> ProfitProtectionConfig:
        """
        Retorna a configuração, recarregando do arquivo se ele foi modificado.
        """
        try:
            current_mtime = self.yaml_path.stat().st_mtime if self.yaml_path.exists() else None
        except FileNotFoundError:
            current_mtime = None

        # A verificação de `self._config is None` garante o primeiro carregamento.
        # A comparação de mtime garante o recarregamento em caso de mudança.
        if self._config is None or (current_mtime is not None and current_mtime != self._last_mtime):
            logger.info(
                f"Detectada mudança no arquivo de configuração (mtime: {self._last_mtime} -> {current_mtime}) ou primeiro carregamento. Recarregando..."
            )
            # Limpa o cache do resolver de perfil para forçar a re-resolução com os novos dados
            self.get_profile.cache_clear()

            # Carrega a nova configuração do arquivo
            self._config = self._carregar_e_validar_yaml()

            # Atualiza o timestamp da última modificação conhecida
            self._last_mtime = current_mtime

        return self._config

    @lru_cache(maxsize=32)
    def get_profile(
        self,
        profile_name: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> ProfitProtectionProfile:
        """
        Resolve e retorna o perfil de proteção de lucro apropriado com base na precedência.

        Precedência:
        1. Override específico do agente (`agent_overrides`).
        2. Perfil ativo (`profile_ativo` no YAML ou `profile_name` do argumento).
        3. Perfil 'baseline' do YAML.
        4. Defaults internos (se tudo mais falhar).

        Args:
            profile_name: Nome do perfil a ser carregado. Se None, usa o `profile_ativo` do YAML.
            agent_id: ID do agente para verificar se há um override.

        Returns:
            Um objeto ProfitProtectionProfile validado.
        """
        config = self._get_config()

        final_profile_name = profile_name or config.profile_ativo

        # 1. Verificar override do agente
        if agent_id and agent_id in config.agent_overrides:
            override = config.agent_overrides[agent_id]
            if "profile" in override and override["profile"] in config.profiles:
                final_profile_name = override["profile"]
                logger.debug(f"Override para agent_id '{agent_id}' encontrado. Usando perfil '{final_profile_name}'.")

        # 2. Obter o perfil
        profile_data = config.profiles.get(final_profile_name)

        if not profile_data:
            logger.warning(f"Perfil '{final_profile_name}' não encontrado. Usando perfil 'baseline'.")
            profile_data = config.profiles.get("baseline")

        # 3. Fallback final para builtin se 'baseline' também não existir (improvável)
        if not profile_data:
            logger.error("Nenhum perfil 'baseline' encontrado na configuração. Usando defaults internos como último recurso.")
            return ProfitProtectionProfile(**_DEFAULTS_BUILTIN, nome="Baseline (builtin)")

        return profile_data

    def get_shadow_mode(self) -> bool:
        """Retorna o estado do shadow_mode da configuração."""
        config = self._get_config()
        return config.shadow_mode
