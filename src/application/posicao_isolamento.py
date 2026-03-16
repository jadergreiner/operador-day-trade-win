#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Isolamento de Posições entre Agentes RL
========================================

Implementa isolamento completo de posições (RL 5000 vs RL Direto):
  - Session ID único por agente
  - Validação de ownership de posição
  - Impede leitura/sobrescrita de posição de outro agente
  - Metadados completos de rastreamento

Uso:
    from src.application.posicao_isolamento import PosicaoIsoladaManager

    manager = PosicaoIsoladaManager(
        session_id="agente_direto_20260316_123354",
        agent_version="DIRETO_v2",
        outputs_dir=Path("outputs")
    )

    # Registrar posição
    manager.registrar_posicao_aberta(
        preco_entrada=182000.0,
        ticket=123456,
        lado="BUY",
        quantidade=1
    )

    # Verificar se posição pertence a este agente
    if manager.eh_dono_posicao():
        print("Posição deste agente")

    # Fechar posição
    manager.registrar_posicao_fechada()
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple


logger = logging.getLogger(__name__)


class PosicaoIsoladaManager:
    """
    Gerenciador de posições com isolamento total entre agentes.

    Características:
    - Arquivo JSON por session ID (isolado)
    - Validação de ownership (impede leitura de outro agente)
    - Metadados completos de rastreamento
    - Type hints 100%
    - Documentação em português
    """

    def __init__(
        self,
        session_id: str,
        agent_version: str,
        outputs_dir: Path
    ) -> None:
        """
        Inicializa gerenciador de posição isolada.

        Args:
            session_id: Session ID único do agente (ex: "agente_direto_20260316_123354")
            agent_version: Versão do agente (ex: "DIRETO_v2", "RL_5000_v1")
            outputs_dir: Diretório para armazenar arquivo de status
        """
        self.session_id: str = session_id
        self.agent_version: str = agent_version
        self.outputs_dir: Path = Path(outputs_dir)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        # Arquivo específico para este agente
        self.status_arquivo: Path = (
            self.outputs_dir / f"agente_posicao_{session_id}.json"
        )

        # Estado em memória
        self.posicao_aberta: bool = False
        self.metadados_posicao: Dict[str, Any] = {}

        # Carregar status anterior (se existir)
        self._carregar_status()

        logger.debug(
            f"[ISOLAMENTO] PosicaoIsoladaManager inicializado: "
            f"session_id={session_id}, version={agent_version}"
        )

    def _carregar_status(self) -> None:
        """Carrega status de posição anterior se arquivo existir."""
        try:
            if self.status_arquivo.exists():
                with open(self.status_arquivo, 'r', encoding='utf-8') as f:
                    dados = json.load(f)

                    # Validar que posição foi criada DESTE agente
                    if not self._validar_ownership(dados):
                        logger.warning(
                            f"[ISOLAMENTO] Arquivo de posição foi criado por outro "
                            f"agente ({dados.get('owner')}) - ignorando"
                        )
                        self.posicao_aberta = False
                        self.metadados_posicao = {}
                        return

                    self.posicao_aberta = dados.get("aberta", False)
                    self.metadados_posicao = dados

                    if self.posicao_aberta:
                        logger.info(
                            f"[ISOLAMENTO] Posição aberta detectada para session "
                            f"{self.session_id} (criada em "
                            f"{dados.get('open_time')})"
                        )
                    else:
                        logger.debug(
                            f"[ISOLAMENTO] Nenhuma posição aberta para "
                            f"session {self.session_id}"
                        )
            else:
                logger.debug(
                    f"[ISOLAMENTO] Primeiro acesso para session "
                    f"{self.session_id} - arquivo não existe"
                )
                self.posicao_aberta = False
                self.metadados_posicao = {}

        except json.JSONDecodeError as e:
            logger.error(
                f"[ISOLAMENTO] Erro ao desserializar JSON de posição: {e}"
            )
            self.posicao_aberta = False
            self.metadados_posicao = {}

        except Exception as e:
            logger.error(
                f"[ISOLAMENTO] Erro ao carregar status de posição: {e}"
            )
            self.posicao_aberta = False
            self.metadados_posicao = {}

    def _validar_ownership(self, dados: Dict[str, Any]) -> bool:
        """
        Valida que a posição foi criada por ESTE agente.

        Args:
            dados: Dados do arquivo de posição

        Returns:
            True se a posição pertence a este agente, False caso contrário
        """
        owner_esperado = self.agent_version

        # Se arquivo não tem owner, deixar para compatibilidade com versões antigas
        if "owner" not in dados:
            logger.warning(
                f"[ISOLAMENTO] Arquivo não tem campo 'owner' - "
                f"possível arquivo antigo"
            )
            return False

        owner_arquivo = dados.get("owner")

        # Se owner é diferente, isto é um erro crítico de isolamento
        if owner_arquivo != owner_esperado:
            logger.error(
                f"[ISOLAMENTO] ❌ VIOLAÇÃO DE ISOLAMENTO DETECTADA! "
                f"Tentativa de ler posição de outro agente: "
                f"esperado={owner_esperado}, arquivo={owner_arquivo}"
            )
            return False

        return True

    def _salvar_status(self) -> None:
        """Salva status de posição no arquivo JSON."""
        try:
            with open(self.status_arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.metadados_posicao, f, indent=2, ensure_ascii=False)

            logger.debug(
                f"[ISOLAMENTO] Status de posição salvo: {self.status_arquivo}"
            )

        except Exception as e:
            logger.error(
                f"[ISOLAMENTO] Erro ao salvar status de posição: {e}"
            )
            raise

    def registrar_posicao_aberta(
        self,
        preco_entrada: float,
        ticket: int,
        lado: str,
        quantidade: int
    ) -> None:
        """
        Registra que uma posição foi aberta POR ESTE AGENTE.

        Args:
            preco_entrada: Preço de entrada da posição
            ticket: ID da ordem no MT5
            lado: "BUY" ou "SELL"
            quantidade: Quantidade de contratos
        """
        self.posicao_aberta = True

        self.metadados_posicao = {
            "session_id": self.session_id,
            "owner": self.agent_version,
            "owner_version": self.agent_version,
            "aberta": True,
            "preco_entrada": preco_entrada,
            "open_time": datetime.now().isoformat(),
            "ticket": ticket,
            "lado": lado,
            "quantidade": quantidade,
            "timestamp": datetime.now().isoformat(),
        }

        self._salvar_status()

        logger.info(
            f"[ISOLAMENTO] ✅ Posição aberta registrada para agente "
            f"{self.agent_version}:\n"
            f"  - Session: {self.session_id}\n"
            f"  - Ticket: {ticket}\n"
            f"  - Tipo: {lado}\n"
            f"  - Preço: R$ {preco_entrada:.2f}\n"
            f"  - Arquivo: {self.status_arquivo.name}"
        )

    def registrar_posicao_fechada(self) -> None:
        """Registra que a posição foi fechada POR ESTE AGENTE."""
        self.posicao_aberta = False

        self.metadados_posicao = {
            "session_id": self.session_id,
            "owner": self.agent_version,
            "aberta": False,
            "open_time": self.metadados_posicao.get("open_time"),
            "close_time": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

        self._salvar_status()

        logger.info(
            f"[ISOLAMENTO] Posição fechada registrada para agente "
            f"{self.agent_version} (session {self.session_id})"
        )

    def tem_posicao_aberta(self) -> bool:
        """
        Verifica se ESTE AGENTE tem uma posição aberta.

        Returns:
            True se agente tem posição aberta, False caso contrário
        """
        return self.posicao_aberta

    def eh_dono_posicao(self) -> bool:
        """
        Verifica se este agente é o dono da posição atual.

        Returns:
            True se posição pertence a este agente, False caso contrário
        """
        if not self.posicao_aberta:
            return False

        owner = self.metadados_posicao.get("owner")
        return owner == self.agent_version

    def obter_metadados_posicao(self) -> Dict[str, Any]:
        """
        Obtém metadados completos da posição.

        Returns:
            Dicionário com metadados (session_id, owner, ticket, etc)

        Raises:
            ValueError se posição não pertence a este agente
        """
        if not self.eh_dono_posicao():
            raise ValueError(
                f"Posição não pertence a este agente "
                f"(owner: {self.metadados_posicao.get('owner')})"
            )

        return self.metadados_posicao.copy()

    def obter_infos_resumidas(self) -> Tuple[bool, str]:
        """
        Obtém informações resumidas sobre status de posição.

        Returns:
            Tupla (tem_posicao_aberta, resumo_texto)
        """
        if not self.posicao_aberta:
            return False, f"Sem posição aberta (session: {self.session_id})"

        if not self.eh_dono_posicao():
            owner = self.metadados_posicao.get("owner", "desconhecido")
            return False, (
                f"⚠️  Posição pertence a outro agente ({owner}), "
                f"não será operada"
            )

        preco = self.metadados_posicao.get("preco_entrada", "N/A")
        ticket = self.metadados_posicao.get("ticket", "N/A")
        lado = self.metadados_posicao.get("lado", "N/A")

        resumo = (
            f"✅ Posição aberta (agente: {self.agent_version}): "
            f"{lado} @ R$ {preco} (ticket: {ticket})"
        )

        return True, resumo

    def validar_integridade(self) -> bool:
        """
        Valida integridade do isolamento de posição.

        Verifica:
        - Arquivo existe se posição aberta
        - Owner está correto
        - Session ID está correto

        Returns:
            True se tudo OK, False se problemas detectados
        """
        if not self.posicao_aberta:
            return True

        # Arquivo deve existir
        if not self.status_arquivo.exists():
            logger.error(
                f"[VALIDAÇÃO] ❌ Arquivo de posição não existe: "
                f"{self.status_arquivo}"
            )
            return False

        # Carregar arquivo e validar
        try:
            with open(self.status_arquivo, 'r', encoding='utf-8') as f:
                dados_arquivo = json.load(f)

            # Validar owner
            if dados_arquivo.get("owner") != self.agent_version:
                logger.error(
                    f"[VALIDAÇÃO] ❌ Owner no arquivo é diferente do agente"
                )
                return False

            # Validar session ID
            if dados_arquivo.get("session_id") != self.session_id:
                logger.error(
                    f"[VALIDAÇÃO] ❌ Session ID no arquivo é diferente"
                )
                return False

            logger.info("[VALIDAÇÃO] ✅ Integridade de isolamento OK")
            return True

        except Exception as e:
            logger.error(f"[VALIDAÇÃO] ❌ Erro ao validar integridade: {e}")
            return False
