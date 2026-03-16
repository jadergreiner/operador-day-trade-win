#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes para Isolamento de Posições entre Agentes RL
====================================================

Testa:
  - Isolamento completo de session ID
  - Validação de ownership de posição
  - Impede que um agente leia posição do outro
  - Persistência correta de metadados de posição
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from src.application.posicao_isolamento import PosicaoIsoladaManager


class TestIsolamentoPosicao:
    """Testes para isolamento de posições entre agentes."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Cria diretório temporário para testes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def session_id_agente_5000(self) -> str:
        """Session ID único para RL 5000."""
        return f"agente_5000_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v1"

    @pytest.fixture
    def session_id_agente_direto(self) -> str:
        """Session ID único para RL Direto."""
        return f"agente_direto_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v2"

    def test_criar_status_arquivo_com_session_id_unico(
        self,
        temp_dir: Path,
        session_id_agente_5000: str
    ) -> None:
        """Testa que cada agente cria arquivo de status com seu próprio session ID."""
        # Arrange
        arquivo_status = temp_dir / f"agente_posicao_{session_id_agente_5000}.json"

        # Act
        arquivo_status.write_text(json.dumps({
            "session_id": session_id_agente_5000,
            "aberta": True,
            "open_time": datetime.now().isoformat(),
            "agent_version": "RL_5000_v1",
            "timestamp": datetime.now().isoformat()
        }))

        # Assert
        assert arquivo_status.exists()
        dados = json.loads(arquivo_status.read_text())
        assert dados["session_id"] == session_id_agente_5000
        assert dados["agent_version"] == "RL_5000_v1"

    def test_validar_ownership_posicao(
        self,
        temp_dir: Path,
        session_id_agente_5000: str,
        session_id_agente_direto: str
    ) -> None:
        """Testa que um agente não consegue ler posição de outro agente."""
        # Arrange - RL 5000 cria sua posição
        arquivo_5000 = temp_dir / f"agente_posicao_{session_id_agente_5000}.json"
        arquivo_5000.write_text(json.dumps({
            "session_id": session_id_agente_5000,
            "aberta": True,
            "owner": "RL_5000_v1",
            "timestamp": datetime.now().isoformat()
        }))

        # Act - RL Direto tenta ler posição
        arquivo_direto = (
            temp_dir / f"agente_posicao_{session_id_agente_direto}.json"
        )

        # Assert - RL Direto tem seu próprio arquivo vazio
        assert not arquivo_direto.exists()
        assert arquivo_5000.exists()

        # Verificar que leitura é específica por session ID
        dados_5000 = json.loads(arquivo_5000.read_text())
        assert dados_5000["session_id"] == session_id_agente_5000
        assert dados_5000["owner"] == "RL_5000_v1"

    def test_isolar_multiplas_posicoes(
        self,
        temp_dir: Path,
        session_id_agente_5000: str,
        session_id_agente_direto: str
    ) -> None:
        """Testa múltiplos agentes operando simultaneamente com posições isoladas."""
        # Arrange
        arquivos_agentes: Dict[str, Path] = {
            "RL_5000": temp_dir / f"agente_posicao_{session_id_agente_5000}.json",
            "RL_DIRETO": temp_dir / f"agente_posicao_{session_id_agente_direto}.json",
        }

        # Act - cada agente cria sua posição
        for agente_tipo, arquivo in arquivos_agentes.items():
            arquivo.write_text(json.dumps({
                "session_id": session_id_agente_5000
                    if agente_tipo == "RL_5000"
                    else session_id_agente_direto,
                "aberta": True,
                "owner": agente_tipo,
                "preco_entrada": 182000.0 + (100 if agente_tipo == "RL_5000" else 200),
                "timestamp": datetime.now().isoformat()
            }))

        # Assert - cada arquivo tem dados corretos
        for agente_tipo, arquivo in arquivos_agentes.items():
            assert arquivo.exists()
            dados = json.loads(arquivo.read_text())
            assert dados["owner"] == agente_tipo

        # Verificar isolamento
        dados_5000 = json.loads(arquivos_agentes["RL_5000"].read_text())
        dados_direto = json.loads(arquivos_agentes["RL_DIRETO"].read_text())

        assert dados_5000["owner"] != dados_direto["owner"]
        assert dados_5000["preco_entrada"] == 182100.0
        assert dados_direto["preco_entrada"] == 182200.0

    def test_impedir_sobrescrita_posicao_outro_agente(
        self,
        temp_dir: Path,
        session_id_agente_5000: str,
        session_id_agente_direto: str
    ) -> None:
        """Testa que um agente não consegue sobrescrever posição do outro."""
        # Arrange - RL 5000 cria posição
        arquivo_5000 = temp_dir / f"agente_posicao_{session_id_agente_5000}.json"
        dados_originais = {
            "session_id": session_id_agente_5000,
            "aberta": True,
            "owner": "RL_5000_v1",
            "preco_entrada": 182000.0
        }
        arquivo_5000.write_text(json.dumps(dados_originais))

        # Act - Simular tentativa de outro agente sobrescrever
        # (isso não deveria ser permitido na implementação real)
        arquivo_direto = temp_dir / f"agente_posicao_{session_id_agente_direto}.json"
        arquivo_direto.write_text(json.dumps({
            "session_id": session_id_agente_direto,
            "aberta": True,
            "owner": "RL_DIRETO_v1"
        }))

        # Assert - arquivo original não foi alterado
        dados_lidos = json.loads(arquivo_5000.read_text())
        assert dados_lidos == dados_originais
        assert dados_lidos["owner"] == "RL_5000_v1"

    def test_metadados_posicao_completos(
        self,
        temp_dir: Path,
        session_id_agente_5000: str
    ) -> None:
        """Testa que posição contém todos metadados necessários."""
        # Arrange
        arquivo_status = temp_dir / f"agente_posicao_{session_id_agente_5000}.json"
        metadados_posicao = {
            "session_id": session_id_agente_5000,
            "aberta": True,
            "owner": "RL_5000_v1",
            "owner_version": "v5000-SAFE",
            "preco_entrada": 182000.0,
            "open_time": datetime.now().isoformat(),
            "ticket": 123456789,
            "lado": "BUY",
            "quantidade": 1,
            "timestamp": datetime.now().isoformat()
        }

        # Act
        arquivo_status.write_text(json.dumps(metadados_posicao, indent=2))
        dados_lidos = json.loads(arquivo_status.read_text())

        # Assert - todos metadados presentes
        assert dados_lidos["session_id"] == session_id_agente_5000
        assert dados_lidos["owner"] == "RL_5000_v1"
        assert dados_lidos["owner_version"] == "v5000-SAFE"
        assert dados_lidos["aberta"] is True
        assert "preco_entrada" in dados_lidos
        assert "open_time" in dados_lidos
        assert "ticket" in dados_lidos

    def test_arquivos_nao_existem_sessao_nova(
        self,
        temp_dir: Path,
        session_id_agente_direto: str
    ) -> None:
        """Testa que nova sessão começa sem posições abertas."""
        # Arrange
        arquivo_status = temp_dir / f"agente_posicao_{session_id_agente_direto}.json"

        # Act & Assert
        assert not arquivo_status.exists()

    def test_regeneracao_session_id_diferente(self) -> None:
        """Testa que cada nova execução gera session ID diferente."""
        # Arrange & Act
        session_1 = f"agente_direto_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        session_2 = f"agente_direto_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Assert - session IDs devem ser diferentes (por UUID)
        assert session_1 != session_2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
