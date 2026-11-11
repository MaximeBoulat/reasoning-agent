import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import config
from bench.agent.agent import Agent, SYSTEM
from bench.agent.inference import Inference
from bench.agent.tools import EXCLUDED, ProjectTools
from bench.log import RunLog, utc_now


def positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description="Start an architecture decomposition run.")
    parser.add_argument("--provider", choices=config.MODELS, default=config.DEFAULT_PROVIDER)
    parser.add_argument("--model")
    parser.add_argument("--source", type=Path, default=config.SOURCE_DIR)
    parser.add_argument("--task", type=Path, default=config.TASK_PATH)
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default=config.DEFAULT_EFFORT)
    parser.add_argument("--max-turns", type=positive, default=config.MAX_TURNS)
    parser.add_argument("--max-output-tokens", type=positive, default=config.MAX_OUTPUT_TOKENS)
    parser.add_argument("--timeout", type=positive, default=config.REQUEST_TIMEOUT)
    args = parser.parse_args()
    key_name = f"{args.provider.upper()}_API_KEY"
    api_key = config.API_KEYS[args.provider]
    if not api_key:
        parser.error(f"Set {key_name} in {config.PROJECT_DIR / '.env'} or your environment")
    source = args.source.resolve()
    if not source.is_dir() or not source.is_relative_to(config.SOURCE_DIR.resolve()):
        parser.error("--source must be a directory inside dropbox/")
    tools = ProjectTools(source)
    task = args.task.read_text(encoding="utf-8")
    if not task.strip():
        parser.error("Task is empty")
    model = args.model or config.MODELS[args.provider]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    directory = config.OUTPUT_DIR / run_id
    directory.mkdir(parents=True, exist_ok=False)
    log = RunLog(directory)
    metadata = {
        "run_id": run_id, "status": "running", "started_at": utc_now(),
        "provider": args.provider, "model": model, "source": str(source),
        "effort": args.effort, "max_turns": args.max_turns,
        "max_output_tokens": args.max_output_tokens, "timeout_seconds": args.timeout,
        "task": task, "system_prompt": SYSTEM, "excluded_names": sorted(EXCLUDED),
        "excludes_env_files_and_symlinks": True, "reasoning_capture": "provider summaries",
    }
    log.save("run.json", metadata)
    log.save("file-map.json", {"files": tools.files})
    log.write("run_started", **metadata)
    print(f"Run: {directory}", flush=True)
    exit_code = 0
    try:
        inference = Inference(args.provider, model, api_key, args.effort, args.max_output_tokens, args.timeout)
        answer = Agent(inference, tools, log.write, args.max_turns).run(task)
        (directory / "answer.md").write_text(answer + "\n", encoding="utf-8")
        blocks = re.findall(r"^```mermaid\s*\n(.*?)^```\s*$", answer, re.MULTILINE | re.DOTALL)
        diagram = blocks[0].strip() if len(blocks) == 1 else answer.strip()
        if (len(blocks) > 1 or not diagram.splitlines() or diagram.splitlines()[0] != "stateDiagram-v2"
                or "```" in diagram or len(diagram.splitlines()) < 2):
            raise ValueError("Final answer must contain one stateDiagram-v2 diagram; see answer.md")
        (directory / "diagram.mmd").write_text(diagram + "\n", encoding="utf-8")
        metadata["status"] = "completed"
        metadata["diagram"] = "diagram.mmd"
        print(f"Diagram: {directory / 'diagram.mmd'}", flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        metadata["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        metadata["error"] = f"{type(exc).__name__}: {exc}".replace(api_key, "[redacted]")
        log.write("run_error", error=metadata["error"])
        print(metadata["error"], flush=True)
        exit_code = 130 if isinstance(exc, KeyboardInterrupt) else 1
    finally:
        metadata["ended_at"] = utc_now()
        log.save("run.json", metadata)
        log.write("run_ended", status=metadata["status"])
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
