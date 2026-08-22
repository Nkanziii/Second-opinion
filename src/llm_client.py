"""
Thin LLM client with three modes, auto-selected so the experiment runs
today regardless of what's set up:

1. ANTHROPIC_API_KEY set -> real calls to Claude (default model below).
2. OPENAI_API_KEY set (and no Anthropic key) -> real calls to OpenAI.
3. Neither set, or --mock passed -> canned rotating mock responses per
   persona, so you can exercise the whole pipeline (conversation loop,
   divergence scoring, transcript logging) before spending anything or
   signing up for an API key.

Swap ANTHROPIC_MODEL / OPENAI_MODEL below if you want a cheaper/faster
model for rapid iteration vs. a stronger one for the final installation.
"""

import os

ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
OPENAI_MODEL = "gpt-4o-mini"

_MOCK_RESPONSES = {
    "cautious": [
        "I hear you, {visitor_name} — before we go further, could you tell me how long this has been going on? "
        "There are several things this could be, and I'd rather not guess. Confidence: 25%",
        "That's useful, {visitor_name}, but Dr. Sure is moving too fast here — we haven't ruled anything out yet. "
        "Let's not commit to one story. Confidence: 30%",
        "I understand the appeal of a quick answer, {visitor_name}, but I'd want more information before I'd feel "
        "comfortable saying anything definite. Confidence: 20%",
    ],
    "confident": [
        "{visitor_name}, I've seen this exact pattern before — it's textbook. No need to overthink it. Confidence: 90%",
        "With respect to Dr. Hedges, {visitor_name}, more questions won't change the answer. I'm confident in this one. Confidence: 85%",
        "{visitor_name}, trust me on this — the case is clear, and further tests would just confirm what I already know. Confidence: 95%",
    ],
}


def _mock_reply(persona_id: str, visitor_name: str, turn_index: int) -> str:
    options = _MOCK_RESPONSES[persona_id]
    return options[turn_index % len(options)].format(visitor_name=visitor_name)


def get_provider(force_mock: bool = False) -> str:
    if force_mock:
        return "mock"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "mock"


class LLMClient:
    def __init__(self, force_mock: bool = False):
        self.provider = get_provider(force_mock)
        self._client = None
        if self.provider == "anthropic":
            import anthropic

            self._client = anthropic.Anthropic()
        elif self.provider == "openai":
            import openai

            self._client = openai.OpenAI()

    def reply(self, system_prompt: str, conversation: list, persona_id: str,
              visitor_name: str, turn_index: int) -> str:
        """conversation is a list of {"role": "user"|"assistant", "content": str}
        from this persona's point of view (its own turns are "assistant",
        everything said by the visitor or the other persona is "user")."""
        if self.provider == "mock":
            return _mock_reply(persona_id, visitor_name, turn_index)

        if self.provider == "anthropic":
            resp = self._client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=200,
                system=system_prompt,
                messages=conversation,
            )
            return resp.content[0].text

        if self.provider == "openai":
            messages = [{"role": "system", "content": system_prompt}] + conversation
            resp = self._client.chat.completions.create(
                model=OPENAI_MODEL,
                max_tokens=200,
                messages=messages,
            )
            return resp.choices[0].message.content

        raise RuntimeError(f"Unknown provider: {self.provider}")
