"""Panda Router task-profiler model: Ettin encoder + multi-task heads.

Torch-free imports (``decode``, ``onnx_profiler.OnnxProfiler``) are safe for serving without torch.
"""

HEAD_ORDER = ["category", "difficulty", "skills", "flags", "checklist", "out_tokens"]
