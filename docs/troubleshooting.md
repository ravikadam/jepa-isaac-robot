# Troubleshooting: failures we hit and how to avoid them

This is a record of actual failures from the RunPod experiment. Start with the
preflight checklist; use the table below when a symptom appears.

## Preflight checklist

1. Use NVIDIA's official `nvcr.io/nvidia/isaac-sim:6.0.1` image.
2. Set `ACCEPT_EULA=Y` and `PRIVACY_CONSENT=Y`.
3. Run `/isaac-sim/isaac-sim.compatibility_check.sh` before installing models.
4. Invoke Python through `/isaac-sim/python.sh`, never an assumed `python3`.
5. Assume the container is non-root and contains neither Git nor system packages.
6. Install PyTorch from the CUDA 12.8 index used by the tested RTX 5090 pod.
7. Run the oracle smoke test before downloading the 11.8 GB checkpoint.
8. Keep only one billable pod running once compatibility is confirmed.

## Symptom, cause, fix, and prevention

| Symptom | Root cause | Fix | Prevent it next time |
|---|---|---|---|
| `List directory /var/lib/apt/lists/partial is missing - Permission denied` repeats forever | The official container runs as UID 1234, while the startup loop calls root-only `apt`. | Remove `apt` from startup. Use the official image's bundled tools or install Python packages with `pip --user`. | Run `id` first and never place a failing install command in a restart loop. |
| `/bin/bash: python3: command not found` | Isaac's interpreter is not exposed as a normal `python3` command. | Use `/isaac-sim/python.sh script.py`. | Treat `python.sh` as part of the Isaac runtime, not an optional wrapper. |
| `git: command not found` | The official runtime image is intentionally minimal. | Download GitHub source archives with `curl ...tar.gz | tar -xz`. | Do not make Git a runtime dependency in the pod. |
| Vulkan reports `ERROR_INCOMPATIBLE_DRIVER` in a generic PyTorch image | Installing Isaac's Python package does not reproduce the official image's complete graphics/Vulkan stack. | Replace the pod with NVIDIA's official Isaac Sim container and rerun the compatibility checker. | Validate Vulkan before downloading checkpoints or installing Python dependencies. |
| `ModuleNotFoundError: No module named torch` | Isaac Sim 6.0.1 does not bundle PyTorch for external ML inference. | Install a driver-compatible build through Isaac Python: `python.sh -m pip install --user --index-url https://download.pytorch.org/whl/cu128 torch torchvision`. | Check `torch.version.cuda`, execute a CUDA tensor operation, and print the GPU name before model loading. |
| pip starts downloading CUDA 13 packages on a CUDA 12.8 host | `--extra-index-url` still lets pip prefer a newer PyPI build. | Use `--index-url` for the PyTorch install, then install `timm`, `einops`, and other packages separately. | Verify the selected wheel in pip output; do not rely on the package name alone. |
| `No module named isaacsim.robot.manipulators.examples` | Isaac Sim 6 keeps the legacy Franka/RMPFlow examples as an opt-in extension. | Enable `isaacsim.robot.manipulators.examples` through Kit's extension manager before importing it. | Run a two-line import smoke test against the exact Isaac version. |
| V-JEPA tries `localhost:8300` and raises `ConnectionRefusedError` | Meta's current repository snapshot temporarily assigns its checkpoint base URL to a local test server. | The adapter explicitly selects `https://dl.fbaipublicfiles.com/vjepa2`, with `VJEPA_BASE_URL` available for mirrors. | Inspect the resolved checkpoint URL before starting a multi-gigabyte download. |
| First Isaac run appears stuck at high CPU | Extensions, robot assets, and shaders are loading/compiling; startup output can be very noisy. | Monitor the live PID and Isaac logs; allow the first launch to warm its caches. | Perform a short oracle episode first and retain the pod cache for later runs. |
| The oracle moves but does not succeed in five steps | Five clipped Cartesian actions are only a smoke test, not a realistic episode budget. | Confirm distance decreases, then run the normal 30-step budget. | Distinguish motion validation from benchmark success in metrics and documentation. |
| Cloud credit falls faster than expected | The incompatible generic pod and official validation pod overlap at about $0.99/hour each. | Delete the rejected pod immediately after the official pod passes compatibility. | Check `runpodctl pod list` and `currentSpendPerHr` after every replacement. |

## Minimal validation sequence

```bash
/isaac-sim/isaac-sim.compatibility_check.sh
/isaac-sim/python.sh -c \
  'import torch; x=torch.randn(256,256,device="cuda"); print(torch.__version__, x.sum())'
/isaac-sim/python.sh isaac_sim/reach.py \
  --headless --method oracle --episodes 1 --max-steps 5
```

Only proceed to `--method vjepa` after all three commands succeed.
