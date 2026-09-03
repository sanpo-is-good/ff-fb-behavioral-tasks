from __future__ import annotations

import itertools
import math
import random

import numpy as np
from psychopy import core, event, visual

from .common import ExperimentConfig, save_rows, show_text


def _orientation_difference(angle_deg: np.ndarray, target_deg: float) -> np.ndarray:
    return np.abs(((angle_deg - target_deg + 90.0) % 180.0) - 90.0)


def _oriented_bandpass_noise(
    n_px: int,
    size_deg: float,
    orientation_deg: float,
    orientation_halfwidth_deg: float,
    low_cpd: float,
    high_cpd: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate Fourier-filtered oriented noise similar to the MATLAB implementation.

    The image is normalized to PsychoPy's [-1, 1] image range.
    """
    white = rng.random((n_px, n_px), dtype=np.float32) - 0.5
    spectrum = np.fft.fftshift(np.fft.fft2(white))

    sample_deg = size_deg / n_px
    f = np.fft.fftshift(np.fft.fftfreq(n_px, d=sample_deg))
    fx, fy = np.meshgrid(f, f)
    radial = np.sqrt(fx * fx + fy * fy)
    angle = (np.degrees(np.arctan2(fy, fx)) + 180.0) % 180.0

    radial_mask = (radial >= low_cpd) & (radial <= high_cpd)
    orient_mask = _orientation_difference(angle, orientation_deg) <= orientation_halfwidth_deg
    filt = radial_mask & orient_mask

    filtered = np.real(np.fft.ifft2(np.fft.ifftshift(spectrum * filt)))
    filtered -= filtered.mean()
    peak = np.max(np.abs(filtered))
    if peak > 0:
        filtered /= peak
    return filtered.astype(np.float32)


def _build_target_schedule(
    n_intervals: int,
    probability: float,
    buffer_intervals: int,
    min_separation_intervals: int,
    rng: random.Random,
) -> list[bool]:
    """Approximate the original MATLAB target scheduler.

    The original code draws the number of targets from Bernoulli intervals (p=.05),
    requires >=1 target, excludes early/late intervals, and prevents nearby targets.
    """
    desired = sum(rng.random() < probability for _ in range(n_intervals))
    desired = max(1, desired)
    schedule = [False] * n_intervals
    candidates = list(range(buffer_intervals, max(buffer_intervals, n_intervals - buffer_intervals)))
    rng.shuffle(candidates)
    for idx in candidates:
        lo = max(0, idx - min_separation_intervals)
        hi = min(n_intervals, idx + min_separation_intervals + 1)
        if not any(schedule[lo:hi]):
            schedule[idx] = True
            if sum(schedule) >= desired:
                break
    return schedule


def _draw_fixation(win, fixation, cue_left=None, cue_right=None):
    fixation.draw()
    if cue_left is not None:
        cue_left.draw()
    if cue_right is not None:
        cue_right.draw()


def run(win, cfg: ExperimentConfig, output_dir: str = "data", seed: int = 1):
    p = cfg.raw["figure_ground_poltoratski"]
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    # Published Experiment 1 factors: surround orientation x attended side x incongruent side.
    orientations = [float(v) for v in p.get("orientations_deg", [45, 135])]
    sides = ["left", "right"]
    conditions = [
        {"surround_orientation": ori, "attend_side": att, "incongruent_side": inc}
        for ori, att, inc in itertools.product(orientations, sides, sides)
    ]
    reps = int(p.get("repetitions_per_condition", 1))
    blocks = conditions * reps
    rng.shuffle(blocks)

    block_s = float(p.get("block_length_s", 16.0))
    rest_s = float(p.get("rest_s", 16.0))
    initial_fix_s = float(p.get("initial_fixation_s", 16.0))
    final_fix_s = float(p.get("final_fixation_s", 16.0))
    update_s = float(p.get("noise_update_s", 0.2))
    cue_s = float(p.get("cue_before_s", 1.0))
    n_intervals = int(round(block_s / update_s))

    figure_diam = float(p.get("figure_diameter_deg", 4.0))
    eccentricity = float(p.get("figure_center_eccentricity_deg", 3.0))
    gap_deg = float(p.get("gap_deg", 0.15))
    surround_size = float(p.get("surround_size_deg", 18.0))
    noise_px = int(p.get("noise_size_px", 256))
    ori_halfwidth = float(p.get("orientation_halfwidth_deg", 10.0))
    low_cpd = float(p.get("low_cpd", 0.5))
    high_cpd = float(p.get("high_cpd", 4.0))
    target_low_cpd = float(p.get("target_low_cpd", 1.5))
    target_high_cpd = float(p.get("target_high_cpd", 12.0))
    target_probability = float(p.get("target_probability_per_interval", 0.05))
    buffer_intervals = int(p.get("target_buffer_intervals", 4))
    min_sep = int(p.get("target_min_separation_intervals", 2))
    response_window_s = float(p.get("response_window_s", 0.8))

    bg = cfg.raw.get("background", [0.0, 0.0, 0.0])
    surround_stim = visual.ImageStim(win, image=np.zeros((noise_px, noise_px)), size=(surround_size, surround_size), units="deg", interpolate=True)
    left_stim = visual.ImageStim(win, image=np.zeros((noise_px, noise_px)), size=(figure_diam, figure_diam), pos=(-eccentricity, 0), mask="circle", units="deg", interpolate=True)
    right_stim = visual.ImageStim(win, image=np.zeros((noise_px, noise_px)), size=(figure_diam, figure_diam), pos=(eccentricity, 0), mask="circle", units="deg", interpolate=True)

    # Filled background circles create the gray gap outside each figure aperture.
    left_gap = visual.Circle(win, radius=figure_diam / 2 + gap_deg, pos=(-eccentricity, 0), fillColor=bg, lineColor=bg, units="deg")
    right_gap = visual.Circle(win, radius=figure_diam / 2 + gap_deg, pos=(eccentricity, 0), fillColor=bg, lineColor=bg, units="deg")
    fixation = visual.Circle(win, radius=float(p.get("fixation_diameter_deg", 0.15)) / 2, fillColor="black", lineColor="white", units="deg")

    cue_offset = float(p.get("cue_offset_deg", 0.35))
    cue_radius = float(p.get("cue_diameter_deg", 0.10)) / 2

    cue_color_name = str(p.get("attended_cue_color", "white")).lower()
    attended_color = "white" if cue_color_name == "white" else "black"
    unattended_color = "black" if attended_color == "white" else "white"

    show_text(
        win,
        "Poltoratski figure-ground replication (Exp. 1)\n\n"
        f"{cue_color_name.upper()} の点が示す側を注視し、\n"
        "その図形の空間周波数が一瞬細かくなったら SPACE を押してください。\n\n"
        "Spaceで開始",
    )

    rows = []
    # Initial fixation
    fixation.draw(); win.flip(); core.wait(initial_fix_s)

    for block_idx, cond in enumerate(blocks, start=1):
        surround_ori = cond["surround_orientation"]
        incong_ori = orientations[1] if math.isclose(surround_ori, orientations[0]) else orientations[0]
        left_ori = incong_ori if cond["incongruent_side"] == "left" else surround_ori
        right_ori = incong_ori if cond["incongruent_side"] == "right" else surround_ori

        left_targets = _build_target_schedule(n_intervals, target_probability, buffer_intervals, min_sep, rng)
        right_targets = _build_target_schedule(n_intervals, target_probability, buffer_intervals, min_sep, rng)

        # Pre-generate all textures for this block so Fourier filtering does not disturb 200-ms timing.
        textures = []
        for i in range(n_intervals):
            surround_img = _oriented_bandpass_noise(noise_px, surround_size, surround_ori, ori_halfwidth, low_cpd, high_cpd, np_rng)
            left_img = _oriented_bandpass_noise(
                noise_px, figure_diam, left_ori, ori_halfwidth,
                target_low_cpd if left_targets[i] else low_cpd,
                target_high_cpd if left_targets[i] else high_cpd,
                np_rng,
            )
            right_img = _oriented_bandpass_noise(
                noise_px, figure_diam, right_ori, ori_halfwidth,
                target_low_cpd if right_targets[i] else low_cpd,
                target_high_cpd if right_targets[i] else high_cpd,
                np_rng,
            )
            textures.append((surround_img, left_img, right_img))

        # 1 s cue preceding the stimulus block.
        if cond["attend_side"] == "left":
            left_color, right_color = attended_color, unattended_color
        else:
            left_color, right_color = unattended_color, attended_color
        cue_left = visual.Circle(win, radius=cue_radius, pos=(-cue_offset, 0), fillColor=left_color, lineColor=left_color, units="deg")
        cue_right = visual.Circle(win, radius=cue_radius, pos=(cue_offset, 0), fillColor=right_color, lineColor=right_color, units="deg")
        _draw_fixation(win, fixation, cue_left, cue_right); win.flip(); core.wait(cue_s)

        event.clearEvents()
        block_clock = core.Clock()
        attended_targets = left_targets if cond["attend_side"] == "left" else right_targets
        target_onsets = [i * update_s for i, v in enumerate(attended_targets) if v]
        hit_targets: set[int] = set()
        false_alarms = 0
        responses = []

        for i, (surround_img, left_img, right_img) in enumerate(textures):
            # Poll responses that happened since the previous update.
            got = event.getKeys(keyList=["space", "escape"], timeStamped=block_clock)
            for key, t in got:
                if key == "escape":
                    win.close(); core.quit()
                responses.append(float(t))
                eligible = [j for j, onset in enumerate(target_onsets) if j not in hit_targets and 0 <= t - onset <= response_window_s]
                if eligible:
                    hit_targets.add(eligible[-1])
                else:
                    false_alarms += 1

            surround_stim.setImage(surround_img)
            left_stim.setImage(left_img)
            right_stim.setImage(right_img)
            surround_stim.draw()
            left_gap.draw(); right_gap.draw()
            left_stim.draw(); right_stim.draw()
            _draw_fixation(win, fixation, cue_left, cue_right)
            target_time = i * update_s
            wait = target_time - block_clock.getTime()
            if wait > 0:
                core.wait(wait)
            win.flip()

        # Final response poll after the last displayed interval.
        core.wait(min(response_window_s, 0.8))
        got = event.getKeys(keyList=["space", "escape"], timeStamped=block_clock)
        for key, t in got:
            if key == "escape":
                win.close(); core.quit()
            responses.append(float(t))
            eligible = [j for j, onset in enumerate(target_onsets) if j not in hit_targets and 0 <= t - onset <= response_window_s]
            if eligible:
                hit_targets.add(eligible[-1])
            else:
                false_alarms += 1

        n_targets = len(target_onsets)
        hits = len(hit_targets)
        rows.append({
            "task": "figure_ground_poltoratski_expt1",
            "block": block_idx,
            "surround_orientation_deg": surround_ori,
            "attend_side": cond["attend_side"],
            "incongruent_side": cond["incongruent_side"],
            "left_orientation_deg": left_ori,
            "right_orientation_deg": right_ori,
            "attended_targets": n_targets,
            "hits": hits,
            "false_alarms": false_alarms,
            "hit_rate": hits / n_targets if n_targets else np.nan,
            "responses": len(responses),
            "figure_diameter_deg": figure_diam,
            "figure_eccentricity_deg": eccentricity,
            "gap_deg": gap_deg,
            "noise_low_cpd": low_cpd,
            "noise_high_cpd": high_cpd,
            "orientation_halfwidth_deg": ori_halfwidth,
            "noise_update_s": update_s,
            "block_length_s": block_s,
        })

        if block_idx < len(blocks):
            fixation.draw(); win.flip(); core.wait(rest_s)

    fixation.draw(); win.flip(); core.wait(final_fix_s)
    path = save_rows(rows, output_dir, "figure-ground-poltoratski", cfg)
    show_text(win, f"終了しました。\n保存: {path}\n\nSpace")
    return rows, path
