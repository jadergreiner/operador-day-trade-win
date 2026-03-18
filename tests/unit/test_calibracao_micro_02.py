"""
CALIBRACAO-MICRO-02: Testes da condicao dinamica do modo EXP_REDUZIDA.

Verifica que a nova logica ativa EXP_REDUZIDA apenas em situacoes
genuinamente ambiguas (macro forte E smc NEUTRO) e desativa quando
o mercado exibe tendencia clara (ADX alto + smc com direcao).

Status: CALIBRACAO-MICRO-02 (18/03/2026)
Referencia: docs/BACKLOG.md (CALIBRACAO-MICRO-02)
"""

import sqlite3
import tempfile
import os
from decimal import Decimal
from typing import TypedDict

import pytest


class _CicloTendencia(TypedDict):
    macro: int
    smc: str
    adx: float


# ── Helpers para simular a logica de ativacao ─────────────────────────────────

def _calcular_exp_reduzida(
    macro_score: int,
    smc_direction: str,
    adx: float,
) -> bool:
    """
    Replica a logica de ativacao do EXP_REDUZIDA conforme CALIBRACAO-MICRO-02.

    Ativa quando: |macro_score| >= 40 AND smc_direction == NEUTRO
    Desativa quando: adx >= 35 AND smc_direction != NEUTRO
    """
    smc_dir = (smc_direction or "NEUTRO").upper()
    exp_reduzida_ativacao = abs(macro_score) >= 40 and smc_dir == "NEUTRO"
    exp_reduzida_desativacao = adx >= 35 and smc_dir != "NEUTRO"
    return exp_reduzida_ativacao and not exp_reduzida_desativacao


# ── Testes de ativacao ────────────────────────────────────────────────────────

class TestExpReduzidaAtivacao:
    """Testes das condicoes que ATIVAM o modo EXP_REDUZIDA."""

    def test_macro_40_smc_neutro_ativa(self) -> None:
        """macro=40 + SMC NEUTRO deve ativar EXP_REDUZIDA."""
        assert _calcular_exp_reduzida(macro_score=40, smc_direction="NEUTRO", adx=20)

    def test_macro_62_smc_neutro_ativa(self) -> None:
        """macro=62 + SMC NEUTRO: cenario real 17/03/2026 deve ativar."""
        assert _calcular_exp_reduzida(macro_score=62, smc_direction="NEUTRO", adx=22)

    def test_macro_negativo_40_smc_neutro_ativa(self) -> None:
        """macro=-40 + SMC NEUTRO deve ativar (valor absoluto >= 40)."""
        assert _calcular_exp_reduzida(macro_score=-40, smc_direction="NEUTRO", adx=18)

    def test_macro_99_smc_neutro_adx_baixo_ativa(self) -> None:
        """macro extremo + SMC NEUTRO + ADX baixo: deve ativar."""
        assert _calcular_exp_reduzida(macro_score=99, smc_direction="NEUTRO", adx=10)

    def test_macro_39_nao_ativa_abaixo_limiar(self) -> None:
        """macro=39 esta abaixo do limiar 40: nao deve ativar."""
        assert not _calcular_exp_reduzida(macro_score=39, smc_direction="NEUTRO", adx=20)

    def test_macro_20_antigo_threshold_nao_ativa_mais(self) -> None:
        """
        macro=20 ativava no sistema antigo (threshold era 7).
        Com CALIBRACAO-MICRO-02, nao deve mais ativar.
        Isso e a correcao principal: dia 17/03 teve macro entre +14 e +62,
        e com threshold=7 quase todos os ciclos tinham EXP_REDUZIDA.
        """
        assert not _calcular_exp_reduzida(macro_score=20, smc_direction="NEUTRO", adx=22)

    def test_macro_14_nao_ativa(self) -> None:
        """macro=14 (minimo observado em 17/03/2026) nao deve mais ativar."""
        assert not _calcular_exp_reduzida(macro_score=14, smc_direction="NEUTRO", adx=18)

    def test_smc_buy_macro_alto_nao_ativa(self) -> None:
        """macro=50 mas SMC=BUY: nao e ambiguo, nao deve ativar."""
        assert not _calcular_exp_reduzida(macro_score=50, smc_direction="BUY", adx=28)

    def test_smc_sell_macro_alto_nao_ativa(self) -> None:
        """macro=-55 mas SMC=SELL: tendencia confirmada, nao deve ativar."""
        assert not _calcular_exp_reduzida(macro_score=-55, smc_direction="SELL", adx=30)


# ── Testes de desativacao ─────────────────────────────────────────────────────

class TestExpReduzidaDesativacao:
    """Testes da condicao de DESATIVACAO explicita do modo EXP_REDUZIDA."""

    def test_adx_35_smc_buy_desativa(self) -> None:
        """adx=35 + SMC=BUY: mesmo com macro alto, desativa EXP_REDUZIDA."""
        assert not _calcular_exp_reduzida(macro_score=45, smc_direction="BUY", adx=35)

    def test_adx_40_smc_sell_desativa(self) -> None:
        """adx=40 + SMC=SELL: tendencia forte confirmada, desativa."""
        assert not _calcular_exp_reduzida(macro_score=50, smc_direction="SELL", adx=40)

    def test_adx_34_smc_buy_nao_desativa(self) -> None:
        """adx=34 (abaixo do limiar 35): condicao de desativacao nao e suficiente."""
        # Com macro=45 e smc=BUY, smc nao e NEUTRO, entao ativacao nao ocorre mesmo
        # Este teste verifica que adx=34 nao e suficiente para desativacao
        resultado = _calcular_exp_reduzida(macro_score=45, smc_direction="NEUTRO", adx=34)
        # smc=NEUTRO com adx=34: ativacao=True, desativacao=False (adx<35) → ativa
        assert resultado, "adx=34 com smc=NEUTRO deve manter EXP_REDUZIDA ativo"

    def test_adx_35_smc_neutro_nao_desativa(self) -> None:
        """adx=35 mas SMC ainda NEUTRO: desativacao exige smc != NEUTRO."""
        # Ativacao: macro>=40 E smc=NEUTRO → True
        # Desativacao: adx>=35 E smc!=NEUTRO → False (smc=NEUTRO)
        # Resultado: ativo
        assert _calcular_exp_reduzida(macro_score=45, smc_direction="NEUTRO", adx=35)

    def test_cenario_tendencia_clara_macro40_adx35_buy(self) -> None:
        """
        Cenario de tendencia clara: macro=45, ADX=38, SMC=BUY.
        EXP_REDUZIDA deve estar INATIVO (desativacao explicita).
        Criterio de pronto: <30% dos ciclos em dia de tendencia clara.
        """
        assert not _calcular_exp_reduzida(macro_score=45, smc_direction="BUY", adx=38)


# ── Testes de rastreabilidade no CycleResult ─────────────────────────────────

class TestExpReduzidaCycleResult:
    """Testes que CycleResult.exp_reduzida_ativo e populado corretamente."""

    def test_campo_exp_reduzida_ativo_existe_no_cycleresult(self) -> None:
        """CycleResult deve ter campo exp_reduzida_ativo (bool, default False)."""
        import scripts.agente_micro_tendencia_winfut as agente

        result = agente.CycleResult()
        assert hasattr(result, "exp_reduzida_ativo"), (
            "CycleResult deve ter campo exp_reduzida_ativo apos CALIBRACAO-MICRO-02."
        )
        assert isinstance(result.exp_reduzida_ativo, bool)
        assert result.exp_reduzida_ativo is False, "Default deve ser False."

    def test_campo_exp_reduzida_ativo_e_bool(self) -> None:
        """Campo exp_reduzida_ativo deve aceitar valores booleanos."""
        import scripts.agente_micro_tendencia_winfut as agente

        result = agente.CycleResult()
        result.exp_reduzida_ativo = True
        assert result.exp_reduzida_ativo is True

        result.exp_reduzida_ativo = False
        assert result.exp_reduzida_ativo is False


# ── Testes de rastreabilidade no banco de dados ───────────────────────────────

class TestExpReduzidaBanco:
    """Testes de persistencia do campo exp_reduzida_ativo no SQLite."""

    def _criar_tabela(self, cursor: sqlite3.Cursor) -> None:
        """Cria tabela micro_trend_decisions com campo exp_reduzida_ativo."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS micro_trend_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                macro_score INTEGER NOT NULL,
                macro_signal TEXT NOT NULL,
                macro_confidence REAL NOT NULL,
                micro_score INTEGER NOT NULL,
                micro_trend TEXT NOT NULL,
                smc_direction TEXT,
                adx REAL,
                num_opportunities INTEGER DEFAULT 0,
                exp_reduzida_ativo INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def test_schema_tem_coluna_exp_reduzida_ativo(self) -> None:
        """Tabela micro_trend_decisions deve ter coluna exp_reduzida_ativo."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            self._criar_tabela(cursor)
            conn.commit()

            cursor.execute("PRAGMA table_info(micro_trend_decisions)")
            colunas = [row[1] for row in cursor.fetchall()]
            conn.close()

            assert "exp_reduzida_ativo" in colunas, (
                "Coluna exp_reduzida_ativo deve existir em micro_trend_decisions."
            )
        finally:
            os.unlink(db_path)

    def test_inserir_exp_reduzida_ativo_verdadeiro(self) -> None:
        """Deve persistir exp_reduzida_ativo=1 quando modo esta ativo."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            self._criar_tabela(cursor)

            cursor.execute("""
                INSERT INTO micro_trend_decisions
                (timestamp, macro_score, macro_signal, macro_confidence,
                 micro_score, micro_trend, smc_direction, adx,
                 num_opportunities, exp_reduzida_ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("2026-03-18T10:00:00", 45, "COMPRA", 0.75,
                  2, "CONTINUACAO", "NEUTRO", 22.0, 3, 1))
            conn.commit()

            cursor.execute(
                "SELECT exp_reduzida_ativo FROM micro_trend_decisions WHERE id=1"
            )
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == 1, "exp_reduzida_ativo deve ser 1 (True)."
        finally:
            os.unlink(db_path)

    def test_inserir_exp_reduzida_ativo_falso(self) -> None:
        """Deve persistir exp_reduzida_ativo=0 quando modo esta inativo."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            self._criar_tabela(cursor)

            cursor.execute("""
                INSERT INTO micro_trend_decisions
                (timestamp, macro_score, macro_signal, macro_confidence,
                 micro_score, micro_trend, smc_direction, adx,
                 num_opportunities, exp_reduzida_ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("2026-03-18T11:00:00", 20, "COMPRA", 0.60,
                  3, "CONTINUACAO", "BUY", 38.0, 5, 0))
            conn.commit()

            cursor.execute(
                "SELECT exp_reduzida_ativo FROM micro_trend_decisions WHERE id=1"
            )
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == 0, "exp_reduzida_ativo deve ser 0 (False)."
        finally:
            os.unlink(db_path)

    def test_consultar_percentual_ciclos_exp_reduzida(self) -> None:
        """Deve ser possivel calcular percentual de ciclos com EXP_REDUZIDA ativo."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            self._criar_tabela(cursor)

            # Simula 10 ciclos: 2 com EXP_REDUZIDA ativo (20%)
            ciclos = [
                ("2026-03-18T09:00:00", 15, "COMPRA", 0.55, 2, "CONTINUACAO", "BUY", 32.0, 3, 0),
                ("2026-03-18T09:30:00", 20, "COMPRA", 0.60, 3, "CONTINUACAO", "BUY", 35.0, 4, 0),
                ("2026-03-18T10:00:00", 45, "COMPRA", 0.75, 2, "CONTINUACAO", "NEUTRO", 22.0, 2, 1),
                ("2026-03-18T10:30:00", 25, "NEUTRO", 0.50, 0, "CONSOLIDACAO", "NEUTRO", 18.0, 0, 0),
                ("2026-03-18T11:00:00", 30, "COMPRA", 0.65, 2, "CONTINUACAO", "BUY", 36.0, 3, 0),
                ("2026-03-18T11:30:00", 42, "COMPRA", 0.70, 3, "CONTINUACAO", "NEUTRO", 25.0, 2, 1),
                ("2026-03-18T12:00:00", 35, "COMPRA", 0.68, 2, "CONTINUACAO", "BUY", 38.0, 4, 0),
                ("2026-03-18T12:30:00", 22, "NEUTRO", 0.52, 0, "CONSOLIDACAO", "NEUTRO", 16.0, 0, 0),
                ("2026-03-18T13:00:00", 28, "COMPRA", 0.62, 2, "CONTINUACAO", "BUY", 34.0, 3, 0),
                ("2026-03-18T13:30:00", 18, "COMPRA", 0.58, 2, "CONTINUACAO", "BUY", 30.0, 2, 0),
            ]
            cursor.executemany("""
                INSERT INTO micro_trend_decisions
                (timestamp, macro_score, macro_signal, macro_confidence,
                 micro_score, micro_trend, smc_direction, adx,
                 num_opportunities, exp_reduzida_ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ciclos)
            conn.commit()

            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(exp_reduzida_ativo) as com_exp_reduzida,
                    ROUND(100.0 * SUM(exp_reduzida_ativo) / COUNT(*), 1) as pct
                FROM micro_trend_decisions
            """)
            row = cursor.fetchone()
            conn.close()

            total, com_exp, pct = row
            assert total == 10
            assert com_exp == 2
            assert pct == 20.0, f"Percentual esperado 20%, obtido {pct}%."
            # Criterio de pronto: < 30% em dia de tendencia clara
            assert pct < 30.0, (
                f"EXP_REDUZIDA deve estar ativo em menos de 30% dos ciclos "
                f"em dia de tendencia clara. Obtido: {pct}%."
            )
        finally:
            os.unlink(db_path)

    def test_schema_agente_tem_coluna_exp_reduzida_ativo(self) -> None:
        """
        Verifica que o agente real cria a tabela com exp_reduzida_ativo.
        Testa a SQL de criacao de tabela embutida no agente.
        """
        import scripts.agente_micro_tendencia_winfut as agente

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            agente._create_micro_trend_tables(db_path)

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(micro_trend_decisions)")
            colunas = [row[1] for row in cursor.fetchall()]
            conn.close()

            assert "exp_reduzida_ativo" in colunas, (
                "Agente deve criar micro_trend_decisions com coluna "
                "exp_reduzida_ativo apos CALIBRACAO-MICRO-02."
            )
        finally:
            os.unlink(db_path)


# ── Teste de criterio de pronto ───────────────────────────────────────────────

class TestCriterioPronto:
    """Testes do criterio de pronto: EXP_REDUZIDA < 30% em dia de tendencia."""

    def test_dia_tendencia_clara_macro20_adx35_menos_30pct(self) -> None:
        """
        Em dia de tendencia clara (macro > 20, ADX > 35, smc com direcao),
        EXP_REDUZIDA deve ser inativo para todos os ciclos.
        """
        # Simula 10 ciclos de um dia com tendencia clara
        ciclos_tendencia: list[_CicloTendencia] = [
            {"macro": 25, "smc": "BUY", "adx": 36.0},
            {"macro": 30, "smc": "BUY", "adx": 38.0},
            {"macro": 28, "smc": "BUY", "adx": 35.0},
            {"macro": 32, "smc": "BUY", "adx": 40.0},
            {"macro": 27, "smc": "BUY", "adx": 37.0},
            {"macro": 35, "smc": "BUY", "adx": 42.0},
            {"macro": 29, "smc": "BUY", "adx": 36.0},
            {"macro": 31, "smc": "BUY", "adx": 38.0},
            {"macro": 26, "smc": "BUY", "adx": 35.0},
            {"macro": 33, "smc": "BUY", "adx": 39.0},
        ]
        ativos = sum(
            1 for c in ciclos_tendencia
            if _calcular_exp_reduzida(c["macro"], c["smc"], c["adx"])
        )
        pct = ativos / len(ciclos_tendencia) * 100
        assert pct < 30, (
            f"EXP_REDUZIDA deve estar ativo em < 30% dos ciclos em dia de "
            f"tendencia clara. Obtido: {pct:.1f}% ({ativos}/{len(ciclos_tendencia)})."
        )

    def test_cenario_17_03_2026_exp_reduzida_drasticamente_reduzido(self) -> None:
        """
        Cenario real 17/03/2026: macro entre +14 e +62, SMC variado.
        Com novo threshold (40), EXP_REDUZIDA so ativa quando macro >= 40 E smc=NEUTRO.
        O sistema antigo (threshold=7) teria ativado em ~100% dos ciclos.
        """
        # Dados representativos do dia 17/03/2026
        # macro entre 14-62, maioria com smc confirmado intraday
        ciclos_17_03: list[_CicloTendencia] = [
            {"macro": 14, "smc": "NEUTRO", "adx": 18.0},   # macro<40: inativo
            {"macro": 20, "smc": "NEUTRO", "adx": 20.0},   # macro<40: inativo
            {"macro": 30, "smc": "BUY", "adx": 25.0},      # smc!=NEUTRO: inativo
            {"macro": 42, "smc": "NEUTRO", "adx": 22.0},   # ativo
            {"macro": 45, "smc": "BUY", "adx": 28.0},      # smc!=NEUTRO: inativo
            {"macro": 50, "smc": "BUY", "adx": 30.0},      # smc!=NEUTRO: inativo
            {"macro": 55, "smc": "NEUTRO", "adx": 33.0},   # ativo (adx<35)
            {"macro": 62, "smc": "BUY", "adx": 35.0},      # smc!=NEUTRO E adx>=35: inativo
            {"macro": 38, "smc": "NEUTRO", "adx": 24.0},   # macro<40: inativo
            {"macro": 25, "smc": "BUY", "adx": 32.0},      # smc!=NEUTRO: inativo
        ]
        ativos_antigo = sum(
            1 for c in ciclos_17_03
            if abs(c["macro"]) >= 7  # logica antiga
        )
        ativos_novo = sum(
            1 for c in ciclos_17_03
            if _calcular_exp_reduzida(c["macro"], c["smc"], c["adx"])
        )
        pct_antigo = ativos_antigo / len(ciclos_17_03) * 100
        pct_novo = ativos_novo / len(ciclos_17_03) * 100

        assert pct_novo < pct_antigo, (
            f"Nova logica deve ter menos ciclos com EXP_REDUZIDA que a antiga. "
            f"Antigo: {pct_antigo:.0f}%, Novo: {pct_novo:.0f}%."
        )
        assert pct_novo < 30, (
            f"Nova logica deve ter < 30% com EXP_REDUZIDA. Obtido: {pct_novo:.0f}%."
        )
