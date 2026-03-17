"""
Episodio Operador — Sistema de Aprendizado Proprio do Agente Diarios.

O Agente Diarios registra cada trade com contexto rico:
  - Em qual fase do dia entrou (abertura, manha, almoco...)
  - Qual era a qualidade do movimento (forte, fraco, chop, spike)
  - Se havia exaustao, pullback, ou armadilha ativa
  - Como estavam os correlatos (alinhados, divergentes)
  - Qual era o ajuste de confianca da leitura

Com N episodios acumulados, calcula padroes de acerto/erro:
  - Qual fase do dia tem melhor resultado
  - Qual qualidade de movimento gerou mais acerto
  - Se armadilha ALTA levou a perdas
  - Se divergencia critica resultou em perda

Esses padroes retroalimentam o LeituraDeOperador via:
  - ContextoAprendido: modifica pesos dos ajustes de confianca

Persistencia: SQLite (tabela diario_episodios) + fallback JSON

Status: v1.0 (17/03/2026)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("diario_episodio_operador")

# Minimo de episodios para confiar nos padroes aprendidos
MIN_EPISODIOS_APRENDIZADO = 10


# ────────────────────────────────────────────────────────────────
# Estrutura de um episodio
# ────────────────────────────────────────────────────────────────

@dataclass
class EpisodioOperador:
    """
    Registro de um trade completo do Agente Diarios com contexto de leitura.
    """
    session_id: str
    timestamp_entrada: str
    timestamp_saida: str
    direcao: str              # BUY ou SELL
    preco_entrada: float
    preco_saida: float
    sl: float
    tp: float
    atr_entrada: float
    resultado_pts: float      # positivo = ganho, negativo = perda
    motivo_saida: str         # sl_tp_mt5, reversao_*, devolucao_*, guardian_*

    # Contexto da leitura no momento da entrada
    fase_sessao: str
    qualidade_movimento: str
    exaustao: bool
    pullback: bool
    correlacao_estado: str
    divergencia_critica: bool
    risco_armadilha: str
    preco_extremo: bool
    desvio_vwap_pts: float
    ajuste_confianca_leitura: float  # ajuste aplicado pela leitura

    # Contexto do sinal
    confianca_entrada: float
    alinhamento_entrada: float
    momentum_entrada: float

    # Avaliacao
    foi_acerto: bool          # resultado_pts > 0
    max_ganho_pts: float      # maximo ganho atingido durante o trade
    eficiencia: float         # resultado_pts / max_ganho_pts (0-1)


# ────────────────────────────────────────────────────────────────
# Padroes aprendidos
# ────────────────────────────────────────────────────────────────

@dataclass
class ContextoAprendido:
    """
    Padroes extraidos dos episodios acumulados.

    Modifica os pesos do LeituraDeOperador dinamicamente.
    """
    n_episodios: int
    win_rate_geral: float         # % de acertos geral

    # Por fase do dia
    wr_por_fase: dict[str, float]           # fase -> win_rate
    melhor_fase: str
    pior_fase: str

    # Por qualidade de movimento
    wr_por_qualidade: dict[str, float]
    melhor_qualidade: str

    # Armadilha ALTA leva a perda?
    taxa_perda_armadilha_alta: float  # % de perdas quando arm=ALTA

    # Divergencia critica leva a perda?
    taxa_perda_divergencia: float

    # Ajuste dinamico recomendado para LeituraDeOperador
    # Negativo = ser mais conservador nesse contexto
    ajuste_fase_almoco: float          # historico proprio no almoco
    ajuste_exaustao: float             # historico em exaustao
    ajuste_armadilha_alta: float       # historico com arm ALTA
    ajuste_divergencia: float          # historico com divergencia

    resumo: str


# ────────────────────────────────────────────────────────────────
# Repositorio de episodios
# ────────────────────────────────────────────────────────────────

class EpisodioOperadorRepo:
    """
    Persiste e consulta episodios do Agente Diarios.

    Usa SQLite com fallback para JSON se tabela nao existir.
    """

    DDL = """
    CREATE TABLE IF NOT EXISTS diario_episodios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        timestamp_entrada TEXT NOT NULL,
        timestamp_saida TEXT NOT NULL,
        direcao TEXT NOT NULL,
        preco_entrada REAL,
        preco_saida REAL,
        sl REAL,
        tp REAL,
        atr_entrada REAL,
        resultado_pts REAL,
        motivo_saida TEXT,
        fase_sessao TEXT,
        qualidade_movimento TEXT,
        exaustao INTEGER,
        pullback INTEGER,
        correlacao_estado TEXT,
        divergencia_critica INTEGER,
        risco_armadilha TEXT,
        preco_extremo INTEGER,
        desvio_vwap_pts REAL,
        ajuste_confianca_leitura REAL,
        confianca_entrada REAL,
        alinhamento_entrada REAL,
        momentum_entrada REAL,
        foi_acerto INTEGER,
        max_ganho_pts REAL,
        eficiencia REAL
    )
    """

    def __init__(self, db_path: str, fallback_json: Optional[str] = None):
        self._db_path = db_path
        self._fallback_json = fallback_json or db_path.replace(".db", "_diario_episodios.json")
        self._garantir_tabela()

    def _garantir_tabela(self) -> None:
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(self.DDL)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Nao foi possivel criar tabela diario_episodios: %s", e)

    def salvar(self, ep: EpisodioOperador) -> bool:
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                INSERT INTO diario_episodios (
                    session_id, timestamp_entrada, timestamp_saida,
                    direcao, preco_entrada, preco_saida, sl, tp, atr_entrada,
                    resultado_pts, motivo_saida,
                    fase_sessao, qualidade_movimento, exaustao, pullback,
                    correlacao_estado, divergencia_critica, risco_armadilha,
                    preco_extremo, desvio_vwap_pts, ajuste_confianca_leitura,
                    confianca_entrada, alinhamento_entrada, momentum_entrada,
                    foi_acerto, max_ganho_pts, eficiencia
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                ep.session_id, ep.timestamp_entrada, ep.timestamp_saida,
                ep.direcao, ep.preco_entrada, ep.preco_saida, ep.sl, ep.tp,
                ep.atr_entrada, ep.resultado_pts, ep.motivo_saida,
                ep.fase_sessao, ep.qualidade_movimento,
                int(ep.exaustao), int(ep.pullback),
                ep.correlacao_estado, int(ep.divergencia_critica),
                ep.risco_armadilha, int(ep.preco_extremo),
                ep.desvio_vwap_pts, ep.ajuste_confianca_leitura,
                ep.confianca_entrada, ep.alinhamento_entrada, ep.momentum_entrada,
                int(ep.foi_acerto), ep.max_ganho_pts, ep.eficiencia,
            ))
            conn.commit()
            conn.close()
            logger.info(
                "Episodio registrado: dir=%s res=%.0f motivo=%s fase=%s arm=%s",
                ep.direcao, ep.resultado_pts, ep.motivo_saida,
                ep.fase_sessao, ep.risco_armadilha,
            )
            return True
        except Exception as e:
            logger.error("Erro ao salvar episodio: %s", e)
            self._salvar_fallback_json(ep)
            return False

    def _salvar_fallback_json(self, ep: EpisodioOperador) -> None:
        try:
            caminho = Path(self._fallback_json)
            existentes = []
            if caminho.exists():
                existentes = json.loads(caminho.read_text(encoding="utf-8"))
            existentes.append(asdict(ep))
            caminho.write_text(
                json.dumps(existentes, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Falha no fallback JSON: %s", e)

    def listar_ultimos(self, n: int = 100, dias: int = 30) -> list[EpisodioOperador]:
        """Retorna os ultimos N episodios dos ultimos `dias` dias."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM diario_episodios
                WHERE date(timestamp_entrada) >= date('now', ? || ' days')
                ORDER BY timestamp_entrada DESC
                LIMIT ?
            """, (f"-{dias}", n)).fetchall()
            conn.close()
            return [self._row_to_ep(r) for r in rows]
        except Exception as e:
            logger.error("Erro ao listar episodios: %s", e)
            return self._listar_fallback_json(n)

    def _listar_fallback_json(self, n: int) -> list[EpisodioOperador]:
        try:
            caminho = Path(self._fallback_json)
            if not caminho.exists():
                return []
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            return [EpisodioOperador(**d) for d in dados[-n:]]
        except Exception:
            return []

    @staticmethod
    def _row_to_ep(row: sqlite3.Row) -> EpisodioOperador:
        d = dict(row)
        return EpisodioOperador(
            session_id=d["session_id"],
            timestamp_entrada=d["timestamp_entrada"],
            timestamp_saida=d["timestamp_saida"],
            direcao=d["direcao"],
            preco_entrada=float(d["preco_entrada"]),
            preco_saida=float(d["preco_saida"]),
            sl=float(d["sl"]),
            tp=float(d["tp"]),
            atr_entrada=float(d["atr_entrada"]),
            resultado_pts=float(d["resultado_pts"]),
            motivo_saida=d["motivo_saida"],
            fase_sessao=d["fase_sessao"],
            qualidade_movimento=d["qualidade_movimento"],
            exaustao=bool(d["exaustao"]),
            pullback=bool(d["pullback"]),
            correlacao_estado=d["correlacao_estado"],
            divergencia_critica=bool(d["divergencia_critica"]),
            risco_armadilha=d["risco_armadilha"],
            preco_extremo=bool(d["preco_extremo"]),
            desvio_vwap_pts=float(d["desvio_vwap_pts"]),
            ajuste_confianca_leitura=float(d["ajuste_confianca_leitura"]),
            confianca_entrada=float(d["confianca_entrada"]),
            alinhamento_entrada=float(d["alinhamento_entrada"]),
            momentum_entrada=float(d["momentum_entrada"]),
            foi_acerto=bool(d["foi_acerto"]),
            max_ganho_pts=float(d["max_ganho_pts"]),
            eficiencia=float(d["eficiencia"]),
        )


# ────────────────────────────────────────────────────────────────
# Motor de aprendizado
# ────────────────────────────────────────────────────────────────

class AprendizadoOperador:
    """
    Extrai padroes dos episodios acumulados e produz ContextoAprendido.

    O ContextoAprendido e usado pelo DiarioOrderManager para ajustar
    os pesos da LeituraDeOperador dinamicamente — o agente aprende
    quais contextos funcionam para ele especificamente.
    """

    def __init__(self, repo: EpisodioOperadorRepo):
        self._repo = repo

    def calcular_wr(self, episodios: list[EpisodioOperador]) -> float:
        if not episodios:
            return 50.0
        return sum(1 for e in episodios if e.foi_acerto) / len(episodios) * 100

    def calcular_contexto(self, dias: int = 30) -> ContextoAprendido:
        """
        Analisa os episodios dos ultimos `dias` dias e extrai padroes.
        """
        episodios = self._repo.listar_ultimos(n=500, dias=dias)
        n = len(episodios)

        if n < MIN_EPISODIOS_APRENDIZADO:
            return ContextoAprendido(
                n_episodios=n,
                win_rate_geral=50.0,
                wr_por_fase={},
                melhor_fase="",
                pior_fase="",
                wr_por_qualidade={},
                melhor_qualidade="",
                taxa_perda_armadilha_alta=0.0,
                taxa_perda_divergencia=0.0,
                ajuste_fase_almoco=0.0,
                ajuste_exaustao=0.0,
                ajuste_armadilha_alta=0.0,
                ajuste_divergencia=0.0,
                resumo=f"Poucos episodios ({n}/{MIN_EPISODIOS_APRENDIZADO}) para aprender",
            )

        wr_geral = self.calcular_wr(episodios)

        # Win rate por fase
        wr_fase: dict[str, float] = {}
        for fase in set(e.fase_sessao for e in episodios):
            eps_fase = [e for e in episodios if e.fase_sessao == fase]
            if len(eps_fase) >= 3:
                wr_fase[fase] = self.calcular_wr(eps_fase)

        melhor_fase = max(wr_fase, key=wr_fase.get) if wr_fase else ""
        pior_fase = min(wr_fase, key=wr_fase.get) if wr_fase else ""

        # Win rate por qualidade de movimento
        wr_qual: dict[str, float] = {}
        for qual in set(e.qualidade_movimento for e in episodios):
            eps_q = [e for e in episodios if e.qualidade_movimento == qual]
            if len(eps_q) >= 3:
                wr_qual[qual] = self.calcular_wr(eps_q)

        melhor_qual = max(wr_qual, key=wr_qual.get) if wr_qual else ""

        # Taxa de perda com armadilha ALTA
        eps_arm_alta = [e for e in episodios if e.risco_armadilha == "ALTA"]
        taxa_perda_arm = (
            sum(1 for e in eps_arm_alta if not e.foi_acerto) / len(eps_arm_alta) * 100
            if eps_arm_alta else 0.0
        )

        # Taxa de perda com divergencia critica
        eps_div = [e for e in episodios if e.divergencia_critica]
        taxa_perda_div = (
            sum(1 for e in eps_div if not e.foi_acerto) / len(eps_div) * 100
            if eps_div else 0.0
        )

        # Ajustes dinamicos: baseados na diferenca do WR vs WR geral
        # Se win_rate nesse contexto e < WR geral → penalidade adicional
        def _ajuste(wr_ctx: float, n_ctx: int) -> float:
            if n_ctx < 3:
                return 0.0
            diff = wr_ctx - wr_geral
            # Cada 10% de diferenca no WR = 0.05 de ajuste na confianca
            return max(-0.20, min(0.10, diff / 100.0 * 0.5))

        eps_almoco = [e for e in episodios if e.fase_sessao == "ALMOCO"]
        wr_almoco = self.calcular_wr(eps_almoco)
        ajuste_almoco = _ajuste(wr_almoco, len(eps_almoco))

        eps_exaustao = [e for e in episodios if e.exaustao]
        wr_exaustao = self.calcular_wr(eps_exaustao)
        ajuste_exaustao = _ajuste(wr_exaustao, len(eps_exaustao))

        ajuste_arm_alta = _ajuste(100 - taxa_perda_arm, len(eps_arm_alta))
        ajuste_div = _ajuste(100 - taxa_perda_div, len(eps_div))

        # Resumo
        partes = [f"{n} trades | WR={wr_geral:.0f}%"]
        if melhor_fase:
            partes.append(f"melhor_fase={melhor_fase}({wr_fase.get(melhor_fase, 0):.0f}%)")
        if pior_fase and pior_fase != melhor_fase:
            partes.append(f"pior_fase={pior_fase}({wr_fase.get(pior_fase, 0):.0f}%)")
        if taxa_perda_arm > 60:
            partes.append(f"arm_alta perigosa({taxa_perda_arm:.0f}% perda)")
        resumo = " | ".join(partes)

        return ContextoAprendido(
            n_episodios=n,
            win_rate_geral=wr_geral,
            wr_por_fase=wr_fase,
            melhor_fase=melhor_fase,
            pior_fase=pior_fase,
            wr_por_qualidade=wr_qual,
            melhor_qualidade=melhor_qual,
            taxa_perda_armadilha_alta=taxa_perda_arm,
            taxa_perda_divergencia=taxa_perda_div,
            ajuste_fase_almoco=ajuste_almoco,
            ajuste_exaustao=ajuste_exaustao,
            ajuste_armadilha_alta=ajuste_arm_alta,
            ajuste_divergencia=ajuste_div,
            resumo=resumo,
        )


# ────────────────────────────────────────────────────────────────
# Construtor de episodio a partir do ciclo
# ────────────────────────────────────────────────────────────────

def construir_episodio(
    posicao_fechada: object,   # DiarioPosicao
    motivo_saida: str,
    preco_saida: float,
    sinal_entrada: object,     # SinalDiario usado na abertura
    session_id: str,
) -> EpisodioOperador:
    """
    Constroi um EpisodioOperador a partir dos dados disponiveis
    apos o fechamento de uma posicao.
    """
    preco_entrada = getattr(posicao_fechada, "preco_entrada", 0.0)
    direcao = getattr(posicao_fechada, "direcao", "")
    atr = getattr(posicao_fechada, "atr_entrada", 100.0)
    max_ganho = getattr(posicao_fechada, "max_ganho_pts", 0.0)
    abertura_ts = getattr(posicao_fechada, "abertura_ts", datetime.now().isoformat())

    if direcao == "BUY":
        resultado = preco_saida - preco_entrada
    else:
        resultado = preco_entrada - preco_saida

    foi_acerto = resultado > 0
    eficiencia = (resultado / max_ganho) if max_ganho > 0 else 0.0
    eficiencia = max(-1.0, min(1.0, eficiencia))

    # Extrair contexto da leitura
    leitura = getattr(sinal_entrada, "leitura", None)
    fase = getattr(leitura, "fase_sessao", "") if leitura else ""
    qualidade = getattr(leitura, "qualidade_movimento", "") if leitura else ""
    exaustao = getattr(leitura, "exaustao_detectada", False) if leitura else False
    pullback = getattr(leitura, "pullback_saudavel", False) if leitura else False
    corr = getattr(leitura, "correlacao_estado", "") if leitura else ""
    div = getattr(leitura, "divergencia_critica", False) if leitura else False
    risco = getattr(leitura, "risco_armadilha", "") if leitura else ""
    extremo = getattr(leitura, "preco_extremo", False) if leitura else False
    desvio = getattr(leitura, "desvio_vwap_pts", 0.0) if leitura else 0.0
    ajuste_leit = getattr(leitura, "ajuste_confianca", 0.0) if leitura else 0.0

    return EpisodioOperador(
        session_id=session_id,
        timestamp_entrada=abertura_ts,
        timestamp_saida=datetime.now().isoformat(),
        direcao=direcao,
        preco_entrada=preco_entrada,
        preco_saida=preco_saida,
        sl=getattr(posicao_fechada, "sl", 0.0),
        tp=getattr(posicao_fechada, "tp", 0.0),
        atr_entrada=float(atr),
        resultado_pts=resultado,
        motivo_saida=motivo_saida,
        fase_sessao=fase,
        qualidade_movimento=qualidade,
        exaustao=exaustao,
        pullback=pullback,
        correlacao_estado=corr,
        divergencia_critica=div,
        risco_armadilha=risco,
        preco_extremo=extremo,
        desvio_vwap_pts=desvio,
        ajuste_confianca_leitura=ajuste_leit,
        confianca_entrada=float(getattr(sinal_entrada, "confianca", 0.0)),
        alinhamento_entrada=float(getattr(sinal_entrada, "alinhamento", 0.0)),
        momentum_entrada=float(getattr(sinal_entrada, "momentum", 0.0)),
        foi_acerto=foi_acerto,
        max_ganho_pts=float(max_ganho),
        eficiencia=eficiencia,
    )


def construir_episodio_neutro(
    sinal: object,
    session_id: str,
    preco_decisao: float,
    preco_avaliacao: float,
    direcao_sugerida: str,
    resultado_hipotetico: float,
    foi_acerto_ficar_fora: bool,
) -> EpisodioOperador:
    """
    Constroi episodio para decisoes NEUTRO (ficou fora do mercado).

    Registra o que TERIA acontecido se tivesse entrado, para que o
    agente aprenda se ficar fora foi a decisao correta.

    motivo_saida = "ficou_fora_<motivo_bloqueio>"
    direcao = direcao que o momentum/macro sugeriam
    resultado_pts = resultado hipotetico (negativo = bom ter ficado fora)
    foi_acerto = True se ficou fora e mercado reverteu ou andou pouco
    """
    agora = datetime.now().isoformat()
    motivo_bloqueio = getattr(sinal, "motivo_bloqueio", "neutro")
    leitura = getattr(sinal, "leitura", None)
    fase = getattr(leitura, "fase_sessao", "") if leitura else ""
    qualidade = getattr(leitura, "qualidade_movimento", "") if leitura else ""
    exaustao = getattr(leitura, "exaustao_detectada", False) if leitura else False
    pullback = getattr(leitura, "pullback_saudavel", False) if leitura else False
    corr = getattr(leitura, "correlacao_estado", "") if leitura else ""
    div = getattr(leitura, "divergencia_critica", False) if leitura else False
    risco = getattr(leitura, "risco_armadilha", "") if leitura else ""
    extremo = getattr(leitura, "preco_extremo", False) if leitura else False
    desvio = getattr(leitura, "desvio_vwap_pts", 0.0) if leitura else 0.0
    ajuste = getattr(leitura, "ajuste_confianca", 0.0) if leitura else 0.0

    return EpisodioOperador(
        session_id=session_id,
        timestamp_entrada=agora,
        timestamp_saida=agora,
        direcao=direcao_sugerida,
        preco_entrada=preco_decisao,
        preco_saida=preco_avaliacao,
        sl=0.0,
        tp=0.0,
        atr_entrada=float(getattr(sinal, "atr", 100.0)),
        resultado_pts=resultado_hipotetico,
        motivo_saida=f"ficou_fora_{motivo_bloqueio}",
        fase_sessao=fase,
        qualidade_movimento=qualidade,
        exaustao=exaustao,
        pullback=pullback,
        correlacao_estado=corr,
        divergencia_critica=div,
        risco_armadilha=risco,
        preco_extremo=extremo,
        desvio_vwap_pts=desvio,
        ajuste_confianca_leitura=ajuste,
        confianca_entrada=float(getattr(sinal, "confianca", 0.0)),
        alinhamento_entrada=float(getattr(sinal, "alinhamento", 0.0)),
        momentum_entrada=float(getattr(sinal, "momentum", 0.0)),
        foi_acerto=foi_acerto_ficar_fora,
        max_ganho_pts=abs(resultado_hipotetico),
        eficiencia=0.0,
    )
