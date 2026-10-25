from dataclasses import asdict, dataclass, field

from .taxonomy import N_DIFFICULTY, N_SKILL_LEVELS


@dataclass
class TaskProfile:
    category: dict[str, float]
    difficulty: list[float]  # length 10, levels 1..10
    skills: dict[str, list[float]]  # each length 11, levels 0..10
    flags: dict[str, float]
    checklist: dict[str, float]
    out_tokens_log10: dict[str, float] = field(default_factory=lambda: {"p10": 2.5, "p50": 3.0, "p90": 3.5})

    def expected_difficulty(self) -> float:
        return sum((i + 1) * p for i, p in enumerate(self.difficulty))

    def expected_skill(self, axis: str) -> float:
        return sum(i * p for i, p in enumerate(self.skills[axis]))

    def top_category(self) -> tuple[str, float]:
        return max(self.category.items(), key=lambda kv: kv[1])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TaskProfile":
        assert len(d["difficulty"]) == N_DIFFICULTY
        assert all(len(v) == N_SKILL_LEVELS for v in d["skills"].values())
        return cls(**d)


class Profiler:
    def profile(self, task: dict) -> TaskProfile:  # pragma: no cover - interface
        raise NotImplementedError
