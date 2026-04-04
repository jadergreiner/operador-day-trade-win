"""Servico de Diagnostico de Saude Pre-Sessao dos Diarios.

BLID-028 / ROADMAP-DIARIOS-08
Executor: INICIAR_DIARIOS.bat

Detecta problemas nos bancos de dados antes de iniciar a sessao de trading,
prevenindo perda de dados e falhas silenciosas durante o pregao.

Banco alvo: data/db/trading_diarios.db (ADR-019, magic_number=234800).
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("diarios_health_check_service")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_SQLITE_TIMEOUT: int = 30

# Bancos obrigatorios do agente Diarios
_BANCOS_OBRIGATORIOS: tuple[str, ...] = (
    "trading_diarios.db",
)

# Tabelas obrigatorias no banco principal
_TABELAS_OBRIGATORIAS: tuple[str, ...] = (
    "trading_journal_logs",
    "journal_trade_correlation",
    "ai_reflection_logs",
    "reflection_questions",
    "diary_feedback",
)

# Niveis de severidade do diagnostico
_STATUS_OK = "OK"
_STATUS_WARNING = "WARNING"
_STATUS_CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------


class DiariosHealthCheckService:
    """Servico de verificacao de saude dos bancos de dados dos Diarios.

    Executa verificacoes de existencia, integridade estrutural e
    atualidade dos dados antes de iniciar a sessao de trading.

    Banco alvo: data/db/trading_diarios.db (ADR-019, magic_number=234800).
    """

    # ------------------------------------------------------------------
    # Conexao interna
    # ------------------------------------------------------------------

    @staticmethod
    def _conectar(db_path: Path) -> sqlite3.Connection:
        """Abre conexao SQLite com PRAGMAs otimizados para WAL.

        Args:
            db_path: Caminho para o arquivo SQLite.

        Returns:
            Conexao configurada com timeout=30, WAL e busy_timeout=30000.
        """
        conn = sqlite3.connect(str(db_path), timeout=_SQLITE_TIMEOUT)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    # ------------------------------------------------------------------
    # Verificacoes elementares
    # ------------------------------------------------------------------

    def verificar_bancos(self, db_path: Path) -> dict[str, bool]:
        """Verifica existencia dos bancos de dados obrigatorios.

        Checa se o arquivo do banco principal existe e nao esta corrompido
        (abertura sem erros de integridade).

        Args:
            db_path: Caminho para o banco principal (data/db/trading_diarios.db).

        Returns:
            Dicionario {nome_banco: existe} para cada banco obrigatorio.
        """
        resultados: dict[str, bool] = {}

        for nome_banco in _BANCOS_OBRIGATORIOS:
            if nome_banco == "trading_diarios.db":
                caminho = db_path
            else:
                caminho = db_path.parent / nome_banco

            existe = caminho.exists() and caminho.is_file()
            if existe:
                # Tenta abrir para verificar integridade basica
                try:
                    conn = self._conectar(caminho)
                    conn.execute("SELECT 1")
                    conn.close()
                except (sqlite3.DatabaseError, OSError):
                    existe = False

            resultados[nome_banco] = existe

        return resultados

    def verificar_tabelas(self, db_path: Path) -> dict[str, bool]:
        """Verifica existencia das tabelas obrigatorias no banco.

        Args:
            db_path: Caminho para o banco SQLite.

        Returns:
            Dicionario {nome_tabela: existe} para cada tabela obrigatoria.
            Retorna False para todas se o banco nao existir.
        """
        resultados: dict[str, bool] = {t: False for t in _TABELAS_OBRIGATORIAS}

        if not db_path.exists():
            return resultados

        try:
            conn = self._conectar(db_path)
            tabelas_existentes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            conn.close()

            for tabela in _TABELAS_OBRIGATORIAS:
                resultados[tabela] = tabela in tabelas_existentes

        except (sqlite3.DatabaseError, OSError) as exc:
            logger.error("Erro ao verificar tabelas: %s", exc)

        return resultados

    def verificar_ultimo_registro(
        self,
        db_path: Path,
        tabela: str,
        horas: int = 24,
    ) -> bool:
        """Verifica se ha registro recente na tabela dentro da janela de horas.

        Args:
            db_path: Caminho para o banco SQLite.
            tabela: Nome da tabela a verificar (deve conter apenas letras,
                numeros e underscores).
            horas: Janela de tempo em horas (padrao: 24h).

        Returns:
            True se houver pelo menos um registro nas ultimas `horas` horas,
            False caso contrario (banco ausente, tabela ausente ou sem dados).
        """
        if not db_path.exists():
            return False

        # Validar nome de tabela: apenas letras, numeros e underscores
        # para prevenir injecao de SQL via interpolacao de f-string.
        if not tabela.replace("_", "").isalnum():
            logger.error(
                "Nome de tabela invalido (caracteres nao permitidos): %r",
                tabela,
            )
            return False

        limite_iso = (
            datetime.now() - timedelta(hours=horas)
        ).isoformat()

        # Colunas de timestamp candidatas (em ordem de preferencia)
        colunas_candidatas = ["created_at", "timestamp", "updated_at", "date"]

        try:
            conn = self._conectar(db_path)

            # Verificar se tabela existe via query parametrizada (seguro)
            existe = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tabela,),
            ).fetchone()
            if not existe:
                conn.close()
                return False

            # Descobrir colunas da tabela (nome de tabela ja validado acima)
            colunas_info = conn.execute(
                f"PRAGMA table_info({tabela})"  # noqa: S608 — tabela validada
            ).fetchall()
            colunas_tabela = {row[1] for row in colunas_info}

            coluna_ts: str | None = None
            for candidata in colunas_candidatas:
                if candidata in colunas_tabela:
                    coluna_ts = candidata
                    break

            if coluna_ts is None:
                # Sem coluna de timestamp: apenas verifica se ha dados
                # (nome da tabela ja foi validado e confirmado via sqlite_master)
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {tabela}"  # noqa: S608 — validado
                ).fetchone()
                conn.close()
                return bool(row and row[0] > 0)

            # coluna_ts vem de colunas_candidatas (lista interna controlada)
            row = conn.execute(
                f"SELECT 1 FROM {tabela} WHERE {coluna_ts} >= ? LIMIT 1",  # noqa: S608 — validado
                (limite_iso,),
            ).fetchone()
            conn.close()
            return row is not None

        except (sqlite3.DatabaseError, OSError) as exc:
            logger.error(
                "Erro ao verificar ultimo registro em %s.%s: %s",
                db_path.name, tabela, exc,
            )
            return False

    # ------------------------------------------------------------------
    # Diagnostico completo
    # ------------------------------------------------------------------

    def executar_diagnostico_completo(
        self,
        db_path: Path,
    ) -> dict[str, Any]:
        """Executa diagnostico completo dos bancos e tabelas dos Diarios.

        Combina verificar_bancos(), verificar_tabelas() e
        verificar_ultimo_registro() para produzir um relatorio estruturado
        com status OK / WARNING / CRITICAL.

        Args:
            db_path: Caminho para o banco principal (data/db/trading_diarios.db).

        Returns:
            Dicionario com:
                status_geral: "OK" | "WARNING" | "CRITICAL"
                bancos: dict[str, bool]
                tabelas: dict[str, bool]
                atualidade: dict[str, bool]
                problemas: list[str]
                recomendacoes: list[str]
        """
        problemas: list[str] = []
        recomendacoes: list[str] = []

        # 1. Verificar bancos
        bancos = self.verificar_bancos(db_path)
        for nome, existe in bancos.items():
            if not existe:
                problemas.append(f"[CRITICAL] Banco ausente ou corrompido: {nome}")
                recomendacoes.append(
                    f"Executar inicializacao do banco: {nome}"
                )

        # 2. Verificar tabelas
        tabelas = self.verificar_tabelas(db_path)
        for nome, existe in tabelas.items():
            if not existe:
                problemas.append(f"[WARNING] Tabela ausente: {nome}")
                recomendacoes.append(
                    f"Executar DDL de criacao para: {nome}"
                )

        # 3. Verificar atualidade (ultimas 24h)
        tabelas_monitoradas = [
            t for t in _TABELAS_OBRIGATORIAS if tabelas.get(t, False)
        ]
        atualidade: dict[str, bool] = {}
        for tabela in tabelas_monitoradas:
            atualidade[tabela] = self.verificar_ultimo_registro(
                db_path, tabela, horas=24
            )

        tabelas_desatualizadas = [t for t, ok in atualidade.items() if not ok]
        if tabelas_desatualizadas:
            for tabela in tabelas_desatualizadas:
                problemas.append(f"[WARNING] Sem registros nas ultimas 24h: {tabela}")
                recomendacoes.append(
                    f"Verificar se o servico que alimenta '{tabela}' esta ativo"
                )

        # 4. Determinar status geral
        tem_critical = any("[CRITICAL]" in p for p in problemas)
        tem_warning = any("[WARNING]" in p for p in problemas)

        if tem_critical:
            status_geral = _STATUS_CRITICAL
        elif tem_warning:
            status_geral = _STATUS_WARNING
        else:
            status_geral = _STATUS_OK

        return {
            "status_geral": status_geral,
            "bancos": bancos,
            "tabelas": tabelas,
            "atualidade": atualidade,
            "problemas": problemas,
            "recomendacoes": recomendacoes,
            "verificado_em": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Relatorio textual
    # ------------------------------------------------------------------

    def gerar_relatorio_diagnostico(self, db_path: Path) -> str:
        """Gera relatorio textual do diagnostico para o operador.

        Executa diagnostico completo e formata o resultado em texto
        estruturado, adequado para exibicao em terminal ou log.

        Args:
            db_path: Caminho para o banco principal.

        Returns:
            String com relatorio de diagnostico formatado.
        """
        resultado = self.executar_diagnostico_completo(db_path)

        linhas: list[str] = [
            "=" * 60,
            "  DIAGNOSTICO DE SAUDE — PIPELINE DIARIOS",
            "=" * 60,
            f"  Verificado em: {resultado['verificado_em']}",
            f"  Banco alvo:    {db_path}",
            f"  Status geral:  {resultado['status_geral']}",
            "=" * 60,
            "",
            "[ BANCOS ]",
        ]

        for nome, existe in resultado["bancos"].items():
            icone = "OK " if existe else "ERR"
            linhas.append(f"  [{icone}] {nome}")

        linhas += ["", "[ TABELAS ]"]
        for nome, existe in resultado["tabelas"].items():
            icone = "OK " if existe else "ERR"
            linhas.append(f"  [{icone}] {nome}")

        if resultado["atualidade"]:
            linhas += ["", "[ ATUALIDADE (ultimas 24h) ]"]
            for tabela, atualizada in resultado["atualidade"].items():
                icone = "OK " if atualizada else "WAR"
                linhas.append(f"  [{icone}] {tabela}")

        if resultado["problemas"]:
            linhas += ["", "[ PROBLEMAS DETECTADOS ]"]
            for problema in resultado["problemas"]:
                linhas.append(f"  ! {problema}")

        if resultado["recomendacoes"]:
            linhas += ["", "[ RECOMENDACOES ]"]
            for rec in resultado["recomendacoes"]:
                linhas.append(f"  > {rec}")

        linhas += ["", "=" * 60]

        return "\n".join(linhas)
