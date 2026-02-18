"""
Monitor de Triggers - Avisa quando condições mudarem para entrada.

Monitora continuamente:
- Fundamentos (SELIC, EMBI+, USD/BRL)
- Setup técnico (formação clara)
- Volume (confirmação de convicção)
- Alinhamento e Confiança (65%+ - Modelo Day Trade)

Alerta quando triggers ativarem!
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.volume_analysis import VolumeAnalysisService
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


class TriggerMonitor:
    """Monitora triggers e alerta mudanças."""

    def __init__(self):
        self.last_state = {}
        self.alert_count = 0

    def check_triggers(
        self,
        decision,
        volume_variance_pct,
        current_price,
        opening_price,
    ):
        """Verifica triggers e retorna alertas."""

        alerts = []
        current_state = {}

        # Estado atual
        current_state['macro'] = decision.macro_bias
        current_state['fundamental'] = decision.fundamental_bias
        current_state['sentiment'] = decision.sentiment_bias
        current_state['technical'] = decision.technical_bias
        current_state['confidence'] = float(decision.confidence)
        current_state['alignment'] = float(decision.alignment_score)
        current_state['has_entry'] = decision.recommended_entry is not None
        current_state['volume_variance'] = float(volume_variance_pct) if volume_variance_pct else None
        current_state['price_change'] = float(((current_price - opening_price) / opening_price) * 100)

        # TRIGGER 1: Alinhamento >= 65% (Modelo Day Trade)
        if current_state['alignment'] >= 0.65 and self.last_state.get('alignment', 0) < 0.65:
            alerts.append({
                'tipo': 'ALINHAMENTO',
                'nivel': 'CRITICO',
                'mensagem': f"ALINHAMENTO ATINGIU {current_state['alignment']:.0%}!",
                'detalhe': "Sentimento + Tecnica ALINHADOS. Condicao PRINCIPAL atendida!",
            })

        # TRIGGER 2: Confiança >= 65% (Modelo Day Trade)
        if current_state['confidence'] >= 0.65 and self.last_state.get('confidence', 0) < 0.65:
            alerts.append({
                'tipo': 'CONFIANCA',
                'nivel': 'CRITICO',
                'mensagem': f"CONFIANCA ATINGIU {current_state['confidence']:.0%}!",
                'detalhe': "Sistema tem ALTA CONVICCAO na direcao!",
            })

        # TRIGGER 3: Fundamentos mudaram
        if 'fundamental' in self.last_state and current_state['fundamental'] != self.last_state['fundamental']:
            old = self.last_state['fundamental']
            new = current_state['fundamental']
            alerts.append({
                'tipo': 'FUNDAMENTOS',
                'nivel': 'ALTO',
                'mensagem': f"FUNDAMENTOS mudaram: {old} -> {new}",
                'detalhe': f"Possivel mudanca em SELIC, EMBI+ ou USD/BRL",
            })

        # TRIGGER 4: Setup técnico formou
        if current_state['has_entry'] and not self.last_state.get('has_entry', False):
            alerts.append({
                'tipo': 'SETUP_TECNICO',
                'nivel': 'ALTO',
                'mensagem': "SETUP TECNICO FORMOU!",
                'detalhe': f"Ponto de entrada claro: R$ {decision.recommended_entry:.2f}",
            })

        # TRIGGER 5: Volume confirmou (mudou de baixo para alto)
        if volume_variance_pct is not None:
            old_vol = self.last_state.get('volume_variance')
            if old_vol is not None and old_vol < -20 and current_state['volume_variance'] > -20:
                alerts.append({
                    'tipo': 'VOLUME',
                    'nivel': 'MEDIO',
                    'mensagem': f"VOLUME SUBIU para {current_state['volume_variance']:+.1f}%",
                    'detalhe': "Movimento ganhou CONVICCAO!",
                })

        # TRIGGER 6: Macro mudou
        if 'macro' in self.last_state and current_state['macro'] != self.last_state['macro']:
            old = self.last_state['macro']
            new = current_state['macro']
            alerts.append({
                'tipo': 'MACRO',
                'nivel': 'MEDIO',
                'mensagem': f"MACRO mudou: {old} -> {new}",
                'detalhe': "Mudanca em DXY ou VIX",
            })

        # TRIGGER 7: PRONTO PARA OPERAR (condições completas - Modelo Day Trade 65%)
        if current_state['confidence'] >= 0.65 and current_state['alignment'] >= 0.65:
            if self.last_state.get('confidence', 0) < 0.65 or self.last_state.get('alignment', 0) < 0.65:
                alerts.append({
                    'tipo': 'PRONTO_PARA_OPERAR',
                    'nivel': 'CRITICO',
                    'mensagem': ">>> TODAS AS CONDICOES ATENDIDAS <<<",
                    'detalhe': f"Sistema vai ENTRAR {decision.action.value} automaticamente!",
                })

        # Atualizar estado
        self.last_state = current_state

        return alerts, current_state


def main():
    """Monitora triggers continuamente."""

    print("=" * 80)
    print("MONITOR DE TRIGGERS - OPERADOR QUANTICO")
    print("=" * 80)
    print()
    print("Monitorando condicoes para entrada...")
    print("Voce sera ALERTADO quando triggers mudarem!")
    print()
    print("Pressione Ctrl+C para parar")
    print()

    # Setup
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    # Conectar
    print("Conectando ao MT5...")
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar")
        return

    print("[OK] Conectado!")
    print()

    # Inicializar
    operator = QuantumOperatorEngine()
    volume_service = VolumeAnalysisService()
    monitor = TriggerMonitor()

    cycle = 0

    try:
        while True:
            cycle += 1
            now = datetime.now()

            print("-" * 80)
            print(f"Ciclo #{cycle} - {now.strftime('%H:%M:%S')}")
            print("-" * 80)

            # Obter dados
            candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)

            if not candles:
                print("[AVISO] Sem dados, tentando novamente...")
                time.sleep(30)
                continue

            opening_candle = candles[0]
            current_candle = candles[-1]
            opening_price = opening_candle.open.value
            current_price = current_candle.close.value

            # Análise completa
            decision = operator.analyze_and_decide(
                symbol=symbol,
                candles=candles,
                dollar_index=Decimal("104.3"),
                vix=Decimal("16.5"),
                selic=Decimal("10.75"),
                ipca=Decimal("4.5"),
                usd_brl=Decimal("5.85"),
                embi_spread=250,
            )

            # Volume
            volume_today, volume_avg_3days, volume_variance_pct = volume_service.calculate_volume_metrics(candles)

            # Verificar triggers
            alerts, current_state = monitor.check_triggers(
                decision=decision,
                volume_variance_pct=volume_variance_pct,
                current_price=current_price,
                opening_price=opening_price,
            )

            # Status atual
            print(f"Preco:       R$ {current_price:,.2f} ({current_state['price_change']:+.2f}%)")
            print(f"Decisao:     {decision.action.value}")
            print(f"Confianca:   {decision.confidence:.0%} {'[OK]' if decision.confidence >= 0.65 else '[X]'}")
            print(f"Alinhamento: {decision.alignment_score:.0%} {'[OK]' if decision.alignment_score >= 0.65 else '[X]'}")
            print()

            # Mostrar dimensões
            print("Dimensoes:")
            print(f"  Macro:       {decision.macro_bias}")
            print(f"  Fundamentos: {decision.fundamental_bias}")
            print(f"  Sentimento:  {decision.sentiment_bias}")
            print(f"  Tecnica:     {decision.technical_bias}")
            print()

            # Contexto adicional
            print("Contexto:")
            print(f"  Setup tecnico: {'SIM' if decision.recommended_entry else 'NAO'}")
            if volume_variance_pct:
                vol_status = "ALTO" if volume_variance_pct > 20 else "BAIXO" if volume_variance_pct < -20 else "NORMAL"
                print(f"  Volume:        {volume_variance_pct:+.1f}% ({vol_status})")
            print()

            # ALERTAS!
            if alerts:
                print("=" * 80)
                print("!!! ALERTAS DE MUDANCA !!!")
                print("=" * 80)
                print()

                for alert in alerts:
                    nivel = alert['nivel']

                    # Símbolo baseado no nível
                    if nivel == 'CRITICO':
                        simbolo = ">>>"
                        separador = "=" * 60
                    elif nivel == 'ALTO':
                        simbolo = ">>"
                        separador = "-" * 60
                    else:
                        simbolo = ">"
                        separador = "." * 60

                    print(separador)
                    print(f"{simbolo} [{alert['tipo']}] {alert['mensagem']}")
                    print(f"    {alert['detalhe']}")
                    print(separador)
                    print()

                monitor.alert_count += 1

            else:
                print("[OK] Sem mudancas detectadas")

            print()

            # Status resumido de triggers
            print("Status dos Triggers:")
            print(f"  [{'OK' if decision.confidence >= 0.65 else '  '}] Confianca >= 65%")
            print(f"  [{'OK' if decision.alignment_score >= 0.65 else '  '}] Alinhamento >= 65%")
            print(f"  [{'OK' if decision.fundamental_bias == 'BEARISH' else '  '}] Fundamentos bearish (para venda)")
            print(f"  [{'OK' if decision.recommended_entry else '  '}] Setup tecnico formado")

            if volume_variance_pct:
                print(f"  [{'OK' if volume_variance_pct > -20 else '  '}] Volume com conviccao")

            # Se todas condições atendidas
            if decision.confidence >= 0.65 and decision.alignment_score >= 0.65:
                print()
                print("=" * 80)
                print(">>> CONDICOES COMPLETAS - SISTEMA PRONTO PARA OPERAR <<<")
                print("=" * 80)
                print()
                print(f"Acao: {decision.action.value}")
                if decision.recommended_entry:
                    print(f"Entrada sugerida: R$ {decision.recommended_entry:.2f}")
                print()

            print()
            print(f"Proximo check em 30 segundos...")
            print()

            # Aguardar 30 segundos
            time.sleep(30)

    except KeyboardInterrupt:
        print()
        print()
        print("=" * 80)
        print("MONITORAMENTO INTERROMPIDO")
        print("=" * 80)
        print()
        print(f"Total de ciclos:  {cycle}")
        print(f"Total de alertas: {monitor.alert_count}")
        print()
        print("Obrigado por usar o Monitor de Triggers!")
        print()

    finally:
        mt5.disconnect()


if __name__ == "__main__":
    main()
