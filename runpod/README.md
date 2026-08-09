# RunPod deployment notes

Result videos:

- [V-JEPA visual-planning run](https://github.com/ravikadam/jepa-isaac-robot/releases/download/v0.1.0/vjepa-isaac-reach.mp4)
- [Oracle coordinate-controller run](https://github.com/ravikadam/jepa-isaac-robot/releases/download/v0.1.0/oracle-isaac-reach.mp4)

Do not leave a pod running after the experiment, and do not overlap replacement
pods longer than needed for a compatibility check.

Create a **Pod** (not Serverless) from `nvcr.io/nvidia/isaac-sim:6.0.1`. Recommended:

- GPU: RTX 4090 (24 GB) minimum; A40/A6000 (48 GB) is safer for V-JEPA 2-AC MPC.
- Container disk: 50 GB minimum; volume: 30 GB for model/cache/results.
- Docker command: keep the image's shell/entrypoint available.
- Environment: `ACCEPT_EULA=Y`, `PRIVACY_CONSENT=Y`.

The official container has no system `python3` or Git command. Fetch archives with
`curl`, and always use Isaac's interpreter:

```bash
curl -fsSL https://github.com/ravikadam/jepa-isaac-robot/archive/refs/heads/main.tar.gz \
  | tar -xz -C /workspace
mv /workspace/jepa-isaac-robot-main /workspace/jepa
curl -fsSL https://github.com/facebookresearch/vjepa2/archive/refs/heads/main.tar.gz \
  | tar -xz -C /workspace
mv /workspace/vjepa2-main /workspace/vjepa2

/isaac-sim/python.sh -m pip install --user \
  --index-url https://download.pytorch.org/whl/cu128 torch torchvision
/isaac-sim/python.sh -m pip install --user timm einops opencv-python

cd /workspace/jepa
/isaac-sim/python.sh isaac_sim/reach.py \
  --method oracle --headless --episodes 1 --max-steps 5
/isaac-sim/python.sh isaac_sim/reach.py \
  --method vjepa --vjepa-repo /workspace/vjepa2 \
  --headless --episodes 5 --mpc-samples 32
```

Download `runs/` and terminate the pod after the run. Pulling Isaac Sim (~10 GB),
warming shaders, and downloading V-JEPA weights makes the first run much slower
than subsequent episodes.

See [the complete troubleshooting guide](../docs/troubleshooting.md) before launch.
