"""Panda Router task-profiler model: Ettin encoder + multi-task heads.

Torch-free imports (``decode``, ``onnx_profiler.OnnxProfiler``) are safe for serving without torch.
"""

HEAD_ORDER = ["category", "difficulty", "skills", "flags", "checklist", "out_tokens"]


def __getattr__(name):
    if name in ("OnnxProfiler", "TorchProfiler"):
        from . import onnx_profiler

        return getattr(onnx_profiler, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
