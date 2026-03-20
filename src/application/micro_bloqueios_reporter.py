"""
CALIBRACAO-MICRO-04: Relatorio Diario de Bloqueios por Categoria.

Responsabilidades:
- Registrar cada oportunidade rejeitada com motivo estruturado na tabela
  SQLite `micro_trend_bloqueios`
- Calcular estatisticas de bloqueios por flag e por horario do pregao
- Gerar relatorio Markdown ao encerramento: top 5 flags, delta medio,
  horarios de maior concentracao

Pipeline:
    Agente Micro Tendencia detecta oportunidade
    → evaluate_opportunity() rejeita com motivo
    → MicroBloqueiosReporter.registrar_bloqueio()
    → Encerramento pregao: gerar_relatorio_pregao()

Executor: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

Status: Implementacao v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-04)
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Enum: Flags de Bloqueio ───────────────────────────────────────────────────


class FlagBloqueador(Enum):
    """Categorias de flags que bloqueiam execucao de oportunidade.

    Valores:
        CONFIANCA: Confianca calculada abaixo do threshold global.
        EXP_REDUZIDA: Modo de exposicao reduzida exige criterios extras.
        DIR_FRACO: Direcao direcional fraca (muitas contradicoes entre TFs).
        TRAP_PROX: Armadilha estrutural proxima ao preco de entrada.
        RR_INSUFICIENTE: Razao risco/retorno abaixo do minimo configurado.
        COOLING_OFF: Cooling-off ativo apos stop loss recente.
    """

    CONFIANCA = "CONFIANCA"
    EXP_REDUZIDA = "EXP_REDUZIDA"
    DIR_FRACO = "DIR_FRACO"
    TRAP_PROX = "TRAP_PROX"
    RR_INSUFICIENTE = "RR_INSUFICIENTE"
    COOLING_OFF = "COOLING_OFF"


# ── Dataclass: Registro de Bloqueio ───────────────────────────────────────────


@dataclass
class BloqueioRecord:
    """Registro de uma oportunidade rejeitada pelo agente.

    Args:
        timestamp: Momento da rejeicao.
        opportunity_id: Identificador da oportunidade rejeitada.
        flag_bloqueador: Flag principal que causou o bloqueio.
        confianca_calculada: Confianca efetiva da oportunidade (%).
        confianca_necessaria: Threshold minimo exigido no momento (%).
        delta: Diferenca entre calculada e necessaria (negativo = deficit).
        detalhes: Mensagem descritiva opcional do motivo.
    """

    timestamp: datetime
    opportunity_id: str
    flag_bloqueador: FlagBloqueador
    confianca_calculada: float
    confianca_necessaria: float
    delta: float
    detalhes: Optional[str] = field(default=None)

    def para_dict(self) -> Dict[str, Any]:
        """Converte o registro para dicionario serializavel em JSON.

        Returns:
            Dict com todos os campos, timestamp em ISO 8601 e flag como string.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "opportunity_id": self.opportunity_id,
            "flag_bloqueador": self.flag_bloqueador.value,
            "confianca_calculada": self.confianca_calculada,
            "confianca_necessaria": self.confianca_necessaria,
            "delta": self.delta,
            "detalhes": self.detalhes,
        }


# ── Motor Principal ───────────────────────────────────────────────────────────


class MicroBloqueiosReporter:
    """Motor de registro e relatorio de bloqueios do Micro Tendencia.

    Persiste cada oportunidade rejeitada em SQLite e gera relatorio
    Markdown estruturado ao encerramento do pregao, mostrando quais
    flags mais reduziram a ativacao operacional.

    Args:
        db_path: Caminho para o banco SQLite. Padrao: data/db/trading.db.

    Exemplo:
        reporter = MicroBloqueiosReporter()

        # Durante o pregao, ao rejeitar oportunidade:
        reporter.registrar_bloqueio(BloqueioRecord(
            timestamp=datetime.now(),
            opportunity_id="opp_001",
            flag_bloqueador=FlagBloqueador.CONFIANCA,
            confianca_calculada=42.5,
            confianca_necessaria=45.0,
            delta=-2.5,
        ))

        # Ao encerrar o pregao:
        reporter.gerar_relatorio_pregao(data=date.today())
    """

    _TABELA = "micro_trend_bloqueios"

    def __init__(
        self,
        db_path: Optional[Path] = None,
    ) -> None:
        """Inicializa o reporter e cria a tabela se nao existir.

        Args:
            db_path: Caminho para o banco SQLite.
        """
        if db_path is None:
            db_path = Path("data/db/trading.db")
        self._db_path = db_path
        self._criar_tabela()

    # ── Privados ──────────────────────────────────────────────────────────────

    def _conectar(self) -> sqlite3.Connection:
        """Abre conexao com o banco SQLite.

        Returns:
            Conexao SQLite configurada.
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _criar_tabela(self) -> None:
        """Cria tabela micro_trend_bloqueios e indices se nao existirem."""
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._TABELA} (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp           TEXT    NOT NULL,
                data_pregao         TEXT    NOT NULL,
                hora_pregao         TEXT    NOT NULL,
                opportunity_id      TEXT    NOT NULL,
                flag_bloqueador     TEXT    NOT NULL,
                confianca_calculada REAL    NOT NULL,
                confianca_necessaria REAL   NOT NULL,
                delta               REAL    NOT NULL,
                detalhes            TEXT
            )
        """
        )
        cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_mtb_data_pregao
            ON {self._TABELA}(data_pregao)
        """
        )
        cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_mtb_flag
            ON {self._TABELA}(flag_bloqueador)
        """
        )
        conn.commit()
        conn.close()

    # ── Publicos: Registro ─────────────────────────────────────────────────────

    def registrar_bloqueio(self, bloqueio: BloqueioRecord) -> int:
        """Persiste um bloqueio no banco SQLite.

        Args:
            bloqueio: Registro de oportunidade rejeitada.

        Returns:
            ID gerado pelo banco para o registro.
        """
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO {self._TABELA}
            (timestamp, data_pregao, hora_pregao, opportunity_id,
             flag_bloqueador, confianca_calculada, confianca_necessaria,
             delta, detalhes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                bloqueio.timestamp.isoformat(),
                bloqueio.timestamp.date().isoformat(),
                bloqueio.timestamp.strftime("%H:%M"),
                bloqueio.opportunity_id,
                bloqueio.flag_bloqueador.value,
                bloqueio.confianca_calculada,
                bloqueio.confianca_necessaria,
                bloqueio.delta,
                bloqueio.detalhes,
            ),
        )
        conn.commit()
        bloqueio_id: int = cursor.lastrowid or 0
        conn.close()
        return bloqueio_id

    # ── Publicos: Consulta ─────────────────────────────────────────────────────

    def listar_bloqueios(
        self,
        data: date,
        flag: Optional[FlagBloqueador] = None,
    ) -> List[BloqueioRecord]:
        """Lista bloqueios registrados em uma data de pregao.

        Args:
            data: Data do pregao a consultar.
            flag: Filtrar por flag especifico (opcional).

        Returns:
            Lista de BloqueioRecord ordenada por timestamp.
        """
        conn = self._conectar()
        cursor = conn.cursor()

        if flag is not None:
            cursor.execute(
                f"""
                SELECT timestamp, opportunity_id, flag_bloqueador,
                       confianca_calculada, confianca_necessaria, delta, detalhes
                FROM {self._TABELA}
                WHERE data_pregao = ? AND flag_bloqueador = ?
                ORDER BY timestamp
            """,
                (data.isoformat(), flag.value),
            )
        else:
            cursor.execute(
                f"""
                SELECT timestamp, opportunity_id, flag_bloqueador,
                       confianca_calculada, confianca_necessaria, delta, detalhes
                FROM {self._TABELA}
                WHERE data_pregao = ?
                ORDER BY timestamp
            """,
                (data.isoformat(),),
            )

        rows = cursor.fetchall()
        conn.close()

        return [
            BloqueioRecord(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                opportunity_id=row["opportunity_id"],
                flag_bloqueador=FlagBloqueador(row["flag_bloqueador"]),
                confianca_calculada=row["confianca_calculada"],
                confianca_necessaria=row["confianca_necessaria"],
                delta=row["delta"],
                detalhes=row["detalhes"],
            )
            for row in rows
        ]

    def calcular_estatisticas(self, data: date) -> Dict[str, Any]:
        """Calcula estatisticas de bloqueios para um pregao.

        Metricas retornadas:
        - total_bloqueios: Contagem total de rejeicoes no dia.
        - por_flag: Dict {flag_str: contagem}.
        - top5_flags: Lista de (flag_str, contagem) ordenada decrescente.
        - delta_medio: Media dos deltas (negativo = confianca abaixo threshold).
        - confianca_media_calculada: Media das confianças calculadas (%).
        - confianca_media_necessaria: Media dos thresholds exigidos (%).

        Args:
            data: Data do pregao.

        Returns:
            Dicionario com metricas estruturadas.
        """
        conn = self._conectar()
        cursor = conn.cursor()

        # Contagem por flag
        cursor.execute(
            f"""
            SELECT flag_bloqueador, COUNT(*) as qtd
            FROM {self._TABELA}
            WHERE data_pregao = ?
            GROUP BY flag_bloqueador
            ORDER BY qtd DESC
        """,
            (data.isoformat(),),
        )
        por_flag_rows = cursor.fetchall()

        # Agregados numericos
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total,
                AVG(delta) as delta_medio,
                AVG(confianca_calculada) as conf_calc_media,
                AVG(confianca_necessaria) as conf_nec_media
            FROM {self._TABELA}
            WHERE data_pregao = ?
        """,
            (data.isoformat(),),
        )
        agr = cursor.fetchone()
        conn.close()

        por_flag: Dict[str, int] = {
            row["flag_bloqueador"]: row["qtd"] for row in por_flag_rows
        }
        top5: List[Tuple[str, int]] = sorted(
            por_flag.items(), key=lambda x: x[1], reverse=True
        )[:5]

        total = agr["total"] or 0

        return {
            "total_bloqueios": total,
            "por_flag": por_flag,
            "top5_flags": top5,
            "delta_medio": agr["delta_medio"] if total > 0 else 0.0,
            "confianca_media_calculada": agr["conf_calc_media"] if total > 0 else 0.0,
            "confianca_media_necessaria": agr["conf_nec_media"] if total > 0 else 0.0,
        }

    # ── Publicos: Relatorio ───────────────────────────────────────────────────

    def gerar_relatorio_pregao(
        self,
        data: date,
        diretorio_saida: Optional[Path] = None,
    ) -> str:
        """Gera relatorio Markdown de bloqueios do pregao.

        O relatorio inclui:
        - Total de rejeicoes no dia
        - Top 5 flags mais frequentes com contagem e percentual
        - Delta medio (gap confianca calculada vs threshold)
        - Concentracao de bloqueios por hora do pregao
        - Recomendacao se agente esteve excessivamente conservador

        Args:
            data: Data do pregao.
            diretorio_saida: Se informado, salva arquivo .md no diretorio.
                Nome: micro_bloqueios_YYYYMMDD.md

        Returns:
            Caminho do arquivo salvo (se diretorio_saida fornecido)
            ou conteudo Markdown como string.
        """
        stats = self.calcular_estatisticas(data=data)
        bloqueios = self.listar_bloqueios(data=data)

        # Concentracao por hora
        por_hora: Dict[str, int] = {}
        for b in bloqueios:
            hora = b.timestamp.strftime("%H:00")
            por_hora[hora] = por_hora.get(hora, 0) + 1
        top_horas = sorted(por_hora.items(), key=lambda x: x[1], reverse=True)[:5]

        data_fmt = data.strftime("%d/%m/%Y")
        total = stats["total_bloqueios"]

        linhas = [
            f"# Relatorio Micro Bloqueios — {data_fmt}",
            "",
            "## Resumo do Pregao",
            "",
            f"- **Total de oportunidades retidas:** {total}",
            f"- **Delta medio (gap confianca):** " f"{stats['delta_medio']:.2f}%",
            f"- **Confianca media calculada:** "
            f"{stats['confianca_media_calculada']:.1f}%",
            f"- **Confianca media necessaria:** "
            f"{stats['confianca_media_necessaria']:.1f}%",
            "",
            "## Top 5 Flags que Mais Bloquearam Trades",
            "",
        ]

        if stats["top5_flags"]:
            linhas.append("| Flag | Bloqueios | % do Total |")
            linhas.append("|------|-----------|------------|")
            for flag_nome, qtd in stats["top5_flags"]:
                pct = (qtd / total * 100) if total > 0 else 0.0
                linhas.append(f"| {flag_nome} | {qtd} | {pct:.1f}% |")
        else:
            linhas.append("_Nenhum bloqueio registrado neste pregao._")

        linhas += [
            "",
            "## Concentracao de Bloqueios por Horario",
            "",
        ]

        if top_horas:
            linhas.append("| Horario | Bloqueios |")
            linhas.append("|---------|-----------|")
            for hora, qtd in top_horas:
                linhas.append(f"| {hora} | {qtd} |")
        else:
            linhas.append("_Sem dados de horario._")

        # Recomendacao automatica
        linhas += ["", "## Recomendacao", ""]
        if total == 0:
            linhas.append(
                "_Nenhuma oportunidade retida registrada. Verificar se agente operou._"
            )
        elif total >= 50:
            linhas.append(
                "**ATENCAO:** Agente muito seletivo — "
                f"{total} oportunidades retidas. "
                "Revisar thresholds de confianca (CALIBRACAO-MICRO-01)."
            )
        elif total >= 20:
            linhas.append(
                f"Volume moderado de retenções ({total}). "
                "Monitorar se a producao de trades esta adequada."
            )
        else:
            linhas.append(
                f"Volume baixo de retenções ({total}). Parametros calibrados."
            )

        conteudo = "\n".join(linhas) + "\n"

        if diretorio_saida is not None:
            nome_arquivo = f"micro_bloqueios_{data.strftime('%Y%m%d')}.md"
            caminho = diretorio_saida / nome_arquivo
            caminho.write_text(conteudo, encoding="utf-8")
            return str(caminho)

        return conteudo
