import os
import anthropic
from typing import Generator

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

HAIKU = "claude-3-haiku-20240307"
SONNET = "claude-3-5-sonnet-20240620"
CLAUDE_MODEL = HAIKU  # Expose for other modules

ALL_TOOLS = [
    {
        "name": "get_calendar_events",
        "description": "Look up the user's scheduled calendar events from MongoDB.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date string, e.g. 2026-07-23"}
            },
            "required": ["date"]
        }
    },
    {
        "name": "get_faq_answer",
        "description": "Look up a frequently asked question from the MongoDB FAQ collection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"}
            },
            "required": ["question"]
        }
    },
    {
        "name": "book_calendar",
        "description": "Book a new calendar event for the user. Use when the caller asks to schedule, book, or set up a meeting or appointment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id":     {"type": "string", "description": "The user/business account ID"},
                "title":       {"type": "string", "description": "Short title for the event, e.g. 'Consultation Call'"},
                "date":        {"type": "string", "description": "ISO datetime string, e.g. '2026-07-24T15:00:00'"},
                "description": {"type": "string", "description": "Optional longer description or notes"}
            },
            "required": ["user_id", "title", "date"]
        }
    },
    {
        "name": "send_sms",
        "description": "Send an SMS confirmation or summary to the caller's phone number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to_number": {"type": "string", "description": "Destination phone number in E.164 format, e.g. '14045551234'"},
                "text":      {"type": "string", "description": "The SMS message body to send"}
            },
            "required": ["to_number", "text"]
        }
    }
]


def _dispatch_tool(tool_name: str, tool_input: dict, services: dict) -> str:
    mongo = services.get("mongo")
    vonage = services.get("vonage")

    if tool_name == "get_calendar_events":
        return mongo.search_calendar("default", tool_input.get("date", ""))
    elif tool_name == "get_faq_answer":
        return mongo.query_faq("default", tool_input["question"])
    elif tool_name == "book_calendar":
        return mongo.book_calendar(
            user_id=tool_input["user_id"],
            title=tool_input["title"],
            date=tool_input["date"],
            description=tool_input.get("description", "")
        )
    elif tool_name == "send_sms":
        from app.services.vonage_service import send_sms
        return send_sms(
            to_number=tool_input["to_number"],
            text=tool_input["text"]
        )
    else:
        return f"Unknown tool: {tool_name}"


def claude_chat(system_prompt: str, messages: list, services: dict = None, use_tools: bool = True) -> dict:
    kwargs = {
        "model": SONNET,
        "max_tokens": 1024,
        "system": system_prompt,
        "messages": list(messages),
    }
    if use_tools:
        kwargs["tools"] = ALL_TOOLS

    while True:
        response = client.messages.create(**kwargs)

        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if not tool_calls or not use_tools or not services:
            text = "".join(b.text for b in response.content if b.type == "text")
            return {"text": text, "tool_calls": []}

        tool_results = []
        for call in tool_calls:
            result_text = _dispatch_tool(call.name, call.input, services)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": result_text
            })

        kwargs["messages"].append({"role": "assistant", "content": response.content})
        kwargs["messages"].append({"role": "user", "content": tool_results})


def _stream_claude_tokens(system_prompt: str, messages: list) -> Generator[str, None, None]:
    with client.messages.stream(
        model=HAIKU,
        max_tokens=512,
        system=system_prompt,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
