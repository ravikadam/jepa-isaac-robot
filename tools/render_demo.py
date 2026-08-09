"""Render an episode trace into a community-friendly MP4 and HTML dashboard."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/SFNS.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--episode", type=int, default=0)
    parser.add_argument("--fps", type=int, default=3)
    args = parser.parse_args()
    prefix = f"episode-{args.episode:03d}"
    goal = Image.open(args.run_dir / f"{prefix}-goal.png").convert("RGB")
    trace = [json.loads(line) for line in (args.run_dir / f"{prefix}-trace.jsonl").read_text().splitlines()]
    with (args.run_dir / "metrics.csv").open(newline="") as handle:
        method = next(csv.DictReader(handle))["method"]
    method_label = {"vjepa": "V-JEPA PLANNER", "oracle": "ORACLE CONTROLLER", "random": "RANDOM BASELINE"}[method]
    output_dir = args.run_dir / f"{prefix}-demo-frames"
    output_dir.mkdir(exist_ok=True)
    title, body, mono = font(34), font(23), font(21)

    for item in trace:
        current = Image.open(args.run_dir / f"{prefix}-frames" / f"{item['step']:04d}.png").convert("RGB")
        canvas = Image.new("RGB", (1280, 720), "#07111f")
        current = current.resize((480, 480)); goal_img = goal.resize((320, 320))
        canvas.paste(current, (42, 118)); canvas.paste(goal_img, (552, 118))
        draw = ImageDraw.Draw(canvas)
        draw.text((42, 34), f"{method_label} × Isaac Sim", font=title, fill="#f4f8ff")
        draw.text((42, 82), "LIVE ROBOT CAMERA", font=body, fill="#6ee7ff")
        draw.text((552, 82), "VISUAL GOAL", font=body, fill="#a7f3d0")
        draw.rounded_rectangle((902, 82, 1240, 598), 18, fill="#101d30", outline="#263a55", width=2)
        draw.text((930, 112), method_label, font=body, fill="#fbbf24")
        action = item["action_xyz"]
        lines = [
            f"step       {item['step']:02d}",
            f"Δx       {action[0]:+.4f} m",
            f"Δy       {action[1]:+.4f} m",
            f"Δz       {action[2]:+.4f} m",
            "",
            f"goal gap   {item['distance_m']:.3f} m",
            f"plan time  {item['planning_ms']:.0f} ms",
        ]
        draw.multiline_text((930, 170), "\n".join(lines), font=mono, fill="#dce8f8", spacing=14)
        progress = max(0.0, min(1.0, 1.0 - item["distance_m"] / max(trace[0]["distance_m"], 1e-6)))
        draw.rounded_rectangle((42, 638, 1240, 676), 12, fill="#15243a")
        draw.rounded_rectangle((42, 638, 42 + int(1198 * progress), 676), 12, fill="#22c55e")
        draw.text((530, 642), f"progress to visual goal  {progress:5.1%}", font=body, fill="white")
        canvas.save(output_dir / f"{item['step']:04d}.png")

    try:
        import imageio.v2 as imageio
        with imageio.get_writer(args.run_dir / f"{prefix}-demo.mp4", fps=args.fps, codec="libx264") as video:
            for frame in sorted(output_dir.glob("*.png")):
                video.append_data(imageio.imread(frame))
    except Exception as error:
        print(f"Frames rendered; MP4 skipped: {error}")


if __name__ == "__main__":
    main()
