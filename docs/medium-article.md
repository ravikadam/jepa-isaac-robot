# I Gave V-JEPA 2-AC a Robot Body: Visual Planning in NVIDIA Isaac Sim

> Draft status: replace bracketed result fields after the reproducible run completes.

Most robot demos quietly give the policy the object coordinates. This experiment
asks a harder and more interesting question: can a world model move a robot toward
what success *looks like*?

I connected Meta FAIR's V-JEPA 2-AC action-conditioned world model to a Franka Panda
inside NVIDIA Isaac Sim. The robot sees one live RGB image and one goal RGB image.
It never receives the target cube coordinates. At each control step, V-JEPA predicts
how candidate Cartesian motions would change its latent visual state. Model-predictive
control selects the action whose predicted representation is closest to the goal.

## What the demo does

The scene contains a Franka arm, a fixed monocular camera, and a red target cube.
Isaac Sim first uses its conventional controller to place the gripper at the target
and records that frame as the visual goal. The arm resets. From then on, only JEPA's
image-goal planner chooses the Cartesian deltas; Isaac's motion controller merely
executes those deltas safely at the joint level.

This separation matters. RMPFlow is the robot's muscles and reflexes. V-JEPA 2-AC is
the visual planner deciding where those muscles should move next.

## Architecture

```text
live RGB ──► V-JEPA encoder ──► current latent ─┐
                                                ├─► CEM/MPC ─► Δx,Δy,Δz ─► RMPFlow ─► Franka
goal RGB ──► V-JEPA encoder ──► goal latent ────┘                         │
                                                    next camera frame ◄──┘
```

## Why V-JEPA 2-AC instead of plain V-JEPA?

Plain V-JEPA learns powerful video representations, but it is not conditioned on
robot actions. V-JEPA 2-AC adds a predictor post-trained on DROID robot trajectories.
Its seven-dimensional action is Cartesian translation, Euler-angle rotation, and
gripper closedness. That makes counterfactual planning possible: “If I move this
way, will the scene become more like the goal?”

## Results

Across [N] seeded reaching episodes, the JEPA planner succeeded in [SUCCESS_RATE]
of trials, with median final gripper-to-target distance [DISTANCE] m and median
planning latency [LATENCY] ms. The coordinate-aware RMPFlow oracle achieved
[ORACLE], while random Cartesian actions achieved [RANDOM].

The most important limitation is domain shift. V-JEPA 2-AC was trained on real DROID
camera trajectories, not this synthetic Isaac Sim camera. A failure is therefore a
useful measurement of visual/action alignment—not a generic verdict on JEPA.

## Reproduce it

The public repository contains the scene, planner adapter, deterministic seeds,
metrics, video renderer, and RunPod instructions. The recommended starting point is
an RTX 5090 or 48 GB GPU, five episodes, and 32 MPC samples. Once the fixed-camera
baseline works, increase camera, lighting, texture, and target variation one axis at
a time.

## What I would try next

1. Calibrate camera and end-effector frames against the DROID convention.
2. Compare V-JEPA 2-AC against JEPA-WM and DINO-WM on identical episodes.
3. Add grasp and pick-and-place only after reaching is reliable.
4. Fine-tune on randomized Isaac trajectories, then test whether the policy transfers
   back to a physical Franka.

World models become much easier to reason about when every proposed action, visual
goal, latency, and resulting frame is visible. That transparency is the real purpose
of this demo.
