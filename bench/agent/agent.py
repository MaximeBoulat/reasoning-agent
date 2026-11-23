import time
from collections.abc import Callable
from pathlib import Path

from .inference import Inference
from .tools import ProjectTools, SCHEMAS


_PROMPT_DIR = Path(__file__).resolve().parent.parent / "SystemPrompt"
SYSTEM = ((_PROMPT_DIR / "Prompt.md").read_text(encoding="utf-8")
          + (_PROMPT_DIR / "Example.md").read_text(encoding="utf-8") + "\n")


class Agent:
    def __init__(self, inference: Inference, tools: ProjectTools, emit: Callable[..., None], max_turns: int) -> None:
        self.inference = inference
        self.tools = tools
        self.emit = emit
        self.max_turns = max_turns

    def run(self, task: str) -> str:
        self.inference.begin(task)
        final = None
        for step in range(1, self.max_turns + 1):
            print(f"Turn {step}/{self.max_turns}: requesting {self.inference.model}", flush=True)
            payload = self.inference.payload(SYSTEM, SCHEMAS)
            self.emit("llm_request", step=step, payload=payload)
            started = time.perf_counter()
            body = self.inference.request(payload)
            self.emit("llm_response", step=step, body=body, elapsed_seconds=time.perf_counter() - started)
            turn = self.inference.accept(body)
            self.emit("assistant_turn", step=step, text=turn.text, reasoning_summaries=turn.reasoning,
                      calls=turn.calls, usage=body.get("usage"), finished=turn.finished)
            results = []
            for call in turn.calls:
                self.emit("tool_call", step=step, **call)
                started = time.perf_counter()
                result = self.tools.dispatch(call["name"], call["arguments"])
                self.emit("tool_result", step=step, id=call["id"], name=call["name"], result=result,
                          elapsed_seconds=time.perf_counter() - started)
                print(f"  {call['name']}: {'error' if 'error' in result else 'ok'}", flush=True)
                results.append({"id": call["id"], "result": result})
            self.inference.add_results(results)
            if turn.finished:
                final = turn.text
                break
        if final is None:
            raise RuntimeError(f"Turn limit reached ({self.max_turns}); no final answer")
        return final
