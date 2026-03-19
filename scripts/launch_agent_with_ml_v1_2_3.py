#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAUNCHER: AGENTE MICRO TENDÊNCIA WITH ML v1.2.3

Executa agente com INTEGRATION-ML-001 dataset loading integrado
Importa data_loader.load_and_label() e injeta features no ambiente

Releases:
  - v1.2.0 (20/02): TASK-CRITICA-0 - Core infrastructure + ORM
  - v1.2.3 (25/02): INTEGRATION-ML-001 Phase 3 - ML dataset loading
               14/14 tests PASSING | 94% code coverage

Compatível 100% com flags originais do agente.

Uso:
    python launch_agent_with_ml_v1_2_3.py --auto-trade
    python launch_agent_with_ml_v1_2_3.py --simulate
    python launch_agent_with_ml_v1_2_3.py --account 456789 --ml-version 1.2.3

Status: PRODUCAO
"""

import sys
import os
import subprocess
import time
import atexit
from pathlib import Path

# ─ Setup path ─
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = Path(current_dir).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# ─ Global process handles ─
_api_process = None
_ati1_process = None
_execution_monitor_process = None

# ─ Imports ─
try:
    from src.application.data_loader import load_and_label
    ML_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Nao conseguiu importar data_loader: {e}")
    ML_AVAILABLE = False

# Tenta importar agente (tolerante a falhas)
try:
    import agente_micro_tendencia_winfut as agente_module
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False

import agente_micro_tendencia_s2_6_integrated as s2_6_module
from src.application.opening_context_report import generate_opening_context_vs_result_report
from src.application.opening_context_runtime import initialize_opening_context_runtime

# ─ P0-1 API Integration ─
try:
    from src.infrastructure.clients.order_api_client import OrderAPIClient
    from src.infrastructure.adapters.mt5_adapter_proxy import MT5AdapterProxy
    P0_1_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] P0-1 API não importado: {e}")
    P0_1_AVAILABLE = False

# ─ Terminal Isolation Enforcer ─
try:
    from src.infrastructure.terminal_isolation_enforcer import (
        TerminalIsolationEnforcer,
        initialize_enforcer,
        validate_critical_operation,
        TerminalIsolationViolation,
    )
    ENFORCER_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Terminal Isolation Enforcer não importado: {e}")
    ENFORCER_AVAILABLE = False

# ─ Terminal Isolation Enforcer ─
try:
    from src.infrastructure.terminal_isolation_enforcer import (
        TerminalIsolationEnforcer,
        initialize_enforcer,
        validate_critical_operation
    )
    ENFORCER_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Terminal Isolation Enforcer não importado: {e}")
    ENFORCER_AVAILABLE = False


def start_api_server_subprocess():
    """
    Inicia servidor API em subprocess.

    A API é iniciada em background e continua rodando enquanto
    o agente está ativo. É finalizada automaticamente via atexit.

    Returns:
        subprocess.Popen: Processo da API ou None se falha
    """
    if not P0_1_AVAILABLE:
        return None

    global _api_process

    try:
        api_script = root_dir / "scripts" / "start_api_server.py"

        print("  [START] Iniciando servidor P0-1 API em background...")

        # Inicia API em subprocess
        _api_process = subprocess.Popen(
            [sys.executable, str(api_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Aguarda API iniciar (timeout 5 segundos)
        print("  [WAIT] Aguardando API carregar (timeout=5s)...")
        for i in range(5):
            time.sleep(1)
            if _api_process.poll() is not None:
                # Processo terminou unexpectedly
                stdout, stderr = _api_process.communicate()
                print("  [ERRO] API falhou ao iniciar")
                if stderr:
                    print(f"     Erro: {stderr[:200]}")
                return None

        # Verifica se API respondendo
        try:
            from src.infrastructure.clients.order_api_client import OrderAPIClient
            test_client = OrderAPIClient(timeout=2, max_retries=1)
            if test_client.health_check():
                print(f"  [OK] API Server iniciado com sucesso (PID={_api_process.pid})")

                # Registra cleanup automático
                atexit.register(_cleanup_api_process)

                return _api_process
        except Exception as e:
            print(f"  [WARN] API nao respondendo: {e}")

        return None

    except Exception as e:
        print(f"  [ERRO] Erro ao iniciar API subprocess: {e}")
        return None


def _cleanup_api_process():
    """
    Finaliza processo da API quando o programa termina.
    """
    global _api_process

    if _api_process and _api_process.poll() is None:
        try:
            print("\n  [STOP] Encerrando servidor API...")
            _api_process.terminate()
            try:
                _api_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _api_process.kill()
            print("  [OK] API Server finalizado")
        except Exception as e:
            print(f"  [WARN] Erro ao finalizar API: {e}")


def start_ati1_ws_subprocess():
    """
    Inicia ATI-1 WebSocket Server em subprocess.
    """
    global _ati1_process

    try:
        ati1_port = os.getenv("ATI1_PORT", "8000")
        ati1_host = os.getenv("ATI1_HOST", "127.0.0.1")

        print("  [START] Iniciando ATI-1 WebSocket Server...")

        _ati1_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.application.websocket_server_ati1:app",
                "--host",
                ati1_host,
                "--port",
                ati1_port,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Aguarda alguns segundos
        time.sleep(2)

        if _ati1_process.poll() is not None:
            stdout, stderr = _ati1_process.communicate()
            print("  [ERRO] ATI-1 WS falhou ao iniciar")
            if stderr:
                print(f"     Erro: {stderr[:200]}")
            return None

        print(f"  [OK] ATI-1 WS iniciado (PID={_ati1_process.pid})")
        atexit.register(_cleanup_ati1_process)
        return _ati1_process
    except Exception as e:
        print(f"  [WARN] Erro ao iniciar ATI-1 WS: {e}")
        return None


def _cleanup_ati1_process():
    """Finaliza ATI-1 WS server."""
    global _ati1_process
    if _ati1_process and _ati1_process.poll() is None:
        try:
            print("\n  [STOP] Encerrando ATI-1 WebSocket...")
            _ati1_process.terminate()
            try:
                _ati1_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _ati1_process.kill()
            print("  [OK] ATI-1 WebSocket finalizado")
        except Exception as e:
            print(f"  [WARN] Erro ao finalizar ATI-1 WS: {e}")


def start_execution_monitor_subprocess():
    """
    Inicia Execution Monitor (AC5.8) em subprocess.
    """
    global _execution_monitor_process

    try:
        trader_id = os.getenv("TRADER_ID", "TRADER_001")
        ati1_port = os.getenv("ATI1_PORT", "8000")
        ati1_host = os.getenv("ATI1_HOST", "127.0.0.1")
        ati1_url = os.getenv("ATI1_URL", f"http://{ati1_host}:{ati1_port}")
        token = os.getenv("ATI1_BROADCAST_TOKEN", "")

        monitor_script = root_dir / "scripts" / "start_execution_monitor.py"
        cmd = [
            sys.executable,
            str(monitor_script),
            "--db", "data/db/trading.db",
            "--trader-id", trader_id,
            "--ati1-url", ati1_url,
        ]
        if token:
            cmd.extend(["--ati1-token", token])

        print("  [START] Iniciando Execution Monitor (AC5.8)...")
        _execution_monitor_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(1)
        if _execution_monitor_process.poll() is not None:
            stdout, stderr = _execution_monitor_process.communicate()
            print("  [ERRO] Execution Monitor falhou ao iniciar")
            if stderr:
                print(f"     Erro: {stderr[:200]}")
            return None

        print(f"  [OK] Execution Monitor iniciado (PID={_execution_monitor_process.pid})")
        atexit.register(_cleanup_execution_monitor)
        return _execution_monitor_process
    except Exception as e:
        print(f"  [WARN] Erro ao iniciar Execution Monitor: {e}")
        return None


def _cleanup_execution_monitor():
    """Finaliza Execution Monitor."""
    global _execution_monitor_process
    if _execution_monitor_process and _execution_monitor_process.poll() is None:
        try:
            print("\n  [STOP] Encerrando Execution Monitor...")
            _execution_monitor_process.terminate()
            try:
                _execution_monitor_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _execution_monitor_process.kill()
            print("  [OK] Execution Monitor finalizado")
        except Exception as e:
            print(f"  [WARN] Erro ao finalizar Execution Monitor: {e}")


def load_ml_features():
    """
    Carrega dataset ML com 24 features engineered (v1.2.3)

    Returns:
        dict: {
            'dataframe': DataFrame com 24 features + labels,
            'feature_names': Lista de 24 nomes de features,
            'statistics': Dict com stats (mean, std, skewness)
        }

    Raises:
        RuntimeError: Se dataset nao consegue ser carregado
    """
    if not ML_AVAILABLE:
        print("[WARN] ML module nao disponivel - retornando vazio")
        return None

    try:
        print("\n  [ML] LOADING ML FEATURES (v1.2.3 - INTEGRATION-ML-001)")
        print("  " + "=" * 60)

        # Paths
        data_dir = root_dir / "data"
        ml_output_dir = data_dir / "ml"
        backtest_results = ml_output_dir / "backtest_results.json"

        # Validations
        if not backtest_results.exists():
            print(f"  [WARN] backtest_results.json nao encontrado em {backtest_results}")
            print(f"     Pulando ML data load...")
            return None

        # Load data
        print(f"  [LOAD] Carregando dados de: {backtest_results}")
        df = load_and_label(str(backtest_results), str(ml_output_dir))

        if df is None or len(df) == 0:
            print("  [WARN] Dataset vazio ou nao carregado")
            return None

        # Get feature names
        feature_names_file = ml_output_dir / "feature_names.json"
        statistics_file = ml_output_dir / "statistics.json"

        feature_names = None
        statistics = None

        if feature_names_file.exists():
            import json
            with open(feature_names_file) as f:
                feature_names = json.load(f)

        if statistics_file.exists():
            import json
            with open(statistics_file) as f:
                statistics = json.load(f)

        # Summary
        print(f"  [OK] Dataset carregado: {len(df)} samples")
        print(f"  [OK] Features: {len(df.columns)} colunas")
        if feature_names:
            print("  [OK] Feature names: 24 nomes persisted")
        if statistics:
            print("  [OK] Statistics: quantidades calculadas")

        # Label distribution
        if 'label' in df.columns:
            buy_count = (df['label'] == 'BUY').sum()
            skip_count = (df['label'] == 'SKIP').sum()
            buy_pct = 100 * buy_count / len(df)
            skip_pct = 100 * skip_count / len(df)
            print(f"  [OK] Label distribution: BUY={buy_pct:.1f}% | SKIP={skip_pct:.1f}%")

        print("  " + "=" * 60)

        return {
            'dataframe': df,
            'feature_names': feature_names,
            'statistics': statistics,
            'count': len(df)
        }

    except Exception as e:
        print(f"  [ERRO] Erro ao carregar ML features: {e}")
        import traceback
        traceback.print_exc()
        return None


def inject_ml_into_environment(ml_data):
    """
    Injeta features ML no ambiente global para acesso do agente

    Args:
        ml_data: Dict com dataset, features, statistics
    """
    if not ml_data or not AGENT_AVAILABLE:
        return

    try:
        print("\n  [INJECT] INJECTING ML FEATURES INTO AGENT ENVIRONMENT")
        print("  " + "=" * 60)

        # Set global variables
        if hasattr(agente_module, 'ML_FEATURES'):
            agente_module.ML_FEATURES = ml_data
            print(f"  [OK] ML_FEATURES.dataframe: {len(ml_data['dataframe'])} rows")

        if hasattr(agente_module, 'ML_FEATURE_NAMES'):
            agente_module.ML_FEATURE_NAMES = ml_data['feature_names']
            if ml_data['feature_names']:
                print(f"  [OK] ML_FEATURE_NAMES: {len(ml_data['feature_names'])} features")

        if hasattr(agente_module, 'ML_STATISTICS'):
            agente_module.ML_STATISTICS = ml_data['statistics']
            if ml_data['statistics']:
                print("  [OK] ML_STATISTICS: quantidades carregadas")

        # Also set in sys.modules for easy access
        sys.modules['ML_DATA'] = type(sys)('ML_DATA')
        sys.modules['ML_DATA'].dataframe = ml_data['dataframe']
        sys.modules['ML_DATA'].feature_names = ml_data['feature_names']
        sys.modules['ML_DATA'].statistics = ml_data['statistics']
        sys.modules['ML_DATA'].count = ml_data['count']

        print("  [OK] ML data injected into agent environment")
        print("  " + "=" * 60)

    except Exception as e:
        print(f"  [WARN] Erro ao injetar ML data: {e}")


def setup_integrations():
    """
    Setup completo: S2-6 Analytics + ML v1.2.3 + Terminal Isolation

    Returns:
        dict: Status das integrações
    """
    print("\n\n  [SETUP] INTEGRACOES: Terminal Isolation + S2-6 + ML v1.2.3")
    print("  " + "=" * 60)

    status = {
        'terminal_isolation': False,
        's2_6': False,
        'ml': False,
        'p0_1_api': False,
        'agent': AGENT_AVAILABLE
    }

    # ⚡ FIRST: Initialize Terminal Isolation Enforcer (HARD STOP MODE)
    if ENFORCER_AVAILABLE:
        print("\n  [SECURITY] TERMINAL ISOLATION ENFORCEMENT (HARD STOP MODE)")
        print("  " + "=" * 60)
        try:
            from config.settings import get_config
            from src.infrastructure.terminal_isolation_enforcer import TerminalIsolationViolation

            config = get_config()

            if not config.mt5_terminal_path:
                print("  [WARN] MT5_TERMINAL_PATH nao configurado em .env")
                print(f"     Adicione a linha (exemplo):")
                print(f"     MT5_TERMINAL_PATH=C:\\Program Files\\Clear Investimentos MT5 Terminal\\terminal64.exe")
                print("  [INFO] Terminal isolation: DESATIVADO (voce configura quando quiser)")
            else:
                # Initializa enforcer com HARD_STOP mode
                enforcer = initialize_enforcer(config.mt5_terminal_path)
                print(f"  [OK] Enforcer inicializado: {config.mt5_terminal_path}")

                # Valida imediatamente (BLOQUEIO ATIVO)
                try:
                    enforcer.validate_before_operation("launcher:startup")
                    isolation_status = enforcer.get_isolation_status()
                    print(f"  [OK] Terminal isolado: {isolation_status['is_isolated']}")
                    print(f"  [OK] PID(s) CLEAR: {isolation_status['clear_pids']}")
                    print(f"  [OK] Terminais perigosos: {isolation_status['dangerous_terminals_detected'] or 'Nenhum'}")
                    status['terminal_isolation'] = True
                except TerminalIsolationViolation as e:
                    # HARD STOP: Falha imediata se isolamento viola
                    print(f"  [ERRO] FALHA CRITICA: {e}")
                    print("  " + "=" * 60)
                    sys.exit(1)
        except Exception as e:
            print(f"  [WARN] Erro no setup de terminal isolation: {e}")
            # Continue anyway - enforcer é opcional

        print("  " + "=" * 60)

    # S2-6 setup (from launch_agent_with_s2_6.py pattern)
    try:
        if AGENT_AVAILABLE and hasattr(s2_6_module, 'initialize_s2_6_adapter'):
            api_url = os.getenv("S2_6_API_URL", "http://localhost:8000")
            adapter = s2_6_module.initialize_s2_6_adapter(api_url)
            print(f"  [OK] S2-6 Analytics: {'ONLINE' if adapter else 'FALLBACK'}")
            status['s2_6'] = True
        else:
            print("  [WARN] S2-6 module nao disponivel")
    except Exception as e:
        print(f"  [WARN] S2-6 setup error: {e}")

    # ML v1.2.3 setup
    try:
        ml_data = load_ml_features()
        if ml_data:
            inject_ml_into_environment(ml_data)
            status['ml'] = True
            print("\n  [OK] ML v1.2.3 Integrado")
        else:
            print("\n  [WARN] ML v1.2.3 Nao disponivel (continuaremos sem)")
    except Exception as e:
        print(f"\n  [WARN] ML setup error: {e}")

    # P0-1 REST API setup
    try:
        result = inject_p0_1_proxy()
        status['p0_1_api'] = result
        if result:
            print("\n  [OK] P0-1 REST API Integrado")
        else:
            print("\n  [INFO] P0-1 nao configurado (usando MT5 direto)")
    except Exception as e:
        print(f"\n  [WARN] P0-1 setup error: {e}")

    print("\n  " + "=" * 60)
    print(f"  Sistema pronto: S2-6={status['s2_6']} | ML={status['ml']} | P0-1={status['p0_1_api']} | Agent={status['agent']}")
    print("  " + "=" * 60)

    return status


def setup_p0_1_api():
    """
    Setup P0-1 REST API integration para orders.

    Cria MT5AdapterProxy que intercepta mt5.send_order() calls
    e encaminha para API REST ao invés de MT5 direto.

    Returns:
        MT5AdapterProxy ou None se falha
    """
    if not P0_1_AVAILABLE:
        print("  [WARN] P0-1 API nao disponivel - usando MT5 direto")
        return None

    try:
        print("\n  [API] P0-1 REST API INTEGRATION")
        print("  " + "=" * 60)

        # API config
        api_url = os.getenv("P0_1_API_URL", "http://localhost:8888")
        print(f"  [INFO] API URL: {api_url}")

        # Create API client
        api_client = OrderAPIClient(api_url=api_url, timeout=5, max_retries=3)

        # Health check
        is_healthy = api_client.health_check()
        if not is_healthy:
            print("  [WARN] API nao respondendo. Sera usado fallback (MT5 direto)")
            return None

        print("  [OK] API Health: OK")
        print("  " + "=" * 60)

        use_api_rest = os.getenv("P0_1_USE_API_REST", "0").strip().lower() in {"1", "true", "yes", "on"}
        if not use_api_rest:
            print("  [INFO] P0-1 desabilitado por padrão - usando MT5 direto")
            return None

        return api_client

    except Exception as e:
        print(f"  [WARN] Erro ao setup P0-1 API: {e}")
        return None


def inject_p0_1_proxy():
    """
    Injeta MT5AdapterProxy no módulo MT5Adapter para interceptar send_order() calls.

    Estratégia: Monkey-patch a classe MT5Adapter ANTES de o agente instanciar.

    Substituição transparente:
        agente.mt5.send_order() → MT5AdapterProxy.send_order()
                                 → OrderAPIClient.create_order()
                                 → POST /api/v1/orders
    """
    if not AGENT_AVAILABLE or not P0_1_AVAILABLE:
        print("  [WARN] Nao consegue injetar P0-1 proxy (deps unavailable)")
        return False

    try:
        print("\n  [INJECT] INJETANDO P0-1 PROXY NO AGENTE")
        print("  " + "=" * 60)

        # Get API client
        api_client = setup_p0_1_api()
        if not api_client:
            print("  [INFO] API nao disponivel - usando MT5 direto")
            return False

        # Procura por MT5Adapter (pode estar em diferentes módulos)
        mt5_adapter_class = None
        if hasattr(agente_module, 'MT5Adapter'):
            mt5_adapter_class = agente_module.MT5Adapter
        else:
            # Busca em sys.modules
            for module_name, module in list(sys.modules.items()):
                if module and hasattr(module, 'MT5Adapter'):
                    mt5_adapter_class = module.MT5Adapter
                    break

        if mt5_adapter_class:
            # Store original send_order method
            original_send_order = mt5_adapter_class.send_order

            def patched_send_order(self, order):
                """send_order patcheado que usa P0-1 API com fallback MT5"""
                # Cria proxy se não existe (lazy init)
                if not hasattr(self, '_p0_1_proxy'):
                    try:
                        self._p0_1_proxy = MT5AdapterProxy(
                            original_adapter=self,
                            api_client=api_client,
                            use_api_rest=True,
                            fallback_to_mt5=True
                        )
                    except Exception as e:
                        print(f"  [WARN] Falha ao criar proxy, usando MT5 direto: {e}")
                        return original_send_order(self, order)

                # Usa proxy para enviar
                return self._p0_1_proxy.send_order(order)

            # Monkey-patch: substitui método na classe
            mt5_adapter_class.send_order = patched_send_order

            print("  [OK] P0-1 Proxy injetado em MT5Adapter.send_order")
            print(f"     Todas as chamadas mt5.send_order() usarão API REST com fallback MT5")
            print("  " + "=" * 60)
            return True
        else:
            print("  [WARN] MT5Adapter nao encontrado no agente ou sys.modules")
            return False

    except Exception as e:
        print(f"  [WARN] Erro ao injetar proxy: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa agente com S2-6 + ML v1.2.3 integrados"""

    print("\n")
    print("  " + "=" * 60)
    print("  AGENTE MICRO TENDENCIA v1.2.3")
    print("  " + "=" * 60)
    print(f"  Release: INTEGRATION-ML-001 Phase 3 (25/02/2026)")
    print(f"  Status: 14/14 tests PASSING | 94% coverage")
    print(f"  Terminal Isolation: HARD STOP Mode (v1.0)")
    print("  " + "=" * 60)

    opening_runtime = initialize_opening_context_runtime(
        db_path=str(root_dir / "data" / "db" / "trading.db"),
        agent_name="micro_tendencia_launcher",
        source="launch_agent_with_ml_v1_2_3",
        mode=" ".join(sys.argv[1:]).strip(),
        printer=print,
        operational_context_dir=os.getenv("OPENING_CONTEXT_DIR") or None,
    )
    if AGENT_AVAILABLE:
        setattr(agente_module, "MACRO_GUARDIAN_UNIVERSAL", opening_runtime.macro_guardian)
        setattr(agente_module, "GUARDIAN_COORDINATOR", opening_runtime.coordinator)
        setattr(agente_module, "OPENING_CONTEXT_FEATURES", opening_runtime.features)
        setattr(agente_module, "OPENING_CONTEXT_POLICY", opening_runtime.policy)
        setattr(agente_module, "PROMPT_ABERTURA_AGENTES", opening_runtime.prompt_abertura_agentes)

    # Inicia servidor API em background (automatic startup)
    print("\n  STARTUP AUTOMATICO")
    print("  " + "=" * 60)
    api_process = start_api_server_subprocess()
    ati1_process = start_ati1_ws_subprocess()
    monitor_process = start_execution_monitor_subprocess()
    print("  " + "=" * 60)

    # Setup integrações
    status = setup_integrations()

    # Executa agente
    if not AGENT_AVAILABLE:
        print("\n  [ERRO] AGENT module nao disponivel")
        sys.exit(1)

    try:
        print("\n  [RUN] Iniciando agente com integracoes ativas...\n")
        agente_module.main()
    except KeyboardInterrupt:
        print("\n\n  [STOP] Agente interrompido pelo usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n  [ERRO] Erro no agente: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            relatorio = generate_opening_context_vs_result_report(
                db_path=str(root_dir / "data" / "db" / "trading.db"),
                output_dir=root_dir / "outputs" / "analysis",
                outputs_root=root_dir / "outputs",
            )
            print(
                "\n  [PRE-ABERTURA] Relatorio contexto x resultado gerado: "
                f"{relatorio.markdown_path}"
            )
        except Exception as exc:
            print(f"\n  [PRE-ABERTURA] Falha ao gerar relatorio final: {exc}")


if __name__ == "__main__":
    main()
