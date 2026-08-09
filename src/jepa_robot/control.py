from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class CartesianAction:
    """V-JEPA 2-AC action: xyz delta, Euler delta, gripper delta."""

    values: np.ndarray

    @classmethod
    def from_sequence(cls, values: Sequence[float], max_translation: float = 0.05):
        action = np.asarray(values, dtype=np.float32).reshape(7).copy()
        norm = float(np.linalg.norm(action[:3]))
        if norm > max_translation:
            action[:3] *= max_translation / norm
        return cls(action)

    @property
    def translation(self) -> np.ndarray:
        return self.values[:3]


def reached(gripper_xyz: Sequence[float], target_xyz: Sequence[float], threshold=0.05) -> bool:
    return float(np.linalg.norm(np.asarray(gripper_xyz) - np.asarray(target_xyz))) <= threshold


@dataclass
class EpisodeMetrics:
    seed: int
    method: str
    success: bool
    steps: int
    final_distance_m: float
    mean_planning_ms: float

