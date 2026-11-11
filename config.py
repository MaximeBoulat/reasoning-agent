import os
from pathlib import Path


def _load_env(path: Path) -> None:
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]
                os.environ.setdefault(key.strip(), value)


PROJECT_DIR = Path(__file__).resolve().parent
_load_env(PROJECT_DIR / ".env")

SOURCE_DIR = PROJECT_DIR / "dropbox"
OUTPUT_DIR = PROJECT_DIR / "output"
TASK_PATH = PROJECT_DIR / "task.txt"
DEFAULT_PROVIDER = "anthropic"
MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-6.1-sol"}
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
API_KEYS = {"anthropic": ANTHROPIC_API_KEY, "openai": OPENAI_API_KEY}
DEFAULT_EFFORT = "medium"
MAX_TURNS = 100
MAX_OUTPUT_TOKENS = 16384
REQUEST_TIMEOUT = 600
