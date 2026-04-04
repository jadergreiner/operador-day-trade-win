"""
Loader tipado para config/profit_protection.yaml.

Responsabilidades:
- Carregar e validar o YAML com esquema Pydantic.
- Resolver o perfil ativo por precedência:
    defaults -> profiles[profile_ativo] -> agent_overrides[agent_id]
- Fornecer fallback para baseline builtin quando o arquivo estiver ausente.
- Rejeitar explicitamente configurações fora de faixa (fail-fast no boot).

ADR: ADR-018
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

# ============================================================
# DEFAULTS BUILTIN — espelham o motor original pré-governança.
# Usados quando o YAML está ausente ou inválido.
# ============================================================
_DEFAULTS_BUILTIN: dict[str, Any] = {
    "profit_target_pct": 2.0,
    "stop_loss_pct": 1.0,
    "partial_close_pct": 0.75,
    "break_even_offset_pct": 0.10,
    "reversao_threshold_pct": 0.75,
    "cooldown_seconds": 5,
}

_YAML_PATH_DEFAULT = (
    Path(__file__).parent.parent.parent.parent / "config" / "profit_protection.yaml"
)


# ============================================================
# SCHEMA PYDANTIC
# ============================================================


class ProfitProtectionProfile(BaseModel):
    """Schema de um perfil de proteção de lucro.

    Contrato de unidade: TODOS os valores _pct são porcentagem absoluta.
        2.0 = 2%  |  0.10 = 0.10%  |  NUNCA 0.02 para 2%.
    """

    nome: str = Field(default="")
    profit_target_pct: float = Field(
        default=2.0,
        gt=0.0,
        le=100.0,
        description="Alvo de lucro em % absoluto (ex: 2.0 = 2%)",
    )
    stop_loss_pct: float = Field(
        default=1.0,
        gt=0.0,
        le=100.0,
        description="Limite de prejuízo em % absoluto",
    )
    partial_close_pct: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Fração do target para sugerir fechamento parcial (0.0 = desativado)",
    )
    break_even_offset_pct: float = Field(
        default=0.10,
        ge=0.0,
        le=100.0,
        description="Offset do break-even stop em % absoluto",
    )
    reversao_threshold_pct: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Fração de reversão para ativar alerta (0.75 = 75% do máximo)",
    )
    cooldown_seconds: int = Field(
        default=5,
        ge=0,
        le=3600,
        description="Mínimo de segundos entre sinais para o mesmo trade",
    )

    @model_validator(mode="after")
    def validar_consistencia(self) -> "ProfitProtectionProfile":
        """Garante que partial_close_pct * profit_target_pct > break_even_offset."""
        if self.partial_close_pct > 0.0:
            partial_trigger = self.profit_target_pct * self.partial_close_pct
            if partial_trigger <= self.break_even_offset_pct:
                raise ValueError(
                    f"partial_close_pct ({self.partial_close_pct}) * "
                    f"profit_target_pct ({self.profit_target_pct}) = "
                    f"{partial_trigger:.3f} deve ser > "
                    f"break_even_offset_pct ({self.break_even_offset_pct})"
                )
        return self

    def as_engine_kwargs(self) -> dict[str, Any]:
        """Retorna dict pronto para passar ao ProfitProtectionEngine.__init__."""
        return {
            "profit_target_pct": self.profit_target_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "partial_close_pct": self.partial_close_pct,
            "break_even_offset_pct": self.break_even_offset_pct,
            "reversao_threshold_pct": self.reversao_threshold_pct,
            "cooldown_seconds": self.cooldown_seconds,
        }


class ProfitProtectionConfig(BaseModel):
    """Schema raiz do arquivo profit_protection.yaml."""

    version: str = Field(default="1.0.0")
    profile_ativo: str = Field(default="baseline")
    shadow_mode: bool = Field(default=False)
    profiles: dict[str, ProfitProtectionProfile] = Field(default_factory=dict)
    agent_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def garantir_baseline(self) -> "ProfitProtectionConfig":
        """Garante que o perfil baseline sempre existe."""
        if "baseline" not in self.profiles:
            self.profiles["baseline"] = ProfitProtectionProfile(
                **_DEFAULTS_BUILTIN, nome="Baseline (builtin)"
            )
        return self


# Rebuild Pydantic models para resolver referências forward
ProfitProtectionConfig.model_rebuild()


# ============================================================
# LOADER
# ============================================================


def carregar_config(
    yaml_path: Optional[Path] = None,
) -> ProfitProtectionConfig:
    """Carrega e valida o arquivo YAML de proteção de lucro.

    Fallback seguro: se o arquivo estiver ausente, retorna config com
    apenas o perfil baseline (valores originais do motor).

    Args:
        yaml_path: Caminho do YAML. Se None usa o padrão do projeto.

    Returns:
        ProfitProtectionConfig validada.
    """
    path = yaml_path or _YAML_PATH_DEFAULT

    if not path.exists():
        logger.warning(
            "[ProfitProtectionConfig] Arquivo '%s' não encontrado. "
            "Usando perfil baseline builtin como fallback.",
            path,
        )
        return _config_baseline_builtin()

    try:
        with open(path, encoding="utf-8") as fh:
            dados = yaml.safe_load(fh)

        cfg = ProfitProtectionConfig.model_validate(dados or {})
        logger.info(
            "[ProfitProtectionConfig] Config carregada: version=%s profile_ativo=%s shadow=%s",
            cfg.version,
            cfg.profile_ativo,
            cfg.shadow_mode,
        )
        return cfg
    except Exception as exc:
        logger.error(
            "[ProfitProtectionConfig] Falha ao carregar '%s': %s — "
            "abortando; corrija o YAML ou remova o arquivo para usar baseline builtin.",
            path,
            exc,
        )
        raise


def resolver_perfil(
    cfg: ProfitProtectionConfig,
    agent_id: Optional[str] = None,
    profile_env: Optional[str] = None,
) -> ProfitProtectionProfile:
    """Resolve o perfil ativo por precedência.

    Ordem de precedência (maior vence):
        1. agent_overrides[agent_id].profile (se existir)
        2. PROFIT_PROTECTION_PROFILE (env var / profile_env)
        3. cfg.profile_ativo (do YAML)
        4. "baseline" (hardcoded final)

    Args:
        cfg: Config carregada.
        agent_id: ID do agente em execução (ex: "agente_direto_20260402").
        profile_env: Valor da variável de ambiente PROFIT_PROTECTION_PROFILE.

    Returns:
        ProfitProtectionProfile resolvido.

    Raises:
        KeyError: Se o perfil não existir nos profiles definidos
                  e não houver fallback disponível. (Não deve acontecer,
                  pois baseline é sempre garantido.)
    """
    # Resolver precedência do nome do perfil
    nome_perfil = cfg.profile_ativo  # Nível 3: default do YAML

    # Nível 2: Override por env var
    env_profile = profile_env or os.environ.get("PROFIT_PROTECTION_PROFILE", "")
    if env_profile:
        nome_perfil = env_profile
        logger.debug(
            "[ProfitProtectionConfig] Override por env PROFIT_PROTECTION_PROFILE='%s'",
            nome_perfil,
        )

    # Nível 1: Override por agente (maior precedência - vence ENV)
    if agent_id and agent_id in cfg.agent_overrides:
        override = cfg.agent_overrides[agent_id]
        if "profile" in override:
            nome_perfil = str(override["profile"])
            logger.debug(
                "[ProfitProtectionConfig] Override de agente '%s' → profile '%s' (maior precedência)",
                agent_id,
                nome_perfil,
            )

    # Resolver perfil — fallback para baseline se inexistente
    if nome_perfil not in cfg.profiles:
        logger.critical(
            "[ProfitProtectionConfig] Perfil '%s' não encontrado em profiles. "
            "Fazendo fallback para baseline.",
            nome_perfil,
        )
        nome_perfil = "baseline"

    perfil = cfg.profiles[nome_perfil]
    logger.info(
        "[ProfitProtectionConfig] Perfil resolvido: '%s' | "
        "profit_target=%.2f%% | break_even=%.2f%% | shadow=%s",
        nome_perfil,
        perfil.profit_target_pct,
        perfil.break_even_offset_pct,
        cfg.shadow_mode,
    )
    return perfil


def _config_baseline_builtin() -> ProfitProtectionConfig:
    """Retorna config mínima com apenas o perfil baseline builtin."""
    return ProfitProtectionConfig(
        profiles={"baseline": ProfitProtectionProfile(**_DEFAULTS_BUILTIN, nome="Baseline (builtin)")}
    )
