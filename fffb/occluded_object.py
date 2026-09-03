from __future__ import annotations

import random
from pathlib import Path

from psychopy import core, visual

from .common import ExperimentConfig, blank_frames, collect_response, present_frames, save_rows, show_fixation, show_text, shuffled


DEMO_CATEGORIES = ["circle", "square", "triangle", "diamond"]
KEYS = ["1", "2", "3", "4"]


def _demo_object(win, category: str):
    if category == "circle":
        return visual.Circle(win, radius=0.16, fillColor="white", lineColor="white")
    if category == "square":
        return visual.Rect(win, width=0.3, height=0.3, fillColor="white", lineColor="white")
    if category == "triangle":
        return visual.Polygon(win, edges=3, radius=0.19, ori=0, fillColor="white", lineColor="white")
    return visual.Rect(win, width=0.24, height=0.24, ori=45, fillColor="white", lineColor="white")


def _external_catalog(root: str | Path):
    root = Path(root)
    catalog = {}
    if not root.exists():
        return catalog
    for category_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        files = [p for p in category_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}]
        if files:
            catalog[category_dir.name] = files
    return catalog


def _occluders(win, level: float, rng: random.Random):
    stims = []
    if level <= 0:
        return stims
    n = max(1, int(round(level * 10)))
    for _ in range(n):
        w = rng.uniform(0.06, 0.14)
        h = rng.uniform(0.06, 0.14)
        x = rng.uniform(-0.16, 0.16)
        y = rng.uniform(-0.16, 0.16)
        stims.append(visual.Rect(win, width=w, height=h, pos=(x, y), fillColor=win.color, lineColor=win.color))
    return stims


def _noise_mask(win, rng: random.Random, n=45):
    stims = []
    for _ in range(n):
        stims.append(visual.Rect(
            win,
            width=rng.uniform(0.02, 0.09),
            height=rng.uniform(0.02, 0.09),
            pos=(rng.uniform(-0.28, 0.28), rng.uniform(-0.28, 0.28)),
            ori=rng.uniform(0, 180),
            fillColor=rng.choice(["white", "gray", "black"]),
            lineColor=None,
        ))
    return stims


def run(win, cfg: ExperimentConfig, output_dir: str = "data", seed: int = 3):
    p = cfg.raw["occluded_object"]
    rng = random.Random(seed)
    use_external = bool(p.get("use_external_images", False))
    catalog = _external_catalog("stimuli/objects") if use_external else {}
    categories = list(catalog.keys())[:4] if len(catalog) >= 4 else DEMO_CATEGORIES
    using_demo = categories == DEMO_CATEGORIES

    conditions = []
    for occ in p["occlusion_levels"]:
        for masked in p["mask_conditions"]:
            for _ in range(int(p["trials_per_cell"])):
                conditions.append({"occlusion": float(occ), "masked": bool(masked)})
    conditions = shuffled(conditions, seed)

    mapping = "   ".join(f"{k}: {c}" for k, c in zip(KEYS, categories))
    show_text(win, f"Occluded object task\n\n物体カテゴリーを選択してください。\n{mapping}\n\nSpaceで開始")
    rows = []
    for trial, cond in enumerate(conditions, start=1):
        category = rng.choice(categories)
        show_fixation(win, cfg.raw.get("fixation_s", 0.5))
        if using_demo:
            obj = _demo_object(win, category)
            source = "procedural-demo"
        else:
            image_path = rng.choice(catalog[category])
            obj = visual.ImageStim(win, image=str(image_path), size=(0.38, 0.38))
            source = str(image_path)
        occs = _occluders(win, cond["occlusion"], rng)
        mask = _noise_mask(win, rng)

        def draw_target():
            obj.draw()
            for s in occs:
                s.draw()

        present_frames(win, draw_target, int(p["target_frames"]))
        blank_frames(win, int(p["soa_frames"]))
        if cond["masked"]:
            present_frames(win, lambda: [s.draw() for s in mask], int(p["mask_frames"]))
        key, rt = collect_response(win, f"カテゴリー?   {mapping}", KEYS)
        correct_key = KEYS[categories.index(category)]
        rows.append({
            "task": "occluded_object",
            "trial": trial,
            "category": category,
            "source": source,
            "occlusion_level_nominal": cond["occlusion"],
            "masked": int(cond["masked"]),
            "response": key,
            "correct": int(key == correct_key),
            "rt_s": rt,
            "target_frames": int(p["target_frames"]),
            "soa_frames": int(p["soa_frames"]),
            "mask_frames": int(p["mask_frames"]) if cond["masked"] else 0,
        })
        core.wait(float(cfg.raw.get("iti_s", 0.5)))
    path = save_rows(rows, output_dir, "occluded-object", cfg)
    show_text(win, f"終了しました。\n保存: {path}\n\nSpace")
    return rows, path
