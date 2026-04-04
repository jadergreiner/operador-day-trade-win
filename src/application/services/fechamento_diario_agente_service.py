"""
BLID-029: Fechamento Diario Individualizado por Agente RL.

Responsabilidades:
- Consultar tabela `trades` em `data/db/trading.db` filtrada por magic_number e data
- Calcular metricas de fechamento por agente: win_rate, pnl, drawdown, status
- Gerar relatorio Markdown por agente em outputs/diarios/

Agentes suportados:
    rl_5000 (magic=234500) | rl_direto (magic=234600)

Pipeline:
    fechar_diario_por_agente.py
    -> FechamentoDiarioAgenteService.gerar_relatorio(agent_name, magic, data, db_path)
    -> FechamentoDiarioAgenteService.gerar_markdown(relatorio, outputs_dir)
    -> outputs/diarios/fechamento_{agent}_{YYYYMMDD}.md

ADR: ADR-012 (magic numbers), ADR-001 (SQLite direto), ADR-019 (segregacao de bancos)
Status: Implementacao v1.0 (06/04/2026)
"""
from __future__ import annotations

import dataclasses
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from config.settings import AGENT_MAGIC_NUMBERS

# ---------------------------------------------------------------------------
# Constantes internas
# ---------------------------------------------------------------------------

_QUERY_TRADES = """
    SELECT side, entry_time, exit_time, profit_loss
    FROM trades
    WHERE magic_number = ?
      AND date(entry_time) = ?
      AND exit_time IS NOT NULL
      AND profit_loss IS NOT NULL
    ORDER BY entry_time ASC
"""

_PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA busy_timeout=30000;",
]


# ---------------------------------------------------------------------------
# Dataclass de relatorio
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class RelatorioFechamentoDiarioAgente:
    """Relatorio de fechamento diario de um agente RL.

    Campos:
        session_id: identificador unico no formato {agent_name}_{data}_{magic_number}
        magic_number: numero magico do agente (EA ID do MT5)
        agent_name: nome do agente (ex: rl_5000, rl_direto)
        data: data da sessao no formato YYYY-MM-DD
        total_trades: quantidade de trades fechados com profit_loss valido
        win_rate: taxa de acerto entre 0.0 e 1.0
        pnl_total_reais: lucro/prejuizo total em reais
        drawdown_max_sessao: maior drawdown da equity curve da sessao (>= 0)
        horario_primeiro_trade: horario do primeiro trade (HH:MM:SS) ou None
        horario_ultimo_trade: horario do ultimo trade (HH:MM:SS) ou None
        status: LUCRATIVO, DEFICITARIO ou NEUTRO
        schema_version: versao do schema do relatorio
        gerado_em: timestamp de geracao em ISO UTC
    """

    session_id: str
    magic_number: int
    agent_name: str
    data: str
    total_trades: int
    win_rate: float
    pnl_total_reais: float
    drawdown_max_sessao: float
    horario_primeiro_trade: Optional[str]
    horario_ultimo_trade: Optional[str]
    status: str
    schema_version: str = "1.0"
    gerado_em: str = dataclasses.field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Service principal
# ---------------------------------------------------------------------------


class FechamentoDiarioAgenteService:
    """Service de fechamento diario por agente RL.

    Responsavel por:
    - Consultar trades do banco SQLite filtrados por magic_number e data
    - Calcular metricas da sessao (win_rate, pnl, drawdown, status)
    - Gerar relatorio Markdown em outputs/diarios/
    """

    # Conjunto de magic numbers validos (derivado de settings — ADR-012)
    _MAGICS_VALIDOS: frozenset[int] = frozenset(AGENT_MAGIC_NUMBERS.values())

    def gerar_relatorio(
        self,
        agent_name: str,
        magic_number: int,
        data: str,
        db_path: Path,
    ) -> RelatorioFechamentoDiarioAgente:
        """Gerar relatorio de fechamento diario para o agente informado.

        Args:
            agent_name: nome do agente (ex: rl_5000, rl_direto)
            magic_number: numero magico do agente no MT5 (de AGENT_MAGIC_NUMBERS)
            data: data da sessao no formato YYYY-MM-DD
            db_path: caminho para o banco SQLite trading.db

        Returns:
            RelatorioFechamentoDiarioAgente com todas as metricas calculadas

        Raises:
            FileNotFoundError: se db_path nao existir
            ValueError: se magic_number nao estiver em AGENT_MAGIC_NUMBERS
            ValueError: se data for futura (maior que hoje)
        """
        # --- Validacoes de entrada ---
        if not db_path.exists():
            raise FileNotFoundError(
                f"Banco de dados nao encontrado: {db_path}"
            )

        if magic_number not in self._MAGICS_VALIDOS:
            raise ValueError(
                f"magic_number {magic_number} invalido — "
                f"deve ser um dos valores em AGENT_MAGIC_NUMBERS: {dict(AGENT_MAGIC_NUMBERS)}"
            )

        data_date = date.fromisoformat(data)
        if data_date.year > date.today().year:
            raise ValueError(
                f"data {data!r} invalida — data em ano futuro nao permitida (hoje: {date.today()})"
            )

        # --- Consulta ao banco ---
        trades = self._consultar_trades(db_path, magic_number, data)

        # --- Calculo das metricas ---
        total_trades = len(trades)

        if total_trades == 0:
            win_rate = 0.0
            pnl_total = 0.0
            drawdown_max = 0.0
            horario_primeiro = None
            horario_ultimo = None
            status = "NEUTRO"
        else:
            profits = [row[3] for row in trades]
            wins = sum(1 for p in profits if p > 0.0)
            win_rate = wins / total_trades
            pnl_total = sum(profits)
            drawdown_max = self._calcular_drawdown_max(profits)

            # Horarios extraidos do entry_time (formato "YYYY-MM-DD HH:MM:SS")
            horario_primeiro = self._extrair_horario(trades[0][1])
            horario_ultimo = self._extrair_horario(trades[-1][1])

            # Determinacao do status
            if pnl_total > 0.0:
                status = "LUCRATIVO"
            elif pnl_total < 0.0:
                status = "DEFICITARIO"
            else:
                status = "NEUTRO"

        session_id = f"{agent_name}_{data}_{magic_number}"

        return RelatorioFechamentoDiarioAgente(
            session_id=session_id,
            magic_number=magic_number,
            agent_name=agent_name,
            data=data,
            total_trades=total_trades,
            win_rate=win_rate,
            pnl_total_reais=pnl_total,
            drawdown_max_sessao=drawdown_max,
            horario_primeiro_trade=horario_primeiro,
            horario_ultimo_trade=horario_ultimo,
            status=status,
        )

    def gerar_markdown(
        self,
        relatorio: RelatorioFechamentoDiarioAgente,
        outputs_dir: Path,
    ) -> Path:
        """Gerar relatorio Markdown para o fechamento diario do agente.

        O arquivo e sobrescrito caso ja exista (operacao idempotente).

        Args:
            relatorio: dataclass com metricas calculadas
            outputs_dir: diretorio de saida (criado se nao existir)

        Returns:
            Path do arquivo Markdown gerado
        """
        outputs_dir.mkdir(parents=True, exist_ok=True)

        data_sem_hifen = relatorio.data.replace("-", "")
        nome_arquivo = f"fechamento_{relatorio.agent_name}_{data_sem_hifen}.md"
        caminho_arquivo = outputs_dir / nome_arquivo

        conteudo = self._montar_conteudo_markdown(relatorio)

        caminho_arquivo.write_text(conteudo, encoding="utf-8")
        return caminho_arquivo

    def _calcular_drawdown_max(self, profits: list[float]) -> float:
        """Calcular o maximo drawdown da equity curve da sessao.

        Algoritmo:
        - Acumula os profits sequencialmente (equity curve)
        - Rastreia o pico corrente da equity
        - Drawdown em cada ponto = peak - equity_corrente
        - Retorna o maior drawdown encontrado

        Args:
            profits: lista de lucros/prejuizos ordenada por entrada

        Returns:
            Maximo drawdown >= 0.0; retorna 0.0 para lista vazia
        """
        if not profits:
            return 0.0

        equity = 0.0
        peak = 0.0
        drawdown_max = 0.0

        for lucro in profits:
            equity += lucro
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            if drawdown > drawdown_max:
                drawdown_max = drawdown

        return drawdown_max

    # ---------------------------------------------------------------------------
    # Metodos privados auxiliares
    # ---------------------------------------------------------------------------

    def _consultar_trades(
        self,
        db_path: Path,
        magic_number: int,
        data: str,
    ) -> list[tuple[str, str, str, float]]:
        """Consultar trades no banco SQLite filtrados por magic_number e data.

        Args:
            db_path: caminho do banco SQLite
            magic_number: numero magico do agente
            data: data da sessao (YYYY-MM-DD)

        Returns:
            Lista de tuplas (side, entry_time, exit_time, profit_loss)
            ordenadas por entry_time ASC
        """
        conn = sqlite3.connect(
            str(db_path),
            timeout=30,
            check_same_thread=False,
        )
        try:
            for pragma in _PRAGMAS:
                conn.execute(pragma)
            cursor = conn.execute(_QUERY_TRADES, (magic_number, data))
            return cursor.fetchall()  # type: ignore[return-value]
        finally:
            conn.close()

    @staticmethod
    def _extrair_horario(entry_time: str) -> str:
        """Extrair a parte de horario de um entry_time no formato 'YYYY-MM-DD HH:MM:SS'.

        Args:
            entry_time: timestamp completo da entrada

        Returns:
            String no formato HH:MM:SS
        """
        partes = entry_time.split(" ")
        if len(partes) >= 2:
            return partes[1]
        return entry_time

    @staticmethod
    def _montar_conteudo_markdown(
        relatorio: RelatorioFechamentoDiarioAgente,
    ) -> str:
        """Montar conteudo Markdown do relatorio de fechamento diario.

        Args:
            relatorio: dataclass com todas as metricas

        Returns:
            String com conteudo Markdown formatado
        """
        win_rate_pct = f"{relatorio.win_rate * 100:.1f}%"
        pnl_str = f"R$ {relatorio.pnl_total_reais:+.2f}"
        dd_str = f"R$ {relatorio.drawdown_max_sessao:.2f}"

        linhas = [
            f"# Fechamento Diario — {relatorio.agent_name} — {relatorio.data}",
            "",
            "## Resumo da Sessao",
            "",
            "| Campo | Valor |",
            "|---|---|",
            f"| **Agente** | {relatorio.agent_name} |",
            f"| **Magic Number** | {relatorio.magic_number} |",
            f"| **Data** | {relatorio.data} |",
            f"| **Session ID** | {relatorio.session_id} |",
            f"| **Total Trades** | {relatorio.total_trades} |",
            f"| **Win Rate** | {win_rate_pct} |",
            f"| **PnL Total** | {pnl_str} |",
            f"| **Drawdown Max Sessao** | {dd_str} |",
            f"| **Primeiro Trade** | {relatorio.horario_primeiro_trade or 'N/A'} |",
            f"| **Ultimo Trade** | {relatorio.horario_ultimo_trade or 'N/A'} |",
            f"| **Status** | **{relatorio.status}** |",
            "",
            "## Metadados",
            "",
            "| Campo | Valor |",
            "|---|---|",
            f"| **Schema Version** | {relatorio.schema_version} |",
            f"| **Gerado Em** | {relatorio.gerado_em} |",
            "",
        ]

        return "\n".join(linhas)
