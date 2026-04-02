"""Testes de integração do pipeline P1-LEARNING no encerramento de sessão.

Valida o acoplamento do fluxo Etapas 5-7 ao shutdown do
`agente_rl_direto_independente.py`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts.agente_rl_direto_independente import _encerrar_sessao_learning
from src.application.p1_learning_closure import EpisodeClosureEngine, MotivoFechamento


def _popular_fechamentos_para_sessao(db_path: Path) -> None:
    """Cria fechamentos suficientes para acionar L1, L2 e geração de regras."""
    engine = EpisodeClosureEngine(db_path=str(db_path))

    cenarios = [
        ("EP_001", 128000.0, 127500.0, -500.0, -1.0, MotivoFechamento.SL_ATINGIDO),
        ("EP_002", 128100.0, 127600.0, -500.0, -1.0, MotivoFechamento.SL_ATINGIDO),
        ("EP_003", 127900.0, 128300.0, 400.0, 0.8, MotivoFechamento.TP_ATINGIDO),
        ("EP_004", 128200.0, 127800.0, -400.0, -0.9, MotivoFechamento.TIMEOUT),
        ("EP_005", 128050.0, 128040.0, -10.0, -0.01, MotivoFechamento.FECHAMENTO_MANUAL),
    ]

    for episode_id, entrada, saida, pnl, pnl_pct, motivo in cenarios:
        engine.registrar_fechamento(
            episode_id=episode_id,
            trade_id=f"TRD_{episode_id}",
            preco_entrada=entrada,
            preco_saida=saida,
            pnl_realizado=pnl,
            pnl_realizado_pct=pnl_pct,
            motivo_fechamento=motivo,
            duracao_total_segundos=300.0,
            market_conditions={"volatilidade": "baixa", "tendencia": "UP"},
            timestamp_fechamento=datetime(2026, 4, 2, 17, 0, 0),
        )


def test_encerrar_sessao_learning_gera_artefatos_em_data_models_e_outputs(
    tmp_path: Path,
) -> None:
    """Deve salvar modelos em `data/models` e relatório em `outputs/`."""
    db_path = tmp_path / "causal_learning.db"
    outputs_dir = tmp_path / "outputs"
    models_dir = tmp_path / "data" / "models"
    _popular_fechamentos_para_sessao(db_path)

    _encerrar_sessao_learning(
        sessao_id="SESSAO_TESTE_P1",
        db_path=db_path,
        output_dir=outputs_dir,
        models_output_dir=models_dir,
        timeout_segundos=5,
    )

    arquivos_l1 = list(models_dir.glob("l1_analysis_*.jsonl"))
    arquivos_regras = list(models_dir.glob("learning_rules_*.json"))
    arquivos_relatorio = list(outputs_dir.glob("p1_learning_report_*.md"))

    assert len(arquivos_l1) == 1
    assert len(arquivos_regras) == 1
    assert len(arquivos_relatorio) == 1

    linha = arquivos_l1[0].read_text(encoding="utf-8").splitlines()[0]
    payload_l1 = json.loads(linha)
    assert "corretude_decisao" in payload_l1
    assert payload_l1["sessao_id"] == "SESSAO_TESTE_P1"

    payload_regras = json.loads(arquivos_regras[0].read_text(encoding="utf-8"))
    assert payload_regras["sessao_id"] == "SESSAO_TESTE_P1"
    assert "regras" in payload_regras


def test_encerrar_sessao_learning_nao_quebra_shutdown_se_relatorio_falhar(
    tmp_path: Path,
) -> None:
    """Falha no relatório não deve interromper a geração dos artefatos base."""
    db_path = tmp_path / "causal_learning.db"
    outputs_dir = tmp_path / "outputs"
    models_dir = tmp_path / "data" / "models"
    _popular_fechamentos_para_sessao(db_path)

    with patch(
        "src.application.p1_learning_relatorio.RelatorioSessao.gerar_relatorio_md",
        side_effect=RuntimeError("falha simulada no markdown"),
    ):
        _encerrar_sessao_learning(
            sessao_id="SESSAO_TESTE_FALHA",
            db_path=db_path,
            output_dir=outputs_dir,
            models_output_dir=models_dir,
            timeout_segundos=5,
        )

    assert list(models_dir.glob("l1_analysis_*.jsonl"))
    assert list(models_dir.glob("learning_rules_*.json"))
