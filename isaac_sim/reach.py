"""Run with Isaac Sim's python.sh, not a system Python interpreter."""

import argparse
import os

os.environ.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")

parser = argparse.ArgumentParser()
parser.add_argument("--method", choices=("oracle", "random", "vjepa"), default="vjepa")
parser.add_argument("--vjepa-repo")
parser.add_argument("--headless", action="store_true")
parser.add_argument("--episodes", type=int, default=5)
parser.add_argument("--mpc-samples", type=int, default=64)
parser.add_argument("--max-steps", type=int, default=30)
args, _ = parser.parse_known_args()

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": args.headless})

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from isaacsim.core.api import World
from isaacsim.core.api.objects import DynamicCuboid
from isaacsim.core.utils.rotations import euler_angles_to_quat
from isaacsim.robot.manipulators.examples.franka import Franka
from isaacsim.robot.manipulators.examples.franka.controllers import RMPFlowController
from isaacsim.sensors.camera import Camera

from jepa_robot.control import CartesianAction, EpisodeMetrics, reached


def settle(world, frames=30):
    for _ in range(frames):
        world.step(render=True)


def rgb(camera):
    frame = camera.get_rgba()
    if frame is None:
        raise RuntimeError("Camera returned no frame")
    return np.ascontiguousarray(frame[..., :3].astype(np.uint8))


def ee_pose(robot):
    xyz, quat = robot.end_effector.get_world_pose()
    # V-JEPA was trained with xyz + Euler angles + gripper closedness. Reaching
    # keeps orientation and gripper fixed, so only xyz must match exactly.
    return np.asarray([*xyz, 0.0, np.pi, 0.0, 0.0], dtype=np.float32)


def drive_to(world, robot, controller, xyz, physics_steps=12):
    for _ in range(physics_steps):
        action = controller.forward(
            target_end_effector_position=np.asarray(xyz),
            target_end_effector_orientation=euler_angles_to_quat([0, np.pi, 0]),
        )
        robot.get_articulation_controller().apply_action(action)
        world.step(render=True)


run_dir = ROOT / "runs" / time.strftime("%Y%m%d-%H%M%S")
run_dir.mkdir(parents=True, exist_ok=True)

world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()
robot = world.scene.add(Franka(prim_path="/World/Franka", name="franka"))
target = world.scene.add(DynamicCuboid(
    prim_path="/World/target", name="target", position=np.array([0.48, 0.0, 0.08]),
    scale=np.array([0.05, 0.05, 0.05]), color=np.array([0.9, 0.1, 0.1]), mass=1.0,
))
camera = Camera(
    prim_path="/World/camera", position=np.array([1.25, 0.0, 0.85]),
    orientation=euler_angles_to_quat([0.0, 1.05, np.pi]), resolution=(256, 256), frequency=20,
)
camera.initialize()
world.reset()
controller = RMPFlowController(name="rmpflow", robot_articulation=robot)
planner = None
if args.method == "vjepa":
    if not args.vjepa_repo:
        parser.error("--vjepa-repo is required when --method=vjepa")
    from jepa_robot.vjepa_planner import VJepaPlanner

    planner = VJepaPlanner(args.vjepa_repo, samples=args.mpc_samples)

rows = []
rng = np.random.default_rng(7)
for episode in range(args.episodes):
    target_xyz = np.array([rng.uniform(0.42, 0.56), rng.uniform(-0.16, 0.16), 0.12])
    target.set_world_pose(position=target_xyz)
    world.reset()
    controller.reset()
    settle(world)

    # Produce a visual demonstration/goal, then restore the initial joint state.
    initial_joints = robot.get_joint_positions().copy()
    for _ in range(80):
        drive_to(world, robot, controller, target_xyz, physics_steps=1)
    goal_rgb = rgb(camera)
    Image.fromarray(goal_rgb).save(run_dir / f"episode-{episode:03d}-goal.png")
    robot.set_joint_positions(initial_joints)
    controller.reset()
    settle(world)
    goal_rep = planner.encode_goal(goal_rgb) if planner else None

    latencies = []
    trace_path = run_dir / f"episode-{episode:03d}-trace.jsonl"
    frames_dir = run_dir / f"episode-{episode:03d}-frames"
    frames_dir.mkdir()
    success = False
    with trace_path.open("w") as trace:
        for step in range(args.max_steps):
            current_rgb = rgb(camera)
            pose = ee_pose(robot)
            started = time.perf_counter()
            if args.method == "vjepa":
                action = planner.act(current_rgb, pose, goal_rep)
            elif args.method == "oracle":
                action = CartesianAction.from_sequence(
                    [*(target_xyz - pose[:3]), 0.0, 0.0, 0.0, 0.0]
                )
            else:
                action = CartesianAction.from_sequence(
                    [*rng.uniform(-0.05, 0.05, size=3), 0.0, 0.0, 0.0, 0.0]
                )
            latencies.append((time.perf_counter() - started) * 1000)
            commanded_xyz = pose[:3] + action.translation
            drive_to(world, robot, controller, commanded_xyz)
            actual_xyz = robot.end_effector.get_world_pose()[0]
            distance = float(np.linalg.norm(actual_xyz - target_xyz))
            Image.fromarray(current_rgb).save(frames_dir / f"{step:04d}.png")
            trace.write(json.dumps({
                "episode": episode, "step": step, "planning_ms": latencies[-1],
                "action_xyz": action.translation.tolist(),
                "commanded_xyz": commanded_xyz.tolist(),
                "actual_xyz": np.asarray(actual_xyz).tolist(),
                "target_xyz": target_xyz.tolist(), "distance_m": distance,
            }) + "\n")
            trace.flush()
            if reached(actual_xyz, target_xyz):
                success = True
                break

    final_xyz = robot.end_effector.get_world_pose()[0]
    Image.fromarray(rgb(camera)).save(run_dir / f"episode-{episode:03d}-final.png")
    metric = EpisodeMetrics(
        seed=episode, method=args.method, success=success, steps=step + 1,
        final_distance_m=float(np.linalg.norm(final_xyz - target_xyz)),
        mean_planning_ms=float(np.mean(latencies)),
    )
    rows.append(metric)
    print(metric)

with (run_dir / "metrics.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(EpisodeMetrics.__annotations__))
    writer.writeheader()
    for row in rows:
        writer.writerow(row.__dict__)

simulation_app.close()
