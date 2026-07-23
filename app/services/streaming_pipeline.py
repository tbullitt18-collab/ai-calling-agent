import os
from .anthropic_service import claude_chat, _stream_claude_tokens, ALL_TOOLS

USE_CLAUDE = os.environ.get("USE_CLAUDE", "false").lower() == "true"


def build_anthropic_messages(history: list) -> list:
    return [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
        for m in history if m.get("role") in ("user", "assistant")
    ]


def stream_response_to_tts(
    system_prompt: str,
    history: list,
    tts_callback,
    services: dict = None,
    caller_phone: str = None
):
    messages = build_anthropic_messages(history)

    # Inject caller phone into system prompt if available
    enriched_system = system_prompt
    if caller_phone:
        enriched_system += f"\n\nCALLER_PHONE: {caller_phone} — You may use this number for send_sms without asking."

    if USE_CLAUDE:
        pre_response = claude_chat(
            system_prompt=enriched_system,
            messages=messages,
            services=services,
            use_tools=True
        )

        if pre_response.get("tool_calls") or not pre_response.get("text"):
            messages.append({"role": "user", "content": "Please summarize what you just did for the caller in one sentence."})
            for chunk in _stream_claude_tokens(enriched_system, messages):
                tts_callback(chunk)
        else:
            for chunk in _stream_claude_tokens(enriched_system, messages):
                tts_callback(chunk)
    else:
        from .google_ai_service import _stream_gemini_tokens
        for chunk in _stream_gemini_tokens(system_prompt, history):
            tts_callback(chunk)
