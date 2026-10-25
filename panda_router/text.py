"""Single source of truth for turning a task dict into model input text."""

MAX_CHARS = 6000


def format_input(task: dict) -> str:
    ctx = task.get("context") or {}
    parts = []
    if langs := ctx.get("repo_languages"):
        parts.append("langs=" + ",".join(langs))
    for key in ("files_in_scope", "estimated_input_tokens"):
        if ctx.get(key) is not None:
            parts.append(f"{key}={ctx[key]}")
    for key in ("has_images", "requires_tools"):
        if ctx.get(key):
            parts.append(key)
    text = (task.get("text") or "").strip()
    if len(text) > MAX_CHARS:
        half = MAX_CHARS // 2
        text = text[:half] + "\n[...]\n" + text[-half:]
    return f"[ctx] {' '.join(parts) or 'none'}\n[task] {text}"
