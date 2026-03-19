"""
ROADMAP-DIARIOS-03: Evolucao de perguntas de reflexao.

Responsabilidades:
- Gerar perguntas de reflexao a partir de contexto de trade.
- Evoluir profundidade conforme historico de sessoes.
- Evitar repeticao de perguntas ja utilizadas recentemente.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ReflectionLevel(str, Enum):
    """Nivel de profundidade da reflexao."""

    BASICO = "basico"
    INTERMEDIARIO = "intermediario"
    AVANCADO = "avancado"


@dataclass(frozen=True)
class ReflectionQuestion:
    """Representa uma pergunta de reflexao gerada."""

    prompt: str
    level: ReflectionLevel
    category: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Converte pergunta para estrutura serializavel."""
        return {
            "prompt": self.prompt,
            "level": self.level.value,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }


class ReflectionQuestionEvolution:
    """Motor de evolucao para perguntas de reflexao do diario."""

    _BASE_QUESTIONS: dict[str, list[str]] = {
        "risk": [
            "Qual foi o risco real assumido nesta operacao?",
            "Onde o plano de risco foi respeitado ou quebrado?",
            "Se repetisse o setup hoje, como ajustaria o tamanho da posicao?",
        ],
        "execution": [
            "A entrada foi executada no gatilho previsto?",
            "Qual sinal de mercado voce ignorou antes da entrada?",
            "Qual microdecisao mais impactou o resultado final?",
        ],
        "mindset": [
            "Qual emocao estava dominante durante a operacao?",
            "Em que momento a disciplina ficou mais fragil?",
            "Qual pensamento recorrente pode estar enviesando suas decisoes?",
        ],
    }

    def evolve_questions(
        self,
        trade_context: dict[str, Any],
        historical_sessions: list[dict[str, Any]],
        used_prompts: list[str] | None = None,
        limit: int = 3,
    ) -> list[ReflectionQuestion]:
        """
        Gera perguntas evoluidas considerando contexto e historico.

        Args:
            trade_context: Dados de uma operacao/sessao atual.
            historical_sessions: Sessoes anteriores para calibrar profundidade.
            used_prompts: Perguntas recentes para evitar repeticao.
            limit: Quantidade maxima de perguntas.
        """
        if limit <= 0:
            return []

        level = self._resolve_level(historical_sessions)
        categories = self._resolve_categories(trade_context)
        blocked = {prompt.strip().lower() for prompt in (used_prompts or [])}

        generated: list[ReflectionQuestion] = []
        for category in categories:
            for base_prompt in self._BASE_QUESTIONS.get(category, []):
                prompt = self._adapt_prompt_for_level(base_prompt, level)
                if prompt.strip().lower() in blocked:
                    continue
                generated.append(
                    ReflectionQuestion(
                        prompt=prompt,
                        level=level,
                        category=category,
                        created_at=datetime.now(),
                    )
                )
                if len(generated) >= limit:
                    return generated

        return generated

    def _resolve_level(self, historical_sessions: list[dict[str, Any]]) -> ReflectionLevel:
        total_sessions = len(historical_sessions)
        if total_sessions >= 20:
            return ReflectionLevel.AVANCADO
        if total_sessions >= 8:
            return ReflectionLevel.INTERMEDIARIO
        return ReflectionLevel.BASICO

    def _resolve_categories(self, trade_context: dict[str, Any]) -> list[str]:
        categories = ["execution", "risk", "mindset"]
        if trade_context.get("high_risk"):
            categories = ["risk", "execution", "mindset"]
        if trade_context.get("emotional_instability"):
            categories = ["mindset", "risk", "execution"]
        return categories

    def _adapt_prompt_for_level(
        self,
        prompt: str,
        level: ReflectionLevel,
    ) -> str:
        if level == ReflectionLevel.BASICO:
            return prompt
        if level == ReflectionLevel.INTERMEDIARIO:
            return f"{prompt} Quais evidencias objetivas sustentam sua resposta?"
        return (
            f"{prompt} Quais evidencias objetivas sustentam sua resposta? "
            "Que experimento pratico voce vai executar na proxima sessao?"
        )
