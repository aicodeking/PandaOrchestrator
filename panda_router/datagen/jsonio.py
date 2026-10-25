import json
import os
import re
from pathlib import Path

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str):
    """Return the largest JSON object/array found in free-form CLI output.

    Handles markdown fences, bullet prefixes ("• "), leading chatter and trailing logs.
    Raises ValueError when nothing parses.
    """
    if text is None:
        raise ValueError("no output")
    dec = json.JSONDecoder(strict=False)  # tolerate raw newlines inside strings
    stripped = text.strip()
    try:
        return dec.decode(stripped)
    except json.JSONDecodeError:
        pass
    # Fences may also occur *inside* JSON strings (code snippets), so consider the whole text and
    # every fenced block and keep the longest JSON value found anywhere.
    candidates = [text] + [m.group(1) for m in _FENCE.finditer(text)]
    best, best_len = None, -1
    for cand in candidates:
        i = 0
        while i < len(cand):
            if cand[i] in "{[":
                try:
                    obj, end = dec.raw_decode(cand, i)
                    if end - i > best_len:
                        best, best_len = obj, end - i
                    i = end  # skip nested values of an already-parsed top-level value
                    continue
                except json.JSONDecodeError:
                    pass
            i += 1
    if best is None:
        raise ValueError("no JSON found in output")
    return best


def read_jsonl(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # tolerate a torn last line after a crash
    return out


def append_jsonl(path, rows) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def write_jsonl(path, rows) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)
