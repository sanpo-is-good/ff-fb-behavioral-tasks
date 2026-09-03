from __future__ import annotations

import csv
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from psychopy import core, event, visual


@dataclass
class ExperimentConfig:
    raw: dict

    @property
    def participant(self) -> str:
        return str(self.raw.get("participant", "demo"))

    @property
    def session(self) -> str:
        return str(self.raw.get("session", "001"))

    @property
    def monitor_hz(self) -> float:
        return float(self.raw.get("monitor_hz", 60))


def load_config(path: str | Path) -> ExperimentConfig:
    with open(path, "r", encoding="utf-8") as f:
        return ExperimentConfig(json.load(f))


def make_window(cfg: ExperimentConfig) -> visual.Window:
    raw = cfg.raw
    win = visual.Window(
        size=raw.get("window_size", [1280, 720]),
        fullscr=bool(raw.get("full_screen", False)),
        color=raw.get("background", [-0.92, -0.92, -0.92]),
        units="height",
        allowGUI=not bool(raw.get("full_screen", False)),
        waitBlanking=True,
    )
    win.recordFrameIntervals = True
    return win


def frames_from_ms(ms: float, hz: float) -> int:
    return max(1, int(round((ms / 1000.0) * hz)))


def show_text(win: visual.Window, text: str, keys: Iterable[str] = ("space",)) -> str:
    stim = visual.TextStim(win, text=text, color="white", height=0.035, wrapWidth=1.35)
    stim.draw()
    win.flip()
    response = event.waitKeys(keyList=list(keys) + ["escape"])[0]
    if response == "escape":
        win.close()
        core.quit()
    return response


def show_fixation(win: visual.Window, duration_s: float = 0.5) -> None:
    fix = visual.TextStim(win, text="+", color="white", height=0.045)
    fix.draw()
    win.flip()
    core.wait(duration_s)


def present_frames(win: visual.Window, draw_fn: Callable[[], None], n_frames: int) -> None:
    for _ in range(max(0, int(n_frames))):
        draw_fn()
        win.flip()


def blank_frames(win: visual.Window, n_frames: int) -> None:
    for _ in range(max(0, int(n_frames))):
        win.flip()


def collect_response(win: visual.Window, prompt: str, keys: list[str]) -> tuple[str, float]:
    text = visual.TextStim(win, text=prompt, color="white", height=0.032, wrapWidth=1.4)
    text.draw()
    win.flip()
    event.clearEvents()
    clock = core.Clock()
    while True:
        got = event.getKeys(keyList=keys + ["escape"], timeStamped=clock)
        if got:
            key, rt = got[0]
            if key == "escape":
                win.close()
                core.quit()
            return key, float(rt)
        core.wait(0.001)


def shuffled(items: list[dict], seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    out = list(items)
    rng.shuffle(out)
    return out


def save_rows(rows: list[dict], output_dir: str | Path, task: str, cfg: ExperimentConfig) -> Path:
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = outdir / f"sub-{cfg.participant}_ses-{cfg.session}_{task}_{stamp}.csv"
    if not rows:
        return path
    columns = sorted({k for r in rows for k in r.keys()})
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path
