import hashlib
import json
import os
from pathlib import Path


EXCLUDED = {".git", "node_modules", ".venv", "__pycache__", "dist", "build", ".next", "coverage", ".DS_Store", ".gitkeep"}
SCHEMAS = [
    {
        "name": "get_file_map",
        "description": "List project-relative file paths in sorted pages. Follow next_offset until null for the full map. Dependencies, generated directories, symlinks and .env files are excluded.",
        "parameters": {
            "type": "object", "properties": {"offset": {"type": "integer", "minimum": 0}},
            "required": ["offset"], "additionalProperties": False,
        },
    },
    {
        "name": "read_file",
        "description": "Read a UTF-8 project file, using a 1-based start_line and up to 400 lines. Follow next_line until null to finish reading. Output includes line numbers and the file SHA-256.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "line_count": {"type": "integer", "minimum": 1, "maximum": 400},
            },
            "required": ["path", "start_line", "line_count"], "additionalProperties": False,
        },
    },
]


class ProjectTools:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=True)
        self.files = []
        for directory, folders, files in os.walk(self.root):
            folders[:] = sorted(name for name in folders if self.allowed(Path(directory) / name))
            self.files.extend((Path(directory) / name).relative_to(self.root).as_posix()
                              for name in files if self.allowed(Path(directory) / name))
        self.files.sort()
        self.file_set = set(self.files)
        if not self.files:
            raise ValueError(f"No input files found in {self.root}")

    def allowed(self, path: Path) -> bool:
        return path.name not in EXCLUDED and not path.name.startswith(".env") and not path.is_symlink()

    def dispatch(self, name: str, arguments: object) -> dict:
        try:
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be an object")
            if name == "get_file_map":
                if set(arguments) != {"offset"}:
                    raise ValueError("Expected offset")
                offset = arguments["offset"]
                if type(offset) is not int or not 0 <= offset <= len(self.files):
                    raise ValueError("offset is outside the file map")
                end = min(offset + 500, len(self.files))
                result = {"files": self.files[offset:end], "total_files": len(self.files),
                          "next_offset": end if end < len(self.files) else None}
            elif name == "read_file":
                if set(arguments) != {"path", "start_line", "line_count"}:
                    raise ValueError("Expected path, start_line and line_count")
                result = self.read_file(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
        except (ValueError, TypeError, OSError, UnicodeError) as exc:
            result = {"error": f"{type(exc).__name__}: {exc}"}
        return result

    def read_file(self, path: str, start_line: int, line_count: int) -> dict:
        if not isinstance(path, str) or path not in self.file_set:
            raise ValueError("path must be a file from get_file_map")
        target = self.root / path
        if any(part.is_symlink() for part in [target, *target.parents]) or not target.resolve().is_relative_to(self.root):
            raise ValueError("File is outside the source root or is a symlink")
        if type(start_line) is not int or start_line < 1 or type(line_count) is not int or not 1 <= line_count <= 400:
            raise ValueError("Invalid line range")
        if target.stat().st_size > 2_000_000:
            raise ValueError("File exceeds the 2 MB read limit")
        content = target.read_bytes()
        text = content.decode("utf-8")
        if "\x00" in text:
            raise ValueError("Binary files are not supported")
        lines = text.splitlines()
        if start_line > max(1, len(lines)):
            raise ValueError("start_line is beyond the end of the file")
        end = min(start_line - 1 + line_count, len(lines))
        selected = []
        characters = 0
        for index in range(start_line - 1, end):
            line = lines[index]
            if len(line) > 60_000:
                raise ValueError("A line exceeds the 60,000 character output limit")
            if characters + len(line) > 60_000:
                break
            selected.append({"line": index + 1, "text": line})
            characters += len(line)
        last = start_line - 1 + len(selected)
        return {"path": path, "sha256": hashlib.sha256(content).hexdigest(), "total_lines": len(lines),
                "lines": selected, "next_line": last + 1 if last < len(lines) else None}
