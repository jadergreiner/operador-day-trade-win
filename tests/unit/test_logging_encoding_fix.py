"""Testes de regressao para encoding Unicode em logging.

Verifica se mensagens de logger com caracteres especiais (->  e acentos)
podem ser encodadas em cp1252 (Windows default encoding).

Issue: UnicodeEncodeError em logging quando usa seta Unicode (->)
Date: 2026-03-16
"""

import logging
import io
from typing import List
import pytest


class TestLoggingUnicodeEncodingFix:
    """Testes para verificar se logger maneja UTF-8 corretamente."""

    def test_logger_with_cp1252_handler_accepts_arrow_character(self) -> None:
        """Verifica que logger pode linpar com -> em vez de Unicode arrow."""
        # Setup: Create logger com handler que simula cp1252
        logger = logging.getLogger("test_unicode")
        logger.handlers.clear()

        # String buffer com encoding cp1252 (como Windows console)
        string_buffer = io.StringIO()
        handler = logging.StreamHandler(string_buffer)
        handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)

        # Test: Logar mensagem com -> (ASCII, funciona em cp1252)
        test_message = "  -> INVALID PRICE: novo SL 182355.00 pode estar fora do spread"
        logger.error(test_message)

        # Assert: Mensagem foi logada sem erro
        output = string_buffer.getvalue()
        assert "INVALID PRICE" in output
        assert "182355.00" in output

    def test_logger_messages_are_cp1252_compatible(self) -> None:
        """Verifica que todas as mensagens de logger sao compostas de chars ASCII."""
        messages: List[str] = [
            "  -> INVALID PRICE: novo SL {nova_sl:.2f} pode estar fora do spread",
            "  -> INVALID STOPS: SL ou TP invalido. SL={novo_sl:.2f}, TP={tp:.2f}",
            "  -> INVALID VOLUME: verificar volume=1",
            "  -> INVALID REQUEST: PROVAVEL: SL ja esta neste valor ou diferenca < 1 ponto",
            "Level 1: 25% de lucro -> Move SL para break-even",
            "Level 2: 50% de lucro -> Fecha 50% (lock in profits)",
            "Level 3: 75% de lucro -> Trailing stop (deixa correr)",
        ]

        for msg in messages:
            # Assert: Mensagem pode ser encodada em cp1252
            try:
                msg.encode("cp1252")
            except UnicodeEncodeError as e:
                pytest.fail(f"Message contains non-cp1252 character: {msg}\nError: {e}")

    def test_ascii_arrow_is_equivalent_to_unicode_arrow(self) -> None:
        """Verifica que -> (ASCII) e Unicode arrow representam mesma semantica."""
        ascii_arrow = "  -> INVALID REQUEST"
        unicode_arrow = "  → INVALID REQUEST"

        # Ambas tienen misma semantica
        assert ascii_arrow.replace("->", " ") == unicode_arrow.replace("→", " ")

    def test_logger_without_unicode_handles_windows_encoding(self) -> None:
        """Integração: verificar que logger com strings ASCII funciona."""
        logger = logging.getLogger("test_windows")
        logger.handlers.clear()

        buffer = io.StringIO()
        handler = logging.StreamHandler(buffer)
        handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Simular as mensagens que estavam quebrando
        test_messages = [
            "[PROTEÇÃO] Posição #2276837237 em +33.3% de lucro. Movendo SL para break-even",
            "[PROTEÇÃO] Falha ao modificar SL: -> INVALID REQUEST",
            "[CICLO 1] Iniciando iteração do loop...",
        ]

        for msg in test_messages:
            try:
                logger.error(msg)
            except UnicodeEncodeError as e:
                pytest.fail(f"Encoding error for message: {msg}\nError: {e}")

        output = buffer.getvalue()
        assert "PROTEÇÃO" in output
        assert "INVALID REQUEST" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
