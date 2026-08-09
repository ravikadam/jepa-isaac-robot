# LinkedIn launch post

Can a robot move toward what success *looks like*, without being given the target's
coordinates?

I connected Meta FAIR's action-conditioned V-JEPA 2-AC world model to a Franka Panda
robot in NVIDIA Isaac Sim. The model compares a live camera image with a goal image,
predicts the visual effect of candidate robot actions, and sends the selected
Cartesian movement to Isaac's RMPFlow controller.

The final demo is interesting, but the path to it was equally instructive: non-root
RunPod permissions, an official container without `python3` or Git, a generic image
with an incompatible Vulkan stack, CUDA wheel selection, and an Isaac Sim 6 API
change. I documented the failures as carefully as the successful control loop so
that someone else can reproduce—and improve—the experiment.

Article: [MEDIUM_ARTICLE_URL]

Demo video: [DEMO_VIDEO_URL]

The article links to the complete public GitHub repository, setup instructions,
metrics, and limitations.

#AI #Robotics #WorldModels #VJEPA #NVIDIAIsaacSim #RunPod #EmbodiedAI
