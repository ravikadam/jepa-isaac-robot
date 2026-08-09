"""Thin adapter around Meta's official V-JEPA 2-AC notebook MPC implementation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from .control import CartesianAction


class VJepaPlanner:
    def __init__(self, repo: str, samples=64, device="cuda:0"):
        repo_path = Path(repo).resolve()
        if not (repo_path / "hubconf.py").exists():
            raise FileNotFoundError(f"Not a V-JEPA 2 checkout: {repo_path}")
        sys.path.insert(0, str(repo_path))
        sys.path.insert(0, str(repo_path / "notebooks"))

        import torch
        from app.vjepa_droid.transforms import make_transforms
        from utils.world_model_wrapper import WorldModel

        encoder, predictor = torch.hub.load(str(repo_path), "vjepa2_ac_vit_giant", source="local")
        encoder, predictor = encoder.to(device).eval(), predictor.to(device).eval()
        crop_size = 256
        transform = make_transforms(
            random_horizontal_flip=False,
            random_resize_aspect_ratio=(1.0, 1.0),
            random_resize_scale=(1.0, 1.0),
            reprob=0.0,
            auto_augment=False,
            motion_shift=False,
            crop_size=crop_size,
        )
        self.torch = torch
        self.model = WorldModel(
            encoder=encoder,
            predictor=predictor,
            tokens_per_frame=(crop_size // encoder.patch_size) ** 2,
            transform=transform,
            device=device,
            mpc_args={
                "rollout": 2, "samples": samples, "topk": min(10, samples),
                "cem_steps": 5, "momentum_mean": 0.15, "momentum_std": 0.15,
                "maxnorm": 0.05, "verbose": False,
            },
        )

    def encode_goal(self, rgb: np.ndarray):
        with self.torch.inference_mode():
            return self.model.encode(rgb)

    def act(self, rgb: np.ndarray, pose7: np.ndarray, goal_rep) -> CartesianAction:
        with self.torch.inference_mode():
            rep = self.model.encode(rgb).view(1, 1, self.model.tokens_per_frame, -1)
            goal = goal_rep.view(1, 1, self.model.tokens_per_frame, -1)
            pose = self.torch.as_tensor(pose7, device=self.model.device, dtype=rep.dtype).view(1, 1, 7)
            action = self.model.infer_next_action(rep, pose, goal)[0].detach().cpu().numpy()
        return CartesianAction.from_sequence(action)

