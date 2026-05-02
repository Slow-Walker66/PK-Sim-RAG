from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rag.deepseek_client import DeepSeekClient
from rag.prompts import INSUFFICIENT_MESSAGE, build_messages
from rag.retriever import RetrievedChunk, Retriever


@dataclass
class AnswerResult:
    answer: str
    citations: List[RetrievedChunk]
    insufficient: bool


class AnswerGenerator:
    def __init__(self, retriever: Retriever, deepseek: DeepSeekClient, *, max_context_chars: int = 12000):
        self.retriever = retriever
        self.deepseek = deepseek
        self.max_context_chars = max_context_chars

    def answer(self, question: str, *, top_k: int = 8, min_score: float = 0.35) -> AnswerResult:
        chunks = self.retriever.retrieve(question, top_k=top_k, min_score=min_score)
        if not chunks:
            return AnswerResult(
                answer=INSUFFICIENT_MESSAGE,
                citations=[],
                insufficient=True,
            )

        messages = build_messages(question, chunks, max_context_chars=self.max_context_chars)
        answer = self.deepseek.chat(messages)
        if not answer:
            answer = INSUFFICIENT_MESSAGE
        return AnswerResult(
            answer=answer,
            citations=chunks,
            insufficient=answer.strip() == INSUFFICIENT_MESSAGE,
        )

