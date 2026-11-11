import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class Turn:
    calls: list[dict]
    text: str
    reasoning: list[str]
    finished: bool


class Inference:
    def __init__(self, provider: str, model: str, api_key: str, effort: str, max_tokens: int, timeout: int) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.effort = effort
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.history = []

    def begin(self, task: str) -> None:
        self.history = [{"role": "user", "content": task}]

    def payload(self, system: str, schemas: list[dict]) -> dict:
        if self.provider == "openai":
            result = {
                "model": self.model, "instructions": system, "input": self.history,
                "tools": [{"type": "function", "strict": True, **schema} for schema in schemas],
                "parallel_tool_calls": False, "store": False,
                "reasoning": {"effort": self.effort, "summary": "auto"},
                "max_output_tokens": self.max_tokens,
            }
        else:
            result = {
                "model": self.model, "system": system, "messages": self.history,
                "tools": [{"name": s["name"], "description": s["description"], "input_schema": s["parameters"]} for s in schemas],
                "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
                "thinking": {"type": "adaptive", "display": "summarized"},
                "output_config": {"effort": self.effort}, "max_tokens": self.max_tokens,
            }
        return result

    def request(self, payload: dict) -> dict:
        if self.provider == "openai":
            url = "https://api.openai.com/v1/responses"
            headers = {"Authorization": f"Bearer {self.api_key}"}
        else:
            url = "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").replace(self.api_key, "[redacted]")
            raise RuntimeError(f"{self.provider} HTTP {exc.code}: {detail}") from None
        return result

    def accept(self, body: dict) -> Turn:
        calls, texts, reasoning = [], [], []
        if self.provider == "openai":
            if body["status"] != "completed":
                raise RuntimeError(f"OpenAI response did not complete: {body.get('incomplete_details') or body.get('error') or body['status']}")
            self.history.extend(body["output"])
            for item in body["output"]:
                if item["type"] == "function_call":
                    calls.append({"id": item["call_id"], "name": item["name"], "arguments": item["arguments"]})
                elif item["type"] == "reasoning":
                    reasoning.extend(part["text"] for part in item.get("summary", []))
                elif item["type"] == "message":
                    for part in item["content"]:
                        if part["type"] == "refusal":
                            raise RuntimeError(f"Model refused: {part['refusal']}")
                        if part["type"] == "output_text":
                            texts.append(part["text"])
            finished = not calls
        else:
            reason = body["stop_reason"]
            if reason not in {"end_turn", "tool_use", "pause_turn"}:
                raise RuntimeError(f"Anthropic response stopped: {reason}")
            self.history.append({"role": "assistant", "content": body["content"]})
            for item in body["content"]:
                if item["type"] == "tool_use":
                    calls.append({"id": item["id"], "name": item["name"], "arguments": item["input"]})
                elif item["type"] == "thinking":
                    reasoning.append(item.get("thinking", ""))
                elif item["type"] == "text":
                    texts.append(item["text"])
            finished = reason == "end_turn" and not calls
        return Turn(calls, "\n".join(texts), reasoning, finished)

    def add_results(self, results: list[dict]) -> None:
        if self.provider == "openai":
            self.history.extend({"type": "function_call_output", "call_id": item["id"],
                                 "output": json.dumps(item["result"])} for item in results)
        elif results:
            self.history.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": item["id"], "content": json.dumps(item["result"]),
                 "is_error": "error" in item["result"]} for item in results
            ]})
