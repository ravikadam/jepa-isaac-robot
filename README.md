# V-JEPA 2-AC + Isaac Sim reaching experiment

This repository is a minimal experiment for testing whether Meta's action-conditioned
V-JEPA world model can guide a Franka arm in NVIDIA Isaac Sim.

## Challenge

A fixed RGB camera observes a Franka Panda and a colored target cube. The task is
successful when the gripper reaches within 5 cm of the cube. At the start of each
episode Isaac Sim's conventional RMPFlow controller creates a **goal image** with
the gripper at the target, then resets the robot. V-JEPA 2-AC uses model-predictive
control (MPC) to choose Cartesian end-effector deltas whose predicted latent state
is closest to the goal image.

This tests a real JEPA capability: action-conditioned prediction and image-goal
planning. Plain V-JEPA is only a video encoder and cannot choose robot actions.

## Hardware and software

- An RTX Linux/Windows machine. Isaac Sim does not run locally on Apple Silicon.
- NVIDIA Isaac Sim 5.1 or newer (the adapter uses its legacy Core API, retained in
  6.x). Allow roughly 50 GB for Isaac Sim.
- A CUDA GPU with enough memory for the 1B-parameter V-JEPA 2-AC model. Start with
  `--mpc-samples 32` if memory is tight.
- Git, Python dependencies from the official V-JEPA 2 repository, and its checkpoint.

## Setup on the simulator machine

```bash
git clone https://github.com/facebookresearch/vjepa2.git third_party/vjepa2
cd third_party/vjepa2
pip install -e .
cd ../..
```

V-JEPA 2 currently documents `torch.hub.load`, which downloads the checkpoint on
first use. To run through Isaac Sim's Python:

```bash
./python.sh /path/to/this/repo/isaac_sim/reach.py \
  --vjepa-repo /path/to/this/repo/third_party/vjepa2 \
  --headless --episodes 5 --mpc-samples 64
```

Use `python.bat` instead of `python.sh` on Windows. Omit `--headless` to watch the
run. Results and camera frames are written beneath `runs/`.

## Validate the repository without Isaac Sim

The portable tests cover action clipping, pose conversion, and success metrics:

```bash
python -m unittest discover -s tests -v
```

## Experiment design

Run at least 20 seeded episodes per method and report success rate, final distance,
steps to success, and wall-clock planning latency. Use three target positions and
small random variations in cube color, lighting, and camera pose. Compare:

1. `vjepa`: the image-goal planner in this repository.
2. `oracle`: RMPFlow commanded directly to the known cube position (upper bound).
3. `random`: random Cartesian deltas (sanity-check lower bound).

The action-conditioned checkpoint was trained on real DROID trajectories, not
Isaac Sim. A weak result may therefore indicate camera/action domain mismatch,
not that JEPA representations are useless. Keep the camera fixed initially and
only add randomization after the basic run succeeds.

## References

- [V-JEPA 2 official code](https://github.com/facebookresearch/vjepa2)
- [V-JEPA research page](https://ai.meta.com/research/vjepa/)
- [Isaac Sim installation](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/quick-install.html)
- [Isaac Sim Franka pick-and-place example](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/examples/manipulation_franka_pick_place.html)

## Troubleshooting before spending GPU time

Read [the failure guide](docs/troubleshooting.md) before creating a pod. It records
the exact permission, Python, Git, Vulkan, CUDA-wheel, Isaac Sim 6 extension, and
checkpoint-URL problems encountered while building this demo, with their fixes and
prevention checks.
