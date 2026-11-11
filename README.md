# ReasoningAgent

A Python test bench for repeated qualitative analysis of architecture decomposition. One LLM inspects a TypeScript project through two tools: `get_file_map` and `read_file`. The test bench saves the final Mermaid state diagram.

## Starting a run

Requires Python 3.12 or newer. There are no third-party Python dependencies.

Place the application's source code in `dropbox/`, either directly or inside a project subdirectory. Enter the API key for your chosen provider in the project's `.env` file:

```dotenv
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

`config.py` loads `.env` automatically and defines the model, path, and run defaults. Existing environment variables take precedence over `.env` values. Command-line options override the corresponding config defaults. `.env` is excluded from Git.

From the ReasoningAgent directory:

```sh
python3 start.py --provider anthropic
python3 start.py --provider openai
```

The default models are `claude-sonnet-5-5` and `gpt-6.1-sol`, respectively. A run uses one provider and one model throughout.

To select a particular project inside the dropbox:

```sh
python3 start.py --provider anthropic --source dropbox/my-app
```

Edit `task.txt` to set the task shared across runs, or pass `--task path/to/task.txt`. Other options are `--model`, `--effort`, `--max-turns`, `--max-output-tokens`, and `--timeout`. Defaults are medium effort, 100 inference turns, 16,384 output tokens per request, and a 600-second request timeout. Provider effort labels do not establish equivalent computational budgets across models.

Each invocation starts a fresh conversation and creates `output/<UTC timestamp>/`.

## Run artifacts

| File | Contents |
| --- | --- |
| `diagram.mmd` | Final Mermaid state diagram, without Markdown fences. |
| `answer.md` | The model's unmodified final answer. |
| `trajectory.jsonl` | Timestamped requests, responses, reasoning summaries, tool calls and results, token usage, durations, and errors. |
| `run.json` | Run status, provider, model, prompts, source root, limits, start/end times, and error if present. |
| `file-map.json` | The sorted source file inventory available at run start. |

The trajectory includes the actual file content returned by each read and its SHA-256 hash. Files are read live; keep the input project unchanged during a run and across repetitions that require identical input. The inventory is not a source snapshot.

`completed` means the model finished and returned a state-diagram artifact with the expected envelope and header. It is not a correctness score or Mermaid syntax certification. The bench does not render or grade the diagram. A failed or interrupted run retains the trajectory. Token truncation, provider errors, and exhausted turn limits terminate the run; requests are not automatically retried.

## Tools and conversation

`get_file_map` returns up to 500 sorted project-relative paths per page. `read_file` returns up to 400 numbered lines and 60,000 content characters, with continuation metadata. Reads accept UTF-8 text files up to 2 MB; individual lines above 60,000 characters are rejected. The tools exclude `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, `.next`, `coverage`, `.DS_Store`, `.gitkeep`, `.env`-prefixed entries, and symlinks. The selected source directory must be under `dropbox/`.

The agent has no shell, network, search, or write tool. Final artifact writing belongs to the test bench. Source contents are presented as evidence rather than operating instructions.

OpenAI uses the Responses API with reasoning summaries enabled and stored responses disabled. Anthropic uses the Messages API with adaptive thinking and summarized display. All returned OpenAI output items and Anthropic content blocks are retained in the conversation, including opaque reasoning content and signatures. Human-readable reasoning capture contains provider summaries, not raw internal reasoning. Complete request and response bodies are recorded without authentication headers.

## Implementation

`start.py` handles configuration, run directories, and artifact persistence. `bench/agent/agent.py` owns the inference/tool loop; `bench/agent/inference.py` translates the two provider protocols; `bench/agent/tools.py` owns source access; and `bench/log.py` writes run records. This follows DecisionBot's separation of the agent, tools, inference, and trajectory logging. There is no decision-model cascade, verifier, or scorer.

Provider references: [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [OpenAI reasoning](https://developers.openai.com/api/docs/guides/reasoning), [Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), and [Anthropic thinking](https://platform.claude.com/docs/en/build-with-claude/thinking).
