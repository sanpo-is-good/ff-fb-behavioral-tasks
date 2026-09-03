from __future__ import annotations

import math
import random

from psychopy import core, visual

from .common import ExperimentConfig, collect_response, present_frames, save_rows, show_fixation, show_text, shuffled


def _segment_positions(grid_n: int, extent: float = 0.62):
    step = extent / (grid_n - 1)
    start = -extent / 2
    for iy in range(grid_n):
        for ix in range(grid_n):
            yield start + ix * step, start + iy * step


def _make_texture(win, grid_n: int, figure_present: bool, figure_fraction: float, rng: random.Random):
    extent = 0.62
    base_ori = rng.choice([35, 55, 125, 145])
    figure_ori = (base_ori + 90) % 180
    fig_half = extent * figure_fraction / 2
    seg_len = extent / grid_n * 0.65
    lines = []
    for x, y in _segment_positions(grid_n, extent):
        in_fig = abs(x) <= fig_half and abs(y) <= fig_half
        ori = figure_ori if (figure_present and in_fig) else base_ori
        # Small jitter avoids overly regular moire-like patterns.
        ori += rng.uniform(-5, 5)
        theta = math.radians(ori)
        dx = math.cos(theta) * seg_len / 2
        dy = math.sin(theta) * seg_len / 2
        lines.append(visual.Line(win, start=(x - dx, y - dy), end=(x + dx, y + dy), lineColor="white", lineWidth=1.2))
    return lines


def _make_mask(win, grid_n: int, rng: random.Random):
    extent = 0.62
    seg_len = extent / grid_n * 0.72
    lines = []
    for x, y in _segment_positions(grid_n, extent):
        ori = rng.uniform(0, 180)
        theta = math.radians(ori)
        dx = math.cos(theta) * seg_len / 2
        dy = math.sin(theta) * seg_len / 2
        lines.append(visual.Line(win, start=(x - dx, y - dy), end=(x + dx, y + dy), lineColor="white", lineWidth=1.2))
    return lines


def run(win, cfg: ExperimentConfig, output_dir: str = "data", seed: int = 1):
    p = cfg.raw["figure_ground"]
    rng = random.Random(seed)
    n = int(p["trials"])
    conditions = [{"figure_present": bool(i % 2)} for i in range(n)]
    conditions = shuffled(conditions, seed)

    show_text(win, "Figure-ground task\n\n中央に向きの違う四角い領域があったら ←、なければ →\n\nSpaceで開始")
    rows = []
    for trial, cond in enumerate(conditions, start=1):
        show_fixation(win, cfg.raw.get("fixation_s", 0.5))
        target = _make_texture(win, int(p["grid_n"]), cond["figure_present"], float(p["figure_fraction"]), rng)
        mask = _make_mask(win, int(p["grid_n"]), rng)
        present_frames(win, lambda: [s.draw() for s in target], int(p["target_frames"]))
        present_frames(win, lambda: [s.draw() for s in mask], int(p["mask_frames"]))
        key, rt = collect_response(win, "四角い領域は？   ← あり    → なし", ["left", "right"])
        correct_key = "left" if cond["figure_present"] else "right"
        rows.append({
            "task": "figure_ground",
            "trial": trial,
            "figure_present": int(cond["figure_present"]),
            "response": key,
            "correct": int(key == correct_key),
            "rt_s": rt,
            "target_frames": int(p["target_frames"]),
            "mask_frames": int(p["mask_frames"]),
        })
        core.wait(float(cfg.raw.get("iti_s", 0.5)))
    path = save_rows(rows, output_dir, "figure-ground", cfg)
    show_text(win, f"終了しました。\n保存: {path}\n\nSpace")
    return rows, path
