# I Gave V-JEPA 2-AC a Robot Body: Visual Planning in NVIDIA Isaac Sim

> Draft status: replace bracketed result fields after the reproducible run completes.

Demo video: [DEMO_VIDEO_URL]

Code and reproduction guide: https://github.com/ravikadam/jepa-isaac-robot

## The idea: give JEPA a body

I wanted to test JEPA as more than a video representation model. The concrete
question was: if a robot can see its current situation and an image of the desired
outcome, can an action-conditioned JEPA help it decide what to do next?

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

## Why NVIDIA Isaac Sim

A physical Franka is expensive, slow to reset, and unforgiving while an interface is
still being debugged. Isaac Sim supplies the robot, physics, camera, repeatable target
placements, and RMPFlow joint-level motion control. It also lets every trial use the
same seeds, so JEPA, an oracle, and random actions can be compared on the same task.

## Architecture

```text
live RGB ──► V-JEPA encoder ──► current latent ─┐
                                                ├─► CEM/MPC ─► Δx,Δy,Δz ─► RMPFlow ─► Franka
goal RGB ──► V-JEPA encoder ──► goal latent ────┘                         │
                                                    next camera frame ◄──┘
```

In code, each control cycle is deliberately small and observable:

1. Isaac Sim renders the live camera image and reports the gripper pose.
2. The V-JEPA encoder maps live and goal images into latent representations.
3. Meta's CEM/MPC code samples seven-dimensional candidate actions and uses the
   action-conditioned predictor to estimate their visual consequences.
4. The lowest-cost candidate becomes a Cartesian action delta.
5. Isaac RMPFlow converts that requested end-effector pose into safe joint commands.
6. A new image closes the feedback loop; every action, latency, and distance is logged.

## Why V-JEPA 2-AC instead of plain V-JEPA?

Plain V-JEPA learns powerful video representations, but it is not conditioned on
robot actions. V-JEPA 2-AC adds a predictor post-trained on DROID robot trajectories.
Its seven-dimensional action is Cartesian translation, Euler-angle rotation, and
gripper closedness. That makes counterfactual planning possible: “If I move this
way, will the scene become more like the goal?”

## The robot's goal

The first challenge is intentionally modest: move the Franka gripper to a red cube.
Isaac briefly moves the arm to the cube to create a goal image, then resets it. JEPA
does not receive the cube coordinates; those are retained only for scoring and for
the coordinate-aware oracle baseline. Success means the end effector is within the
configured tolerance of the cube before the step budget expires.

## The RunPod installation was part of the experiment

The first useful result was not a robot motion—it was a sequence of infrastructure
failures. A startup script repeatedly ran `apt` as a non-root user, producing
`/var/lib/apt/lists/partial: Permission denied`. The replacement command assumed
`python3` existed, but NVIDIA's official container exposes Isaac's interpreter as
`/isaac-sim/python.sh`. A generic PyTorch image could install Isaac, yet failed
Vulkan compatibility because its graphics stack did not match Isaac Sim. Moving to
NVIDIA's official Isaac Sim 6.0.1 image fixed Vulkan, but that minimal image contained
neither Git nor PyTorch. The repository therefore arrives as a GitHub archive, and
PyTorch is installed explicitly from its CUDA 12.8 wheel index. Finally, Isaac Sim 6
moved the Franka examples behind an opt-in extension, requiring that extension to be
enabled before importing Franka and RMPFlow.

These details are preserved in the repository because “use the official container”
is not, by itself, a reproducible instruction. The practical lessons are: validate
Vulkan before downloading a multi-gigabyte model, use Isaac's own Python launcher,
do not assume root or Git exists, pin PyTorch to the host driver's CUDA generation,
and validate the scene with a cheap oracle before loading JEPA.

## What the experiment cost

At publication time the RunPod billing record for this experiment was [ACTUAL_COST],
including failed and overlapping pods. A clean run on the final RTX 5090 setup would
have cost approximately [CLEAN_PATH_COST]: [CLEAN_PATH_HOURS] hours at roughly
[HOURLY_RATE] per hour. The difference paid for diagnosis—principally the generic
container with incompatible Vulkan, repeated startup attempts, and overlap while the
official container was being validated. These figures cover cloud compute and pod
storage, not human time. Exact timestamps and the final calculator are included in
the repository so readers can substitute current RunPod pricing.

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
