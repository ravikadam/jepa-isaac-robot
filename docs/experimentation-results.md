# Experimentation Results: I Gave V-JEPA 2-AC a Robot Body in NVIDIA Isaac Sim

Videos:

- [V-JEPA visual-planning run](https://github.com/ravikadam/jepa-isaac-robot/releases/download/v0.1.0/vjepa-isaac-reach.mp4)
- [Oracle coordinate-controller run](https://github.com/ravikadam/jepa-isaac-robot/releases/download/v0.1.0/oracle-isaac-reach.mp4)

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

![V-JEPA and oracle architecture](https://raw.githubusercontent.com/ravikadam/jepa-isaac-robot/main/docs/architecture.svg)

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

## What the oracle does when JEPA is absent

In everyday language, the oracle lets the robot use a cheat sheet. JEPA must look
at camera images and infer which movement might help. The oracle can ask Isaac Sim
for the cube's exact location, so it already knows the correct direction to move.

The oracle answers a useful control question: can the simulated robot and its motion
controller complete the task when perception and visual planning are removed? Isaac
Sim already knows the cube's exact `(x, y, z)` position and the gripper's current
position. The oracle subtracts the latter from the former, clips that Cartesian
movement to the same maximum step size used by JEPA, keeps orientation and gripper
state fixed, and sends the resulting target pose to RMPFlow.

RMPFlow then performs exactly the same job it performs for JEPA: converting the
requested end-effector pose into joint commands while respecting the robot model.
The difference is only who chooses the target pose. JEPA chooses it by comparing
predicted visual futures with a goal image; the oracle chooses it directly from
privileged simulator coordinates. That makes the oracle an upper-bound and a
diagnostic tool, not a fair vision-based competitor. If the oracle fails, the scene,
controller, tolerance, or step budget is wrong. If the oracle succeeds but JEPA
fails, the likely problem lies in visual/action alignment or domain shift.

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

At publication time the RunPod billing record for this experiment was **$2.65**,
including failed and overlapping pods. A clean run on the final RTX 5090 setup would
have cost approximately **$0.50**: about **0.5 hours** at the observed
**$1.004 per hour**. That estimate allows time to install the pinned dependencies,
download the checkpoint once, warm Isaac, run the three trials, and transfer the
artifacts. The difference paid for diagnosis—principally the generic
container with incompatible Vulkan, repeated startup attempts, and overlap while the
official container was being validated. These figures cover cloud compute and pod
storage, not human time, and current RunPod prices may differ.

## Results

This integration run used one identical seeded target per method and a 60-step
budget. The coordinate-aware oracle succeeded at step 44 with a final distance of
**0.045 m** and **0.033 ms** mean planning overhead. V-JEPA completed all 60
action-conditioned planning cycles but did not reach the target; it finished at
**0.795 m**, with **966 ms** mean planning latency. Random Cartesian actions also
failed, finishing at **0.772 m** with **0.049 ms** planning overhead.

| Method | Success | Steps | Final distance | Mean planning time |
|---|---:|---:|---:|---:|
| Oracle | Yes | 44 | 0.045 m | 0.033 ms |
| V-JEPA 2-AC | No | 60 | 0.795 m | 966 ms |
| Random | No | 60 | 0.772 m | 0.049 ms |

V-JEPA performing slightly worse than this random seed means this is not evidence
of a successful zero-shot policy. It is evidence that the V-JEPA-to-Isaac interface
works and that the uncalibrated domain transfer does not. More seeds are required
before making a statistical comparison.

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
