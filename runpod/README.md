# RunPod deployment notes

The installed `runpodctl` is authenticated. The account currently has a small
balance, so do not leave a pod running after the experiment.

Create a **Pod** (not Serverless) from `nvcr.io/nvidia/isaac-sim:6.0.1`. Recommended:

- GPU: RTX 4090 (24 GB) minimum; A40/A6000 (48 GB) is safer for V-JEPA 2-AC MPC.
- Container disk: 50 GB minimum; volume: 30 GB for model/cache/results.
- Docker command: keep the image's shell/entrypoint available.
- Environment: `ACCEPT_EULA=Y`, `PRIVACY_CONSENT=Y`.

Inside the pod, copy/clone this repository and run:

```bash
cd /workspace/jepa
git clone --depth 1 https://github.com/facebookresearch/vjepa2 third_party/vjepa2
/isaac-sim/python.sh -m pip install -e third_party/vjepa2
/isaac-sim/python.sh isaac_sim/reach.py \
  --vjepa-repo third_party/vjepa2 --headless --episodes 5 --mpc-samples 32
```

Download `runs/` and terminate the pod after the run. Pulling Isaac Sim (~10 GB),
warming shaders, and downloading V-JEPA weights makes the first run much slower
than subsequent episodes.

