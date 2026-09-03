from __future__ import annotations

import random

from psychopy import core, visual

from .common import ExperimentConfig, blank_frames, collect_response, frames_from_ms, present_frames, save_rows, show_fixation, show_text, shuffled


def _pacman(win, pos, inward: str, radius=0.065, color="white"):
    """Create a simple Pac-Man using a circle plus a background-colored square wedge."""
    x, y = pos
    circle = visual.Circle(win, radius=radius, pos=pos, fillColor=color, lineColor=color)
    # Cover one quadrant of the disc. This is a deliberately simple procedural inducer.
    q = radius * 1.05
    dx = q / 2 if "right" in inward else -q / 2
    dy = q / 2 if "up" in inward else -q / 2
    cover = visual.Rect(
        win,
        width=q,
        height=q,
        pos=(x + dx, y + dy),
        fillColor=win.color,
        lineColor=win.color,
    )
    return circle, cover


def _inducers(win, contour: bool, rng: random.Random):
    d = 0.16
    positions = [(-d, d), (d, d), (-d, -d), (d, -d)]
    inward = ["right down", "left down", "right up", "left up"]
    if not contour:
        outward = ["left up", "right up", "left down", "right down"]
        rng.shuffle(outward)
        inward = outward
    stims = []
    for pos, direction in zip(positions, inward):
        stims.extend(_pacman(win, pos, direction))
    return stims


def _checker_mask(win, rng: random.Random, n=12):
    size = 0.045
    stims = []
    for iy in range(-n // 2, n // 2):
        for ix in range(-n // 2, n // 2):
            if rng.random() < 0.75:
                lum = rng.choice([-0.8, -0.2, 0.4, 0.9])
                stims.append(visual.Rect(win, width=size, height=size, pos=(ix * size, iy * size), fillColor=[lum]*3, lineColor=[lum]*3))
    return stims


def run(win, cfg: ExperimentConfig, output_dir: str = "data", seed: int = 2):
    p = cfg.raw["kanizsa"]
    rng = random.Random(seed)
    soas = list(p["soa_ms"])
    reps = int(p["trials_per_soa_per_condition"])
    conditions = []
    for soa in soas:
        for contour in (True, False):
            conditions += [{"soa_ms": soa, "contour": contour} for _ in range(reps)]
    conditions = shuffled(conditions, seed)

    show_text(win, "Kanizsa masking task\n\n中央に見えない四角形が感じられたら ←、なければ →\n\nSpaceで開始")
    rows = []
    for trial, cond in enumerate(conditions, start=1):
        show_fixation(win, cfg.raw.get("fixation_s", 0.5))
        target = _inducers(win, cond["contour"], rng)
        mask = _checker_mask(win, rng)
        present_frames(win, lambda: [s.draw() for s in target], int(p["target_frames"]))
        # The published paradigm varies the blank target-to-mask interval. We store both requested ms and realized frame count.
        blank_n = frames_from_ms(float(cond["soa_ms"]), cfg.monitor_hz)
        blank_frames(win, blank_n)
        present_frames(win, lambda: [s.draw() for s in mask], int(p["mask_frames"]))
        key, rt = collect_response(win, "見えない四角形は？   ← あり    → なし", ["left", "right"])
        correct_key = "left" if cond["contour"] else "right"
        rows.append({
            "task": "kanizsa",
            "trial": trial,
            "contour": int(cond["contour"]),
            "soa_ms_requested": float(cond["soa_ms"]),
            "blank_frames_realized": blank_n,
            "blank_ms_realized": 1000.0 * blank_n / cfg.monitor_hz,
            "response": key,
            "correct": int(key == correct_key),
            "rt_s": rt,
        })
        core.wait(float(cfg.raw.get("iti_s", 0.5)))
    path = save_rows(rows, output_dir, "kanizsa", cfg)
    show_text(win, f"終了しました。\n保存: {path}\n\nSpace")
    return rows, path
