#!/usr/bin/env bash
set -euo pipefail
exec 9>/tmp/jepa-bootstrap.lock
flock -n 9 || { echo "bootstrap is already running"; exit 0; }

if command -v apt-get >/dev/null && [[ $(id -u) -eq 0 ]]; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libxt6 ffmpeg
fi

cd /workspace
python -m venv /opt/isaacenv
/opt/isaacenv/bin/python -m pip install --upgrade pip
/opt/isaacenv/bin/python -m pip install "isaacsim[all,extscache]==6.0.1.0" \
  --extra-index-url https://pypi.nvidia.com

if [[ ! -d /workspace/jepa/third_party/vjepa2/.git ]]; then
  git clone --depth 1 https://github.com/facebookresearch/vjepa2.git \
    /workspace/jepa/third_party/vjepa2
fi
/opt/isaacenv/bin/python -m pip install -e /workspace/jepa/third_party/vjepa2
# Isaac Sim pins these runtime packages more tightly than V-JEPA's optional
# notebook dependencies. Restore the simulator-compatible versions.
/opt/isaacenv/bin/python -m pip install \
  click==8.1.7 psutil==5.9.8 typing_extensions==4.12.2

cd /workspace/jepa
/opt/isaacenv/bin/python -m unittest discover -s tests -v
touch /workspace/BOOTSTRAP_COMPLETE
