"""Source root package.

Evita imports recursivos/pesados em tempo de importacao do pacote raiz.
Os subpacotes continuam acessiveis normalmente via imports explicitos.
"""

__all__ = ["application", "domain", "infrastructure"]
