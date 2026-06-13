from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai import types

from app.config import get_gemini_api_key, get_gemini_model
from app.retriever import ProductRetriever

SYSTEM_INSTRUCTION = """You are the Automat Irrigation product assistant.

Rules:
- Answer ONLY using the catalog context provided with each user message (India or international catalog for this session).
- Be concise, accurate, and helpful. Use bullet points for specs when useful.
- Mention SKU codes when relevant.
- If the context does not contain enough information, say you do not have that detail in this catalog and suggest what the user could ask instead.
- Do not invent products, specs, or prices not present in the context.
- Automat manufactures irrigation products: micro sprinklers, impact sprinklers, filtration, fertigation, and valves.
"""


@dataclass
class ChatMessage:
    role: str
    content: str


class AutomatChatbot:
    """Core Q&A engine — reuse from Streamlit or future social channel adapters."""

    def __init__(self, retriever: ProductRetriever) -> None:
        self.retriever = retriever
        api_key = get_gemini_api_key()
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to a .env file in the project root."
            )
        self.client = genai.Client(api_key=api_key)
        self.model = get_gemini_model()

    def answer(self, question: str, history: list[ChatMessage] | None = None) -> str:
        history = history or []
        context = self.retriever.build_context(question)

        contents: list[types.Content] = []
        for msg in history[-6:]:
            role = "model" if msg.role == "assistant" else "user"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg.content)])
            )

        user_prompt = (
            f"Catalog context:\n{context}\n\n"
            f"User question: {question}"
        )
        contents.append(
            types.Content(role="user", parts=[types.Part(text=user_prompt)])
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
            ),
        )

        return (response.text or "").strip() or "Sorry, I could not generate a response."
