"""Value Objects para a camada de gerenciamento de risco externo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any


@dataclass(frozen=True)
class ConfiguracaoCooldown:
    """
    Configuracao do periodo de espera entre operacoes por agente.

    Atributos:
        periodo_espera_segundos: Segundos a aguardar apos fechar posicao.
    """

    periodo_espera_segundos: int

    def __post_init__(self) -> None:
        if self.periodo_espera_segundos <= 0:
            raise ValueError(
                f"periodo_espera_segundos deve ser positivo, "
                f"recebido: {self.periodo_espera_segundos}"
            )


@dataclass(frozen=True)
class ConfiguracaoSLMaximo:
    """
    Configuracao do stop loss maximo permitido por operacao.

    Atributos:
        perda_maxima_por_operacao_reais: Perda maxima em R$ por trade.
        valor_ponto: Valor em R$ de cada ponto (WINFUT = 0.20).
    """

    perda_maxima_por_operacao_reais: float
    valor_ponto: float = 0.20

    def __post_init__(self) -> None:
        if self.perda_maxima_por_operacao_reais <= 0:
            raise ValueError(
                f"perda_maxima_por_operacao_reais deve ser positivo, "
                f"recebido: {self.perda_maxima_por_operacao_reais}"
            )
        if self.valor_ponto <= 0:
            raise ValueError(
                f"valor_ponto deve ser positivo, recebido: {self.valor_ponto}"
            )


@dataclass(frozen=True)
class ConfiguracaoHorario:
    """
    Configuracao da janela de horario de operacao.

    Atributos:
        hora_inicio: Horario minimo para abertura de novas posicoes.
        hora_fim: Horario maximo para abertura de novas posicoes.
        bloquear_abertura_apos_fim: Se True, bloqueia novas entradas apos hora_fim.
        fechar_posicao_no_fim: Se True, sinaliza fechamento de posicoes em hora_fim.
        fuso_horario: Fuso horario IANA (padrao America/Sao_Paulo).
    """

    hora_inicio: time
    hora_fim: time
    bloquear_abertura_apos_fim: bool = True
    fechar_posicao_no_fim: bool = True
    fuso_horario: str = "America/Sao_Paulo"

    def __post_init__(self) -> None:
        if self.hora_fim <= self.hora_inicio:
            raise ValueError(
                f"hora_fim ({self.hora_fim}) deve ser posterior a "
                f"hora_inicio ({self.hora_inicio})"
            )


@dataclass(frozen=True)
class ConfiguracaoGanhoDiario:
    """
    Configuracao do limitador de ganho diario global.

    Atributos:
        limite_ganho_diario_reais: Teto de ganho em R$ para o pregao.
        congelar_novas_entradas: Se True, bloqueia novas posicoes ao atingir limite.
            Fechamentos de posicoes abertas sempre sao permitidos.
    """

    limite_ganho_diario_reais: float
    congelar_novas_entradas: bool = True

    def __post_init__(self) -> None:
        if self.limite_ganho_diario_reais <= 0:
            raise ValueError(
                f"limite_ganho_diario_reais deve ser positivo, "
                f"recebido: {self.limite_ganho_diario_reais}"
            )


@dataclass(frozen=True)
class EventoCalendario:
    """
    Representa um evento do calendario economico.

    Atributos:
        nome: Nome do evento (ex: 'COPOM', 'NFP').
        timestamp_evento: Data e hora do evento.
        minutos_antes_fechar: Minutos antes do evento para fechar posicoes.
        minutos_apos_abrir: Minutos apos o evento para reabrir operacoes.
    """

    nome: str
    timestamp_evento: datetime
    minutos_antes_fechar: int = 5
    minutos_apos_abrir: int = 2

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise ValueError("nome do evento nao pode ser vazio")
        if self.minutos_antes_fechar < 0:
            raise ValueError(
                f"minutos_antes_fechar deve ser >= 0, "
                f"recebido: {self.minutos_antes_fechar}"
            )
        if self.minutos_apos_abrir < 0:
            raise ValueError(
                f"minutos_apos_abrir deve ser >= 0, "
                f"recebido: {self.minutos_apos_abrir}"
            )


@dataclass(frozen=True)
class ResultadoGateRisco:
    """
    Resultado da avaliacao de um gate de risco individual.

    Atributos:
        aprovado: True se o gate liberou a operacao.
        codigo_gate: Identificador do gate (ex: 'COOLDOWN', 'SL_MAXIMO').
        motivo: Descricao textual da decisao.
        detalhes: Informacoes adicionais para auditoria.
    """

    aprovado: bool
    codigo_gate: str
    motivo: str
    detalhes: dict[str, Any] = field(default_factory=dict)
