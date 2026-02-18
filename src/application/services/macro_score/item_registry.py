"""Registro de todos os itens do macro score."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from src.domain.enums.macro_score_enums import (
    AssetCategory,
    CorrelationType,
    ForexConvention,
    ScoringType,
)


@dataclass(frozen=True)
class MacroScoreItemConfig:
    """Configuracao de um item do macro score."""

    number: int
    symbol: str
    name: str
    category: AssetCategory
    correlation: CorrelationType
    weight: Decimal
    is_futures: bool
    forex_convention: Optional[ForexConvention]
    scoring_type: ScoringType
    indicator_config: Optional[dict]


def _item(
    number: int,
    symbol: str,
    name: str,
    category: AssetCategory,
    correlation: CorrelationType,
    is_futures: bool = False,
    forex_convention: Optional[ForexConvention] = None,
    scoring_type: ScoringType = ScoringType.PRICE_VS_OPEN,
    indicator_config: Optional[dict] = None,
    weight: Decimal = Decimal("1.0"),
) -> MacroScoreItemConfig:
    """Helper para criar item com peso configuravel.

    Pesos adaptativos (implementado 12/02/2026):
      2.0 = Core drivers (IBOV, WDO, WSP, PETR4, VALE3, DI1F, VXBR)
      1.5 = Importantes (bancos, DI vertices, safe havens, flow)
      1.0 = Padrao
      0.5 = Baixa relevancia (forex exotico, agro nicho)
    """
    return MacroScoreItemConfig(
        number=number,
        symbol=symbol,
        name=name,
        category=category,
        correlation=correlation,
        weight=weight,
        is_futures=is_futures,
        forex_convention=forex_convention,
        scoring_type=scoring_type,
        indicator_config=indicator_config,
    )


D = CorrelationType.DIRETA
I = CorrelationType.INVERSA
XXX = ForexConvention.XXX_USD
USD = ForexConvention.USD_XXX


def get_item_registry() -> list[MacroScoreItemConfig]:
    """Retorna registro completo de todos os itens do macro score.

    Inclui:
        1-20:  Indices Brasil (DIRETA)
        21-36: Acoes Brasil (DIRETA)
        37-39: Dolar/Cambio (INVERSA)
        40-51: Forex (DIRETA risco, INVERSA safe havens)
        52-64: Commodities (misto)
        65-67: Juros/Renda Fixa legado (INVERSA)
        68-71: Criptomoedas (DIRETA)
        72-75: Indices Globais (DIRETA)
        76-77: Volatilidade (INVERSA) + HASH11
        78-85: Indicadores Tecnicos Intraday
        86-91: Curva de Juros DI (INVERSA) — vertices + spread
        92-95: Risco Pais (INVERSA) — CDS, cupom cambial, EWZ
        96-98: Petroleo/Energia direto (DIRETA)
        99-101: Emergentes — ETFs peers (DIRETA)
        102-106: Fluxo e Microestrutura — delta, imbalance, book
    """

    items: list[MacroScoreItemConfig] = []

    # ==========================================
    # INDICES BRASIL (1-20) - Correlacao DIRETA
    # ==========================================
    IB = AssetCategory.INDICES_BRASIL
    items.extend([
        _item(1, "BOVA11", "Indice Bovespa (ETF)", IB, D, weight=Decimal("2.0")),
        _item(2, "SMLL", "Small Caps", IB, D, weight=Decimal("1.5")),
        _item(3, "MLCX", "MidLarge Cap", IB, D, weight=Decimal("1.5")),
        _item(4, "INDX", "Setor Industrial", IB, D),
        _item(5, "IMOB", "Imobiliario", IB, D),
        _item(6, "IMAT", "Materiais Basicos", IB, D),
        _item(7, "IGNM", "Governanca Novo Mercado", IB, D),
        _item(8, "AGFS", "Agronegocio", IB, D, weight=Decimal("0.5")),
        _item(9, "BDRX", "BDRs", IB, D),
        _item(10, "IBOV", "Indice Bovespa", IB, D, weight=Decimal("2.0")),
        _item(11, "IBXL", "IBrX-50 Large Cap", IB, D),
        _item(12, "IBXX", "IBrX-100", IB, D),
        _item(13, "ICO2", "Carbono Eficiente", IB, D, weight=Decimal("0.5")),
        _item(14, "ICON", "Consumo", IB, D),
        _item(15, "IDIV", "Dividendos", IB, D),
        _item(16, "IEEX", "Energia Eletrica", IB, D),
        _item(17, "IFIX", "Fundos Imobiliarios", IB, D),
        _item(18, "IFNC", "Financeiro", IB, D, weight=Decimal("1.5")),
        _item(19, "ISEE", "Sustentabilidade", IB, D, weight=Decimal("0.5")),
        _item(20, "UTIL", "Utilidade Publica", IB, D),
    ])

    # ==========================================
    # ACOES BRASIL (21-36) - Correlacao DIRETA
    # ==========================================
    AB = AssetCategory.ACOES_BRASIL
    items.extend([
        _item(21, "PETR4", "Petrobras PN", AB, D, weight=Decimal("2.0")),
        _item(22, "VALE3", "Vale ON", AB, D, weight=Decimal("2.0")),
        _item(23, "ITUB3", "Itau Unibanco ON", AB, D, weight=Decimal("1.5")),
        _item(24, "ABEV3", "Ambev", AB, D),
        _item(25, "B3SA3", "B3", AB, D),
        _item(26, "BBDC3", "Bradesco", AB, D, weight=Decimal("1.5")),
        _item(27, "DIVO11", "ETF Dividendos", AB, D),
        _item(28, "CXSE3", "Caixa Seguridade", AB, D),
        _item(29, "EGIE3", "Engie Brasil", AB, D),
        _item(30, "EQPA3", "Equatorial", AB, D),
        _item(31, "MRVE3", "MRV Engenharia", AB, D),
        _item(32, "BBAS3", "Banco do Brasil", AB, D, weight=Decimal("1.5")),
        _item(33, "SANB3", "Santander Brasil", AB, D),
        _item(34, "SAPR4", "Sanepar", AB, D),
        _item(35, "VIVT3", "Vivo Telefonica", AB, D),
        _item(36, "WEGE3", "WEG", AB, D),
    ])

    # ==========================================
    # DOLAR / CAMBIO (37-39) - Correlacao INVERSA
    # ==========================================
    DC = AssetCategory.DOLAR_CAMBIO
    items.extend([
        _item(37, "WDO", "Mini Dolar", DC, I, is_futures=True, weight=Decimal("2.0")),
        _item(39, "DOL", "Dolar Cheio", DC, I, is_futures=True, weight=Decimal("1.5")),
    ])

    # ==========================================
    # FOREX (40-51) - Futuros de moedas B3
    # ==========================================
    FX = AssetCategory.FOREX
    # Moedas - resolver via ForexScoreHandler (nao sao futuros B3)
    items.extend([
        _item(40, "EUR", "Euro", FX, D),
        _item(41, "GBP", "Libra Esterlina", FX, D),
        _item(42, "AUD", "Dolar Australiano", FX, D),
        _item(43, "NZD", "Dolar Neozelandes", FX, D),
        _item(44, "CAD", "Dolar Canadense", FX, D),
        _item(45, "CNY", "Yuan Chines", FX, D),
        _item(46, "MXN", "Peso Mexicano", FX, D, weight=Decimal("0.5")),
        _item(47, "ZAR", "Rand Sul-Africano", FX, D, weight=Decimal("0.5")),
        _item(48, "TRY", "Lira Turca", FX, D, weight=Decimal("0.5")),
        _item(49, "CLP", "Peso Chileno", FX, D, weight=Decimal("0.5")),
    ])
    # Safe havens - correlacao INVERSA (moeda forte = risk-off = ruim para WIN)
    items.extend([
        _item(50, "CHF", "Franco Suico", FX, I, weight=Decimal("1.5")),
        _item(51, "JPY", "Iene Japones", FX, I, weight=Decimal("1.5")),
    ])

    # ==========================================
    # COMMODITIES (52-64)
    # ==========================================
    CM = AssetCategory.COMMODITIES
    # Ouro - INVERSA
    items.extend([
        _item(52, "GLDG", "Ouro Global", CM, I, is_futures=True, weight=Decimal("1.5")),
    ])
    # Agro/Commodities Brasil - DIRETA, futuros
    items.extend([
        _item(54, "IFBOI", "Boi Gordo (Indice)", CM, D),
        _item(55, "IFMILHO", "Milho (Indice)", CM, D),
        _item(56, "CCM", "Milho B3", CM, D, is_futures=True, weight=Decimal("0.5")),
        _item(57, "ICF", "Cafe Arabica", CM, D, is_futures=True, weight=Decimal("0.5")),
        _item(58, "SJC", "Soja", CM, D, is_futures=True, weight=Decimal("0.5")),
    ])
    # Agro - futuros B3
    items.extend([
        _item(59, "BGI", "Boi Gordo Indice", CM, D, is_futures=True, weight=Decimal("0.5")),
        _item(60, "DAP", "Fosfato Fertilizante", CM, D, is_futures=True, weight=Decimal("0.5")),
    ])
    # Commodities - proxies disponiveis na B3
    items.extend([
        _item(61, "PETR3", "Petrobras ON", CM, D),
        _item(62, "PRIO3", "PetroRio", CM, D),
        _item(63, "CSNA3", "CSN Mineracao", CM, D),
        _item(64, "USIM5", "Usiminas", CM, D),
    ])

    # ==========================================
    # JUROS / RENDA FIXA (65-67) - Correlacao INVERSA
    # ==========================================
    JR = AssetCategory.JUROS_RENDA_FIXA
    items.extend([
        _item(65, "DI", "DI Futuro", JR, I, is_futures=True, weight=Decimal("1.5")),
        _item(66, "T10", "US Treasury 10Y", JR, I, is_futures=True, weight=Decimal("1.5")),
        _item(67, "TSLC", "Tesouro Selic", JR, I),
    ])

    # ==========================================
    # CRIPTOMOEDAS (68-71) - Correlacao DIRETA
    # ==========================================
    CR = AssetCategory.CRIPTOMOEDAS
    items.extend([
        _item(68, "BIT", "Bitcoin", CR, D, is_futures=True),
        _item(69, "ETH", "Ethereum", CR, D, is_futures=True),
        _item(70, "SOL", "Solana", CR, D, is_futures=True),
        _item(71, "ETR", "Ethereum variante", CR, D, is_futures=True),
    ])

    # ==========================================
    # INDICES GLOBAIS (72-75) - Correlacao DIRETA
    # ==========================================
    IG = AssetCategory.INDICES_GLOBAIS
    items.extend([
        _item(72, "WSP", "S&P 500 Futuro", IG, D, is_futures=True, weight=Decimal("2.0")),
        _item(73, "NASD11", "ETF Nasdaq", IG, D, weight=Decimal("1.5")),
        _item(74, "IVVB11", "ETF S&P 500", IG, D, weight=Decimal("1.5")),
        _item(75, "HSI", "Hang Seng China", IG, D, is_futures=True),
    ])

    # ==========================================
    # VOLATILIDADE (76-77) - Correlacao INVERSA
    # ==========================================
    VL = AssetCategory.VOLATILIDADE
    items.extend([
        _item(76, "VXBR", "VIX Brasil", VL, I, weight=Decimal("2.0")),
        _item(77, "HASH11", "ETF Cripto Index", CR, D),
    ])

    # ==========================================
    # INDICADORES TECNICOS INTRADAY (78-85)
    # ==========================================
    IT = AssetCategory.INDICADORES_TECNICOS
    TI = ScoringType.TECHNICAL_INDICATOR
    items.extend([
        _item(78, "VOL", "Volume Financeiro", IT, D, scoring_type=TI,
              indicator_config={"type": "volume"}),
        _item(79, "AGR", "Saldo Agressao", IT, D, scoring_type=TI,
              indicator_config={"type": "aggression"}),
        _item(80, "RSI", "IFR RSI 14", IT, D, scoring_type=TI,
              indicator_config={"type": "rsi", "period": 14, "overbought": 70, "oversold": 30}),
        _item(81, "STOCH", "Estocastico", IT, D, scoring_type=TI,
              indicator_config={"type": "stochastic", "period": 14, "overbought": 80, "oversold": 20}),
        _item(82, "ADX", "ADX Direcional", IT, D, scoring_type=TI,
              indicator_config={"type": "adx", "period": 14, "threshold": 25}),
        _item(83, "VWAP", "VWAP", IT, D, scoring_type=TI,
              indicator_config={"type": "vwap"}),
        _item(84, "MACD", "MACD", IT, D, scoring_type=TI,
              indicator_config={"type": "macd", "fast": 12, "slow": 26, "signal": 9}),
        _item(85, "OBV", "On Balance Volume", IT, D, scoring_type=TI,
              indicator_config={"type": "obv"}),
    ])

    # ==========================================
    # CURVA DE JUROS DI (86-91) - Correlacao INVERSA
    # Juros subindo = WIN caindo. Estrutura a termo da curva
    # permite antecipar ciclo de politica monetaria.
    # ==========================================
    CJ = AssetCategory.CURVA_JUROS
    items.extend([
        _item(86, "DI1F", "DI Futuro vertice curto (Jan prox)", CJ, I, is_futures=True, weight=Decimal("2.0")),
        _item(87, "DI1N", "DI Futuro vertice medio (Jul prox)", CJ, I, is_futures=True, weight=Decimal("1.5")),
        _item(88, "DI1J", "DI Futuro vertice intermediario (Abr prox)", CJ, I, is_futures=True),
        _item(89, "DI1F27", "DI Futuro Jan/2027 (vertice longo)", CJ, I, is_futures=True),
        _item(90, "DI1F29", "DI Futuro Jan/2029 (vertice muito longo)", CJ, I, is_futures=True),
        # Spread da curva: inclinacao curto vs longo. Inversao = recessao.
        _item(91, "DI_SPREAD", "Spread DI Curto vs Longo", CJ, I,
              scoring_type=ScoringType.SPREAD_CURVE,
              indicator_config={"type": "di_spread",
                                "short_vertex": "DI1H",
                                "long_vertex": "DI1F29"},
              weight=Decimal("1.5")),
    ])

    # ==========================================
    # RISCO PAIS (92-95) - Correlacao INVERSA
    # Aumento de risco-pais = fuga de capital = bearish WIN
    # ==========================================
    RP = AssetCategory.RISCO_PAIS
    items.extend([
        # Cupom cambial (DDI/FRC) - diferenca entre juros em dolar no BR vs US
        # Abertura do cupom = estresse cambial = bearish forte
        _item(92, "DDI", "Cupom Cambial DDI Futuro", RP, I, is_futures=True, weight=Decimal("1.5")),
        # BEWZ39 - BDR do EWZ na B3. Proxy de fluxo gringo
        _item(93, "BEWZ39", "BDR iShares Brazil ETF", RP, D, weight=Decimal("1.5")),
        # IMAB11 - ETF IMA-B disponivel na B3 (proxy NTN-B)
        _item(94, "FIXX11", "ETF Renda Fixa Credito Priv", RP, I),
        # FIXA11 - ETF de renda fixa prefixada
        _item(95, "KDIF11", "ETF Infra Debentures", RP, I),
    ])

    # ==========================================
    # PETROLEO / ENERGIA (96-98) - Correlacao DIRETA
    # Petroleo direto (nao proxy via PETR4) para antecipar
    # movimento. Petroleo move ~12% do IBOV via Petrobras.
    # ==========================================
    PE = AssetCategory.PETROLEO_ENERGIA
    items.extend([
        # Petroleo via BDRs/ETFs disponiveis na B3
        _item(96, "PETR4", "Petrobras PN (proxy petroleo)", PE, D),
        _item(97, "PRIO3", "PetroRio (proxy petroleo)", PE, D),
        _item(98, "RECV3", "PetroReconcavo", PE, D),
    ])

    # ==========================================
    # EMERGENTES (99-101) - Correlacao DIRETA
    # Quando fluxo sai de emergentes, sai de todos.
    # Peer comparison essencial para contexto.
    # ==========================================
    EM = AssetCategory.EMERGENTES
    items.extend([
        # Proxies de emergentes disponiveis na B3 como BDRs
        _item(99, "BEEM39", "BDR iShares Emerging Markets", EM, D),
        # HSI futuro B3 - proxy China
        _item(100, "HSI", "Hang Seng China Futuro", EM, D, is_futures=True),
        # Indices globais via ETF B3 como proxy LatAm
        _item(101, "ACWI11", "ETF MSCI All Country World", EM, D),
    ])

    # ==========================================
    # FLUXO E MICROESTRUTURA (102-106)
    # Indicadores de flow e book para micro tendencias.
    # Exigem dados de times & trades do MT5.
    # ==========================================
    FM = AssetCategory.FLUXO_MICROESTRUTURA
    FI = ScoringType.FLOW_INDICATOR
    items.extend([
        # Delta acumulado: diferenca entre volume comprador e vendedor a mercado
        _item(102, "DELTA", "Delta Acumulado (buyer-initiated)", FM, D,
              scoring_type=FI,
              indicator_config={"type": "cumulative_delta"},
              weight=Decimal("1.5")),
        # Imbalance ratio: proporcao compra/venda no book (L1)
        _item(103, "IMBAL", "Book Imbalance Ratio", FM, D,
              scoring_type=FI,
              indicator_config={"type": "book_imbalance", "levels": 1},
              weight=Decimal("1.5")),
        # Speed of tape: velocidade de execucao (trades/segundo)
        _item(104, "SPEED", "Speed of Tape (trades/s)", FM, D,
              scoring_type=FI,
              indicator_config={"type": "tape_speed", "window_seconds": 30}),
        # VWAP deviation: distancia percentual do preco ao VWAP
        _item(105, "VWAPD", "VWAP Deviation %", FM, D,
              scoring_type=FI,
              indicator_config={"type": "vwap_deviation"}),
        # Large trades: contagem de trades grandes (>50 contratos)
        _item(106, "BIGTD", "Large Trades Detector", FM, D,
              scoring_type=FI,
              indicator_config={"type": "large_trades", "min_size": 50}),
    ])

    return items
