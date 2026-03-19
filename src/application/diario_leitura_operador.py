"""
Leitura de Mercado do Agente Diarios — Percepcao de Operador Comerciante.

Este modulo nao calcula indicadores tecnicos. Ele le o mercado como um
operador experiente leria: identificando contexto, armadilhas, exaustao,
barato/caro relativo e correlacoes com outros mercados.

Fontes de percepcao:
  1. Contexto do dia (onde estamos no range, fase da sessao)
  2. Qualidade do movimento (exaustao, momentum real vs falso)
  3. Correlacoes inter-mercado (dolar, SP500, juros, commodities)
  4. Armadilhas classicas (fakeout, squeeze, gap fill trap)
  5. Nocao de barato/caro relativo (VWAP, extremos do dia, desvio)
  6. Mudanca de cenario (quando o que valia de manha nao vale mais)

Saida: LeituraOperador — resumo estruturado da percepcao de mercado
que enriquece o DiarioOrderManager.consolidar_sinal() com contexto
que indicadores tecnicos nao capturam.

Status: v1.0 (17/03/2026)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional


# ────────────────────────────────────────────────────────────────
# Enums e constantes de percepcao
# ────────────────────────────────────────────────────────────────

# Fase da sessao de trading
FASE_ABERTURA = "ABERTURA"       # 09:00 - 10:00 (alta volatilidade, armadilhas)
FASE_MANHA = "MANHA"             # 10:00 - 12:00 (tendencia principal do dia)
FASE_ALMOCO = "ALMOCO"           # 12:00 - 13:30 (liquidez reduzida, evitar)
FASE_TARDE = "TARDE"             # 13:30 - 16:00 (segundo movimento do dia)
FASE_FECHAMENTO = "FECHAMENTO"   # 16:00 - 17:30 (reversao ou aceleracao)

# Posicao no range diario
POSICAO_EXTREMO_ALTO = "EXTREMO_ALTO"     # top 10% do range
POSICAO_ALTO = "ALTO"                      # top 11-35% do range
POSICAO_MEIO = "MEIO"                      # meio do range (30-70%)
POSICAO_BAIXO = "BAIXO"                    # bottom 11-35% do range
POSICAO_EXTREMO_BAIXO = "EXTREMO_BAIXO"  # bottom 10% do range

# Qualidade do movimento
MOVIMENTO_FORTE = "FORTE"           # direcional, volume crescente
MOVIMENTO_FRACO = "FRACO"           # direc. com volume decrescente (exaustao)
MOVIMENTO_CHOP = "CHOP"             # sem direcao, lateralizando
MOVIMENTO_SPIKE = "SPIKE"           # movimento rapido sem continuidade tipica

# Estado de correlacao inter-mercado
CORRELACAO_ALINHADA = "ALINHADA"    # dolar, SP500, juros todos apontando mesmo lado
CORRELACAO_MISTA = "MISTA"          # sinais contraditórios entre mercados
CORRELACAO_DIVERGENTE = "DIVERGENTE"  # WIN indo contra os correlatos principais

# Risco de armadilha
ARMADILHA_ALTA = "ALTA"
ARMADILHA_MEDIA = "MEDIA"
ARMADILHA_BAIXA = "BAIXA"


# ────────────────────────────────────────────────────────────────
# Estrutura de saida
# ────────────────────────────────────────────────────────────────

@dataclass
class LeituraOperador:
    """
    Percepcao de mercado do Agente Diarios — visao de operador comerciante.

    Nao e um conjunto de indicadores. E uma interpretacao contextual
    que informa se o momento e adequado para operar, em qual direcao
    faz mais sentido e quais armadilhas evitar.
    """
    timestamp: str

    # ── Contexto do dia ──────────────────────────────────────────
    fase_sessao: str           # ABERTURA, MANHA, ALMOCO, TARDE, FECHAMENTO
    posicao_no_range: str      # onde o preco esta no range do dia
    range_pts: float           # amplitude total do dia em pontos
    range_expandindo: bool     # range esta crescendo (true) ou comprimindo

    # ── Qualidade do movimento atual ────────────────────────────
    qualidade_movimento: str   # FORTE, FRACO, CHOP, SPIKE
    exaustao_detectada: bool   # movimento perdendo forca (velocidade cai)
    pullback_saudavel: bool    # recuo dentro de tendencia (oportunidade)

    # ── Nocao de barato/caro relativo ───────────────────────────
    desvio_vwap_pts: float     # preco atual - VWAP em pontos
    desvio_vwap_direcao: str   # "ACIMA", "ABAIXO", "NA_VWAP"
    preco_extremo: bool        # esta em extremo do dia (top/bottom 10%)
    potencial_mean_reversion: bool  # caro/barato demais → candidato a reverter

    # ── Correlacoes inter-mercado ────────────────────────────────
    correlacao_estado: str     # ALINHADA, MISTA, DIVERGENTE
    dolar_favoravel: bool      # dolar apoia a direcao do WIN
    sp500_favoravel: bool      # SP500 apoia a direcao do WIN
    commodities_favoravel: bool  # commodities/PETR4/VALE3 apoiam
    divergencia_critica: bool  # WIN contradiz todos os correlatos (perigo)

    # ── Armadilhas identificadas ─────────────────────────────────
    risco_armadilha: str       # ALTA, MEDIA, BAIXA
    armadilhas: list[str]      # descricao das armadilhas identificadas

    # ── Mudanca de cenario ───────────────────────────────────────
    cenario_mudou: bool        # algo mudou desde a abertura
    motivo_mudanca: str        # o que mudou

    # ── Veredicto operacional ────────────────────────────────────
    momento_favoravel: bool    # e um bom momento para operar?
    direcao_preferida: str     # "BUY", "SELL", "NEUTRO"
    confianca_leitura: float   # 0.0-1.0 (confianca na leitura)
    resumo: str                # frase curta do operador sobre o momento

    # Ajuste de confianca a aplicar no sinal final
    # Positivo = boost, Negativo = penalidade
    ajuste_confianca: float = 0.0


# ────────────────────────────────────────────────────────────────
# Motor de leitura
# ────────────────────────────────────────────────────────────────

class LeituraDeOperador:
    """
    Interpreta o mercado como um operador comerciante experiente.

    Recebe os dados brutos (candles, macro, guardian, decisao) e
    produz uma LeituraOperador — percepcao contextual que vai alem
    de indicadores tecnicos.
    """

    # ── Fase da sessao ───────────────────────────────────────────

    def _fase_sessao(self) -> str:
        hora = datetime.now().time()
        if hora < time(10, 0):
            return FASE_ABERTURA
        elif hora < time(12, 0):
            return FASE_MANHA
        elif hora < time(13, 30):
            return FASE_ALMOCO
        elif hora < time(16, 0):
            return FASE_TARDE
        else:
            return FASE_FECHAMENTO

    # ── Posicao no range do dia ──────────────────────────────────

    def _posicao_no_range(
        self, preco: float, high: float, low: float
    ) -> str:
        if high <= low:
            return POSICAO_MEIO
        pct = (preco - low) / (high - low)
        if pct >= 0.90:
            return POSICAO_EXTREMO_ALTO
        elif pct >= 0.65:
            return POSICAO_ALTO
        elif pct <= 0.10:
            return POSICAO_EXTREMO_BAIXO
        elif pct <= 0.35:
            return POSICAO_BAIXO
        else:
            return POSICAO_MEIO

    # ── Qualidade do movimento ───────────────────────────────────

    def _qualidade_movimento(self, candles: list) -> tuple[str, bool, bool]:
        """
        Avalia qualidade do movimento das ultimas velas.

        Retorna (qualidade, exaustao_detectada, pullback_saudavel).

        Exaustao: velas na mesma direcao mas com corpos decrescentes
        Pullback saudavel: movimento contra a tendencia com volume menor
        CHOP: alternancia sem direcao
        SPIKE: vela muito maior que as anteriores (movimento suspeito)
        """
        if len(candles) < 5:
            return MOVIMENTO_CHOP, False, False

        # Calcular corpos e direcoes das ultimas 5 velas
        ultimas = candles[-5:]
        corpos = [abs(float(c.close.value) - float(c.open.value)) for c in ultimas]
        direcoes = [1 if float(c.close.value) >= float(c.open.value) else -1 for c in ultimas]

        corpo_medio = sum(corpos) / len(corpos) if corpos else 0
        ultimo_corpo = corpos[-1]

        # SPIKE: ultima vela muito maior que media (>2.5x)
        if corpo_medio > 0 and ultimo_corpo > corpo_medio * 2.5:
            return MOVIMENTO_SPIKE, False, False

        # CHOP: alternancia de direcoes sem tendencia
        mudancas = sum(1 for i in range(1, len(direcoes)) if direcoes[i] != direcoes[i - 1])
        if mudancas >= 3:
            return MOVIMENTO_CHOP, False, False

        # Tendencia: maioria na mesma direcao
        soma_dir = sum(direcoes)
        tendencia_clara = abs(soma_dir) >= 3

        if not tendencia_clara:
            return MOVIMENTO_CHOP, False, False

        # Exaustao: corpos decrescentes em tendencia (ultimas 3 velas)
        if len(corpos) >= 3:
            exaustao = corpos[-3] > corpos[-2] > corpos[-1] and corpos[-1] < corpo_medio * 0.5
        else:
            exaustao = False

        # Pullback saudavel: 1-2 velas contra, corpo menor que a tendencia
        dir_tendencia = 1 if soma_dir > 0 else -1
        if direcoes[-1] != dir_tendencia and ultimo_corpo < corpo_medio * 0.7:
            pullback = True
        else:
            pullback = False

        qualidade = MOVIMENTO_FRACO if exaustao else MOVIMENTO_FORTE
        return qualidade, exaustao, pullback

    # ── VWAP aproximado ─────────────────────────────────────────

    def _calcular_vwap_aproximado(self, candles: list) -> float:
        """
        VWAP aproximado: media ponderada pelo volume de todas as velas do dia.
        Se nao ha volume, usa TWAP (media temporal).
        """
        if not candles:
            return 0.0

        soma_pv = 0.0
        soma_v = 0.0
        for c in candles:
            preco_tipico = (float(c.high.value) + float(c.low.value) + float(c.close.value)) / 3
            vol = float(getattr(c, "volume", None) or 1)
            soma_pv += preco_tipico * vol
            soma_v += vol

        return soma_pv / soma_v if soma_v > 0 else float(candles[-1].close.value)

    # ── Barato/caro relativo ─────────────────────────────────────

    def _avaliar_barato_caro(
        self, preco: float, vwap: float, atr: float, high: float, low: float
    ) -> tuple[float, str, bool, bool]:
        """
        Avalia se o preco esta barato, caro ou na media.

        Retorna (desvio_pts, direcao, preco_extremo, candidato_mean_reversion).

        Operador pensa: "O mercado ja andou muito? Estou perseguindo?"
        """
        desvio = preco - vwap
        range_dia = high - low if high > low else atr

        # Desvio em multiplos de ATR
        desvio_em_atr = abs(desvio) / atr if atr > 0 else 0

        if desvio > 0:
            direcao = "ACIMA"
        elif desvio < 0:
            direcao = "ABAIXO"
        else:
            direcao = "NA_VWAP"

        # Extremo do dia: top/bottom 10%
        if range_dia > 0:
            pct_range = (preco - low) / range_dia
            preco_extremo = pct_range >= 0.90 or pct_range <= 0.10
        else:
            preco_extremo = False

        # Candidato a mean reversion: desvio > 1.5 ATR E em extremo
        mean_reversion = desvio_em_atr > 1.5 and preco_extremo

        return desvio, direcao, preco_extremo, mean_reversion

    # ── Correlacoes inter-mercado ────────────────────────────────

    def _avaliar_correlacoes(
        self,
        direcao_win: str,
        macro_items: Optional[list],
        decisao: object,
    ) -> tuple[str, bool, bool, bool, bool]:
        """
        Avalia se os mercados correlacionados apoiam a direcao do WIN.

        Retorna (estado, dolar_fav, sp500_fav, commodities_fav, divergencia_critica).

        Logica do operador:
        - Se WIN quer subir mas dolar esta forte → perigo (correlacao inversa)
        - Se WIN quer subir e SP500 tambem sobe → confirmacao
        - Se WIN vai contra TODOS os correlatos → armadilha provavel
        """
        if direcao_win == "NEUTRO":
            return CORRELACAO_MISTA, False, False, False, False

        # Extrair scores dos correlatos dos items macro
        scores = {}
        if macro_items:
            for item in macro_items:
                cat = item.get("category", "")
                sym = item.get("symbol", "")
                score = float(item.get("score", 0))
                scores[sym] = (cat, score)

        def _score_categoria(categoria: str) -> float:
            total = sum(s for (c, s) in scores.values() if c == categoria)
            return total

        score_dolar = _score_categoria("DOLAR_CAMBIO")
        score_sp500 = sum(s for sym, (cat, s) in scores.items()
                          if cat == "INDICES_GLOBAIS")
        score_commodities = _score_categoria("COMMODITIES") + sum(
            s for sym, (cat, s) in scores.items()
            if sym in ("PETR4", "VALE3")
        )

        # Fallback: usar biases do QuantumOperatorEngine
        macro_bias = str(getattr(decisao, "macro_bias", "NEUTRO"))
        fundamental_bias = str(getattr(decisao, "fundamental_bias", "NEUTRO"))

        win_sobe = direcao_win == "BUY"

        # Dolar favoravel: WIN sobe → dolar fraco (score dolar negativo)
        # WIN cai → dolar forte (score dolar positivo)
        if score_dolar != 0:
            dolar_fav = (win_sobe and score_dolar < 0) or (not win_sobe and score_dolar > 0)
        else:
            # Fallback via macro_bias
            dolar_fav = (win_sobe and "BULL" in macro_bias) or (not win_sobe and "BEAR" in macro_bias)

        # SP500 favoravel: correlacao direta
        if score_sp500 != 0:
            sp500_fav = (win_sobe and score_sp500 > 0) or (not win_sobe and score_sp500 < 0)
        else:
            sp500_fav = (win_sobe and "BULL" in macro_bias) or (not win_sobe and "BEAR" in macro_bias)

        # Commodities favoraveis: correlacao direta (Brasil exportador)
        if score_commodities != 0:
            comm_fav = (win_sobe and score_commodities > 0) or (not win_sobe and score_commodities < 0)
        else:
            comm_fav = (win_sobe and "BULL" in fundamental_bias) or (not win_sobe and "BEAR" in fundamental_bias)

        # Divergencia critica: WIN vai contra TODOS os tres correlatos
        divergencia = not dolar_fav and not sp500_fav and not comm_fav

        # Estado geral
        favoraveis = sum([dolar_fav, sp500_fav, comm_fav])
        if favoraveis >= 2:
            estado = CORRELACAO_ALINHADA
        elif favoraveis == 1:
            estado = CORRELACAO_MISTA
        else:
            estado = CORRELACAO_DIVERGENTE

        return estado, dolar_fav, sp500_fav, comm_fav, divergencia

    # ── Armadilhas classicas ─────────────────────────────────────

    def _identificar_armadilhas(
        self,
        fase: str,
        posicao: str,
        qualidade: str,
        exaustao: bool,
        correlacao: str,
        divergencia: bool,
        range_pts: float,
        desvio_vwap_pts: float,
        atr: float,
        candles: list,
    ) -> tuple[str, list[str]]:
        """
        Identifica armadilhas classicas que o operador experiente evitaria.

        Armadilhas monitoradas:
        1. Abertura falsa (ABERTURA + extremo): gap que fecha
        2. Fakeout de range: rompimento sem volume
        3. Squeeze de liquidez: spike no almoco sem continuidade
        4. Exaustao disfarçada: movimento forte que perdeu forca
        5. Armadilha de correlacao: WIN diverge dos correlatos
        6. Perseguir o movimento: entrar caro demais (VWAP muito desviado)
        """
        armadilhas = []
        score_risco = 0

        # 1. ABERTURA FALSA: primeiros 60 min em extremo do dia
        if fase == FASE_ABERTURA and posicao in (POSICAO_EXTREMO_ALTO, POSICAO_EXTREMO_BAIXO):
            armadilhas.append(
                "ABERTURA_FALSA: Preco em extremo nos primeiros 60 min. "
                "Gaps de abertura frequentemente fecham. Aguardar confirmacao."
            )
            score_risco += 2

        # 2. FAKEOUT: rompimento de range com qualidade fraca
        if posicao in (POSICAO_EXTREMO_ALTO, POSICAO_EXTREMO_BAIXO) and qualidade == MOVIMENTO_FRACO:
            armadilhas.append(
                "FAKEOUT_PROVAVEL: Rompimento de extremo com movimento fraco. "
                "Rompimentos verdadeiros tem volume e corpo crescentes."
            )
            score_risco += 2

        # 3. SQUEEZE DE LIQUIDEZ: spike no almoco
        if fase == FASE_ALMOCO and qualidade == MOVIMENTO_SPIKE:
            armadilhas.append(
                "SPIKE_ALMOCO: Movimento rapido no horario de baixa liquidez. "
                "Spikes sem participacao institucional revertam rapidamente."
            )
            score_risco += 3

        # 4. EXAUSTAO: movimento perdeu forca
        if exaustao:
            armadilhas.append(
                "EXAUSTAO_DETECTADA: Velas na mesma direcao com corpos decrescentes. "
                "Participantes esgotando posicoes — proximo movimento pode reverter."
            )
            score_risco += 2

        # 5. DIVERGENCIA DE CORRELACAO
        if divergencia:
            armadilhas.append(
                "DIVERGENCIA_CRITICA: WIN indo contra dolar, SP500 e commodities. "
                "Movimentos divergentes dos correlatos raramente sustentam. Perigo alto."
            )
            score_risco += 3

        # 6. PERSEGUINDO O MOVIMENTO: desvio VWAP excessivo
        if atr > 0 and abs(desvio_vwap_pts) > atr * 1.8:
            lado = "CARO" if desvio_vwap_pts > 0 else "BARATO"
            armadilhas.append(
                f"PERSEGUINDO_MOVIMENTO: Preco {lado} demais ({abs(desvio_vwap_pts):.0f} pts "
                f"da VWAP = {abs(desvio_vwap_pts)/atr:.1f}x ATR). "
                "Entrar agora e comprar/vender no extremo."
            )
            score_risco += 2

        # 7. CHOP no fechamento: mercado sem direcao no final do dia
        if fase == FASE_FECHAMENTO and qualidade == MOVIMENTO_CHOP:
            armadilhas.append(
                "CHOP_FECHAMENTO: Mercado lateralizando no fechamento. "
                "Posicoes abertas no CHOP do fechamento frequentemente viram overnight."
            )
            score_risco += 1

        # Classificar risco
        if score_risco >= 5:
            risco = ARMADILHA_ALTA
        elif score_risco >= 2:
            risco = ARMADILHA_MEDIA
        else:
            risco = ARMADILHA_BAIXA

        return risco, armadilhas

    # ── Mudanca de cenario ───────────────────────────────────────

    def _detectar_mudanca_cenario(
        self,
        guardian_state: object,
        macro_items: Optional[list],
        decisao: object,
    ) -> tuple[bool, str]:
        """
        Detecta se o cenario mudou desde o inicio da sessao.

        Um operador experiente para quando as regras do jogo mudam:
        - Guardian ativou alerta critico
        - Score macro degradou > 15 pontos
        - Divergencia nova entre mercados que antes estavam alinhados
        """
        motivos = []

        # Guardian com alertas
        alertas = getattr(guardian_state, "active_alerts", []) or []
        criticos = [a for a in alertas if getattr(a, "severity", "") == "CRITICAL"]
        if criticos:
            motivos.append(f"Guardian: {len(criticos)} alerta(s) critico(s)")

        # Kill switch ativo
        if getattr(guardian_state, "active_kill_switch", False):
            motivos.append(f"Guardian kill switch: {getattr(guardian_state, 'kill_switch_reason', '')}")

        # Macro bias mudou (Guardian rastreia isso)
        scenario_changes = getattr(guardian_state, "scenario_changes", []) or []
        if isinstance(scenario_changes, (list, tuple)):
            if scenario_changes:
                motivos.append(f"Cenario macro: {scenario_changes[-1]}")
        elif scenario_changes:
            motivos.append(f"Cenario macro: {scenario_changes}")

        mudou = len(motivos) > 0
        return mudou, "; ".join(motivos) if motivos else ""

    # ── Veredicto final ──────────────────────────────────────────

    def _veredicto(
        self,
        fase: str,
        qualidade: str,
        exaustao: bool,
        pullback: bool,
        correlacao: str,
        divergencia: bool,
        risco_armadilha: str,
        posicao: str,
        mean_reversion: bool,
        cenario_mudou: bool,
        direcao_decisao: str,
    ) -> tuple[bool, str, float, str, float]:
        """
        Gera o veredicto operacional: e um bom momento para entrar?

        Retorna (momento_favoravel, direcao_preferida, confianca_leitura,
                 resumo, ajuste_confianca).

        Um bom momento para o operador e quando:
        - Qualidade FORTE + Correlacao ALINHADA + risco BAIXO = maxima confianca
        - Pullback saudavel em tendencia = oportunidade classica
        - Exaustao + extremo = contra-tendencia (mean reversion)

        Nao e bom momento quando:
        - Almoco + CHOP = liquidez ruim
        - Divergencia critica
        - Exaustao sem extremo (movimento morrendo no meio)
        - Cenario mudou (regras do jogo diferentes)
        """
        ajuste = 0.0

        # Penalidades
        if fase == FASE_ALMOCO:
            ajuste -= 0.15  # liquidez ruim, qualquer coisa pode acontecer
        if divergencia:
            ajuste -= 0.20  # risco alto de armadilha
        if risco_armadilha == ARMADILHA_ALTA:
            ajuste -= 0.15
        elif risco_armadilha == ARMADILHA_MEDIA:
            ajuste -= 0.07
        if cenario_mudou:
            ajuste -= 0.12
        if qualidade == MOVIMENTO_CHOP:
            ajuste -= 0.10
        if exaustao and posicao not in (POSICAO_EXTREMO_ALTO, POSICAO_EXTREMO_BAIXO):
            ajuste -= 0.08  # exaustao no meio = nao ha tese clara

        # Bonos
        if correlacao == CORRELACAO_ALINHADA:
            ajuste += 0.10
        if pullback and qualidade != MOVIMENTO_CHOP:
            ajuste += 0.08  # pullback saudavel = entrada classica
        if fase in (FASE_MANHA, FASE_TARDE):
            ajuste += 0.05  # melhores horarios de liquidez

        # Direcao preferida
        if mean_reversion:
            # Caro demais → prefere vender; barato demais → prefere comprar
            direcao_pref = "SELL" if posicao in (POSICAO_EXTREMO_ALTO, POSICAO_ALTO) else "BUY"
            resumo_base = "Mean reversion: preco em extremo, preferir contra-tendencia"
        elif pullback:
            direcao_pref = direcao_decisao  # pullback confirma a tendencia
            resumo_base = "Pullback saudavel: entrada na direcao da tendencia"
        elif exaustao:
            direcao_pref = "NEUTRO"
            resumo_base = "Exaustao detectada: aguardar confirmacao de nova direcao"
        elif divergencia:
            direcao_pref = "NEUTRO"
            resumo_base = "Divergencia critica com correlatos: evitar posicao agora"
        elif qualidade == MOVIMENTO_FORTE and correlacao == CORRELACAO_ALINHADA:
            direcao_pref = direcao_decisao
            resumo_base = "Movimento forte com correlatos alinhados: momento favoravel"
        elif fase == FASE_ALMOCO:
            direcao_pref = "NEUTRO"
            resumo_base = "Horario de almoco: liquidez reduzida, risco de spike falso"
        else:
            direcao_pref = direcao_decisao
            resumo_base = f"Mercado {qualidade.lower()}, fase {fase.lower()}"

        # Momento favoravel: ajuste final positivo E sem divergencia critica
        momento_fav = ajuste > -0.10 and not divergencia and fase != FASE_ALMOCO

        # Confianca da leitura (independente da confianca do sinal)
        confianca = max(0.30, min(0.95, 0.65 + ajuste))

        return momento_fav, direcao_pref, confianca, resumo_base, ajuste

    # ── Metodo principal ─────────────────────────────────────────

    def ler(
        self,
        candles: list,
        decisao: object,
        guardian_state: object,
        macro_items: Optional[list] = None,
        atr: float = 200.0,
    ) -> LeituraOperador:
        """
        Produz a LeituraOperador a partir de todas as fontes disponiveis.

        Parametros:
            candles: candles M15 ao vivo (minimo 5, ideal 50+)
            decisao: TradingDecision do QuantumOperatorEngine
            guardian_state: GuardianState atual
            macro_items: lista de items do MacroScoreResult (opcional)
            atr: ATR atual calculado por calcular_atr()
        """
        agora = datetime.now().isoformat()

        if not candles:
            return LeituraOperador(
                timestamp=agora,
                fase_sessao=self._fase_sessao(),
                posicao_no_range=POSICAO_MEIO,
                range_pts=0.0,
                range_expandindo=False,
                qualidade_movimento=MOVIMENTO_CHOP,
                exaustao_detectada=False,
                pullback_saudavel=False,
                desvio_vwap_pts=0.0,
                desvio_vwap_direcao="NA_VWAP",
                preco_extremo=False,
                potencial_mean_reversion=False,
                correlacao_estado=CORRELACAO_MISTA,
                dolar_favoravel=False,
                sp500_favoravel=False,
                commodities_favoravel=False,
                divergencia_critica=False,
                risco_armadilha=ARMADILHA_MEDIA,
                armadilhas=["sem_dados_candles"],
                cenario_mudou=False,
                motivo_mudanca="",
                momento_favoravel=False,
                direcao_preferida="NEUTRO",
                confianca_leitura=0.30,
                resumo="Sem dados de candles para leitura",
                ajuste_confianca=-0.15,
            )

        # Dados basicos dos candles
        preco = float(candles[-1].close.value)
        high = max(float(c.high.value) for c in candles)
        low = min(float(c.low.value) for c in candles)
        range_pts = high - low

        # Range expandindo? Comparar com 80% dos candles anteriores
        if len(candles) >= 10:
            range_anterior = max(float(c.high.value) for c in candles[:-5]) - \
                             min(float(c.low.value) for c in candles[:-5])
            range_atual = max(float(c.high.value) for c in candles[-5:]) - \
                          min(float(c.low.value) for c in candles[-5:])
            range_expandindo = range_atual > range_anterior * 1.1
        else:
            range_expandindo = False

        fase = self._fase_sessao()
        posicao = self._posicao_no_range(preco, high, low)
        qualidade, exaustao, pullback = self._qualidade_movimento(candles)

        vwap = self._calcular_vwap_aproximado(candles)
        desvio, desvio_dir, extremo, mean_rev = self._avaliar_barato_caro(
            preco, vwap, atr, high, low
        )

        # Direcao da decisao macro
        acao = str(getattr(decisao, "action", "HOLD"))
        if hasattr(getattr(decisao, "action", None), "value"):
            acao = decisao.action.value
        direcao = acao if acao in ("BUY", "SELL") else "NEUTRO"

        corr_estado, dolar_fav, sp500_fav, comm_fav, divergencia = \
            self._avaliar_correlacoes(direcao, macro_items, decisao)

        risco_arm, armadilhas = self._identificar_armadilhas(
            fase, posicao, qualidade, exaustao, corr_estado,
            divergencia, range_pts, desvio, atr, candles,
        )

        cenario_mudou, motivo_mudanca = self._detectar_mudanca_cenario(
            guardian_state, macro_items, decisao,
        )

        momento_fav, direcao_pref, confianca_leitura, resumo, ajuste = \
            self._veredicto(
                fase, qualidade, exaustao, pullback, corr_estado,
                divergencia, risco_arm, posicao, mean_rev,
                cenario_mudou, direcao,
            )

        return LeituraOperador(
            timestamp=agora,
            fase_sessao=fase,
            posicao_no_range=posicao,
            range_pts=range_pts,
            range_expandindo=range_expandindo,
            qualidade_movimento=qualidade,
            exaustao_detectada=exaustao,
            pullback_saudavel=pullback,
            desvio_vwap_pts=desvio,
            desvio_vwap_direcao=desvio_dir,
            preco_extremo=extremo,
            potencial_mean_reversion=mean_rev,
            correlacao_estado=corr_estado,
            dolar_favoravel=dolar_fav,
            sp500_favoravel=sp500_fav,
            commodities_favoravel=comm_fav,
            divergencia_critica=divergencia,
            risco_armadilha=risco_arm,
            armadilhas=armadilhas,
            cenario_mudou=cenario_mudou,
            motivo_mudanca=motivo_mudanca,
            momento_favoravel=momento_fav,
            direcao_preferida=direcao_pref,
            confianca_leitura=confianca_leitura,
            resumo=resumo,
            ajuste_confianca=ajuste,
        )
