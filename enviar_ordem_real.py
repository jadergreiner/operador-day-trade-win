"""
Enviar Ordem Real ao Broker MT5 - Conta 1000346516

Conecta ao gateway MT5 e envia ordem REAL no WIN$N
"""

import asyncio
import json
import logging
import httpx
from datetime import datetime
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def enviar_ordem_real():
    """Envia ordem real ao broker via gateway MT5."""
    
    print("\n" + "="*80)
    print("🚀 ENVIAR ORDEM REAL AO BROKER MT5")
    print("="*80 + "\n")
    
    print("📋 PARAMETROS DA ORDEM:\n")
    print("   Conta: 1000346516")
    print("   Ativo: WIN$N")
    print("   Contrato: WinJ26")
    print("   Quantidade: 1 lote")
    print("   Tipo: BUY (Compra)")
    print("   Take Profit: 300 pontos")
    print("   Stop Loss: 100 pontos\n")
    
    print("⚠️  AVISO: Esta é uma ordem REAL com CAPITAL REAL\n")
    print("   Confirmar envio ao broker? (S/N): ", end="")
    
    confirmacao = input().strip().upper()
    if confirmacao != "S":
        print("\n❌ Cancelado.\n")
        return False
    
    try:
        print("\n" + "-"*80)
        print("📡 CONECTANDO AO GATEWAY MT5...\n")
        
        # Conectar ao gateway MT5 (localhost:8000)
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            print("[1/3] Verificando conexão com broker...")
            try:
                health = await client.get("http://localhost:8000/health")
                if health.status_code == 200:
                    print("      ✅ Broker respondendo\n")
                else:
                    print(f"      ⚠️  Status {health.status_code}\n")
            except Exception as e:
                print(f"      ⚠️  Broker não está respondendo: {e}")
                print("      Continuando com envio mesmo assim...\n")
            
            print("[2/3] Preparando dados da ordem...")
            
            payload = {
                "account": 1000346516,
                "symbol": "WIN$N",
                "contract": "WinJ26",
                "action": "ORDER_TYPE_BUY",
                "volume": 1,
                "type": "ORDER_TYPE_BUY_LIMIT",
                "price": 0.0,  # Mercado
                "tp": 300,      # Take Profit
                "sl": 100,      # Stop Loss
                "comment": "Ordem teste - enviar_ordem_real.py",
                "magic": 20260220,
                "deviation": 10
            }
            
            print(f"      ✅ Payload preparado: {json.dumps(payload, indent=2)}\n")
            
            print("[3/3] Enviando ordem ao broker...\n")
            
            # Enviar ordem via POST
            try:
                response = await client.post(
                    "http://localhost:8000/api/v1/orders",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"      Status HTTP: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    resultado = response.json()
                    print(f"      ✅ Ordem enviada com sucesso!\n")
                    print(f"      Resposta do broker:")
                    print(f"      {json.dumps(resultado, indent=2)}\n")
                    
                    return True
                else:
                    print(f"      ⚠️  Resposta inesperada: {response.text}\n")
                    return False
                    
            except Exception as e:
                print(f"      ⚠️  Erro ao enviar: {e}\n")
                print("      Possíveis causas:")
                print("         - Gateway MT5 não está rodando (localhost:8000)")
                print("         - Erro de conexão com broker")
                print("         - Parâmetros da conta inválidos\n")
                return False
    
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}\n")
        return False


async def verificar_ordens():
    """Verifica ordens na conta."""
    
    print("\n" + "-"*80)
    print("📊 VERIFICANDO ORDENS NA CONTA...\n")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # Buscar ordens
            response = await client.get(
                "http://localhost:8000/api/v1/orders",
                params={"account": 1000346516}
            )
            
            if response.status_code == 200:
                ordens = response.json()
                print(f"Ordens encontradas: {len(ordens)}\n")
                
                for ordem in ordens:
                    print(f"ID: {ordem.get('ticket')}")
                    print(f"   Símbolo: {ordem.get('symbol')}")
                    print(f"   Tipo: {ordem.get('type')}")
                    print(f"   Volume: {ordem.get('volume')}")
                    print(f"   Preço: {ordem.get('price')}")
                    print(f"   Status: {ordem.get('state')}\n")
            else:
                print(f"Erro ao buscar ordens: {response.status_code}\n")
    
    except Exception as e:
        print(f"Erro: {e}\n")


async def main():
    """Main entry point."""
    
    try:
        resultado = await enviar_ordem_real()
        
        if resultado:
            print("="*80)
            print("✅ ORDEM ENVIADA AO BROKER")
            print("="*80)
            print("\n💡 Próximas ações:")
            print("   1. Verifique a ordem na plataforma MT5")
            print("   2. Acompanhe no dashboard: http://localhost:8765/dashboard")
            print("   3. Monitore o P&L em tempo real\n")
            
            # Verificar ordens
            await verificar_ordens()
        else:
            print("\n⚠️  Ordem não foi enviada. Verifique os erros acima.\n")
    
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado pelo usuário.\n")


if __name__ == "__main__":
    asyncio.run(main())
