"""
Script de exemplo para uso do Ambiente Gym de Trading.

Demonstra como usar a Trilha RL Operacional (P2) para:
- Inicializar ambiente
- Registrar episodios
- Salvar/carregar checkpoints
- Gerar relatorios
"""

from src.application.rl_trading_environment import TradingGymEnvironment


def exemplo_ambiente_basico() -> None:
    """Exemplo basico de uso do ambiente."""
    print("=" * 60)
    print("Exemplo: Ambiente Gym Basico")
    print("=" * 60)

    # Criar ambiente
    env = TradingGymEnvironment(
        capital_inicial=10000.0,
        alavancagem=2.0,
    )

    # Executar alguns episodios
    for episodio in range(1, 4):
        print(f"\n Episodio {episodio}")
        estado = env.reset()
        print(f" Estado inicial: {estado}")

        # Simular 3 passos
        for step in range(3):
            action = step % 4  # Rotacionar acoes
            estado, reward, done, info = env.step(action)
            print(f"  Step {step}: action={action}, reward={reward:.2f}")

        # Registrar episodio
        env.registrar_episodio(
            episodio=episodio,
            trades=episodio * 5,
            win_rate=0.60 + (episodio * 0.02),
            total_pnl=500.0 + (episodio * 100),
        )

    # Mostrar metricas
    metricas = env.calcular_metricas()
    print(f"\nMetricas Consolidadas:")
    print(f" Total Reward: R$ {metricas.total_reward:.2f}")
    print(f" Win Rate Medio: {metricas.win_rate*100:.2f}%")
    print(f" Sharpe Ratio: {metricas.sharpe_ratio:.2f}")
    print(f" Max Drawdown: {metricas.max_drawdown*100:.2f}%")
    print(f" Trades Executados: {metricas.trades_executados}")


def exemplo_checkpoint() -> None:
    """Exemplo de salvar e carregar checkpoint."""
    print("\n" + "=" * 60)
    print("Exemplo: Checkpoint")
    print("=" * 60)

    env = TradingGymEnvironment(
        capital_inicial=10000.0,
        alavancagem=2.0,
    )

    # Registrar alguns episodios e salvar
    for i in range(3):
        env.reset()
        env.registrar_episodio(
            episodio=i + 1,
            trades=5,
            win_rate=0.60,
            total_pnl=500.0,
        )

    # Salvar checkpoint
    arquivo = env.salvar_checkpoint(
        versao="v1.0.0",
        melhor_reward=1500.0,
    )
    print(f"Checkpoint salvo: {arquivo}")

    # Carregar checkpoint
    dados = env.carregar_checkpoint(arquivo)
    print(f"Checkpoint carregado:")
    print(f" Versao: {dados['versao']}")
    print(f" Melhor Reward: {dados['melhor_reward']}")
    print(f" Episodios Totais: {dados['episodios_totais']}")


def exemplo_relatorio() -> None:
    """Exemplo de gerar relatorio."""
    print("\n" + "=" * 60)
    print("Exemplo: Relatorio Markdown")
    print("=" * 60)

    env = TradingGymEnvironment(
        capital_inicial=10000.0,
        alavancagem=2.0,
    )

    # Registrar episodios
    for i in range(5):
        env.reset()
        env.registrar_episodio(
            episodio=i + 1,
            trades=5 + i,
            win_rate=0.55 + (i * 0.02),
            total_pnl=400.0 + (i * 150),
        )

    # Gerar relatorio
    relatorio = env.gerar_relatorio_markdown()
    print(relatorio)


if __name__ == "__main__":
    exemplo_ambiente_basico()
    exemplo_checkpoint()
    exemplo_relatorio()

    print("\n" + "=" * 60)
    print("Exemplos Concluidos!")
    print("=" * 60)
