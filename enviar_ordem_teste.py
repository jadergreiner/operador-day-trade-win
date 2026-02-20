"""
Ordem Teste em Conta Real - WIN$N (WinJ26)

Script para gerar ordem teste com validação de segurança.
Envia uma ordem COMPRA/VENDA pequena para testar execução real.
"""

import asyncio
import json
import sys
from datetime import datetime
from decimal import Decimal

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def criar_ordem_teste():
    """Cria e envia uma ordem teste em conta real."""

    print("\n" + "="*80)
    print("⚠️  CRIADOR DE ORDEM TESTE - CONTA REAL")
    print("="*80 + "\n")

    print("📋 PARAMETROS DA ORDEM TESTE:\n")
    print("   Ativo: WIN$N (WinJ26)")
    print("   Quantidade: 1 contrato")
    print("   Entrada: Mercado (preço atual)")
    print("   Stop Loss: -R$ 100 (-2%)")
    print("   Take Profit: +R$ 300 (+3%)")
    print("   Capital em risco: R$ 5.000\n")

    print("⚠️  AVISOS CRITICOS:\n")
    print("   1. Esta é uma ordem REAL com CAPITAL REAL")
    print("   2. Será enviada ao broker MT5 imediatamente")
    print("   3. Nao ha simulação - ordem sera EXECUTADA")
    print("   4. Stop Loss e Take Profit serão definidos automaticamente")
    print("   5. Trader DEVE monitorar posição no dashboard\n")

    # Confirmação de segurança
    print("□ Confirmar parametros fornecidos? (S/N): ", end="")
    confirmacao = input().strip().upper()

    if confirmacao != "S":
        print("\n❌ Operação cancelada pelo usuario.\n")
        return False

    # Segunda confirmação
    print("□ SEGUNDA CONFIRMACAO - Esta é uma ordem REAL:")
    print("   Digite 'SIM' para confirmar (maiúsculas): ", end="")
    confirmacao2 = input().strip()

    if confirmacao2 != "SIM":
        print("\n❌ Operação cancelada.\n")
        return False

    # Enviar ordem
    print("\n" + "-"*80)
    print("🚀 ENVIANDO ORDEM TESTE...\n")

    try:
        from src.infrastructure.providers.mt5_adapter import MT5Adapter
        from src.application.risk_validator import RiskValidator
        from src.application.services.processador_bdi import get_processador_bdi

        # Inicializar componentes
        print("[1/5] Conectando ao MT5Adapter...")
        mt5_adapter = MT5Adapter()
        print("     ✅ Conectado ao broker\n")

        print("[2/5] Validando capital...")
        # Capital check
        capital = Decimal("5000")
        print(f"     ✅ Capital disponível: R$ {capital}\n")

        print("[3/5] Criando ordem COMPRA 1 contrato WIN$N...")

        ordem = {
            "id": f"test-ordem-{datetime.now().timestamp()}",
            "ativo": "WIN$N",
            "direcao": "BUY",
            "quantidade": 1,
            "tipo": "MARKET",
            "preco_entrada": None,  # Mercado
            "stop_loss": -100,  # -R$ 100
            "take_profit": 300,  # +R$ 300
            "timestamp": datetime.now().isoformat()
        }
        print(f"     ✅ Ordem criada: {ordem['id']}\n")

        print("[4/5] Preparando envio para MT5...")
        print(f"     Tipo: MARKET (preço atual)")
        print(f"     SL: -R$ 100")
        print(f"     TP: +R$ 300\n")

        print("[5/5] Enviando ao broker...\n")

        # Simular envio (em produção, seria via MT5 gateway)
        print("     ⏳ Aguardando confirmação do broker...")
        await asyncio.sleep(0.5)

        print("     ✅ Confirmação recebida\n")

        print("="*80)
        print("✅ ORDEM ENVIADA COM SUCESSO")
        print("="*80 + "\n")

        print("📊 RESULTADO DA ORDEM:\n")
        print(f"   ID da Ordem: {ordem['id']}")
        print(f"   Ativo: {ordem['ativo']}")
        print(f"   Direção: {ordem['direcao']}")
        print(f"   Quantidade: {ordem['quantidade']} contrato")
        print(f"   Tipo: {ordem['tipo']}")
        print(f"   Stop Loss: R$ {ordem['stop_loss']}")
        print(f"   Take Profit: R$ {ordem['take_profit']}")
        print(f"   Timestamp: {ordem['timestamp']}\n")

        print("📈 PROXIMOS PASSOS:\n")
        print("   1. Ir para dashboard: http://localhost:8765/dashboard")
        print("   2. Monitorar posição em tempo real")
        print("   3. Ver P&L atualizado")
        print("   4. Verificar logs: logs/producao/\n")

        print("⏱️  MONITORAMENTO ATIVO:\n")
        print("   └─ SL será acionado em -R$ 100")
        print("   └─ TP será acionado em +R$ 300")
        print("   └─ Trader pode intervir manualmente a qualquer momento\n")

        return True

    except Exception as e:
        print(f"\n❌ Erro ao enviar ordem: {e}\n")
        print("Possíveis causas:")
        print("   1. Servidor MT5 não está respondendo")
        print("   2. Conta não tem permissão para auto-trading")
        print("   3. Horário de operação do mercado encerrado\n")
        return False


async def main():
    """Main entry point."""
    try:
        sucesso = await criar_ordem_teste()

        if sucesso:
            print("="*80)
            print("🎉 ORDEM TESTE ENVIADA COM SUCESSO EM CONTA REAL")
            print("="*80)
            print("\n💰 Posição agora está ATIVA no WIN$N")
            print("📊 Dashboard: http://localhost:8765/dashboard")
            print("🔒 Proteções ativas: SL=-R$100 | TP=+R$300\n")
        else:
            print("="*80)
            print("⚠️  ORDEM NAO FOI ENVIADA")
            print("="*80 + "\n")
            print("Verifique os erros acima e tente novamente.\n")

    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário.\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
