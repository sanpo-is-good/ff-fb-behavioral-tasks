from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.stats import norm


def dprime_binary(df: pd.DataFrame, signal_col: str) -> float:
    signal = df[df[signal_col] == 1]
    noise = df[df[signal_col] == 0]
    if len(signal) == 0 or len(noise) == 0:
        return float("nan")
    # Loglinear correction prevents infinite z scores.
    hits = float(signal["correct"].sum())
    fas = float((1 - noise["correct"]).sum())
    hit_rate = (hits + 0.5) / (len(signal) + 1.0)
    fa_rate = (fas + 0.5) / (len(noise) + 1.0)
    return float(norm.ppf(hit_rate) - norm.ppf(fa_rate))


def _logistic(x, lower, upper, x0, scale):
    return lower + (upper - lower) / (1.0 + np.exp(-(x - x0) / scale))


def kanizsa_threshold(df: pd.DataFrame, criterion: float = 0.75) -> dict:
    grouped = df.groupby("soa_ms_requested", as_index=False)["correct"].mean().sort_values("soa_ms_requested")
    x = grouped["soa_ms_requested"].to_numpy(float)
    y = grouped["correct"].to_numpy(float)
    if len(x) < 4:
        return {"threshold_ms": float("nan"), "fit_ok": False}
    p0 = [max(0.45, y.min()), min(1.0, y.max()), np.median(x), max(10.0, np.std(x))]
    try:
        popt, _ = curve_fit(_logistic, x, y, p0=p0, maxfev=20000,
                            bounds=([0.0, 0.55, x.min()-100, 1.0], [0.8, 1.0, x.max()+100, 500.0]))
        lower, upper, x0, scale = popt
        if not (lower < criterion < upper):
            threshold = float("nan")
        else:
            threshold = x0 + scale * math.log((criterion - lower) / (upper - criterion))
        return {"threshold_ms": float(threshold), "fit_ok": True,
                "lower": float(lower), "upper": float(upper), "x0": float(x0), "scale": float(scale)}
    except Exception:
        return {"threshold_ms": float("nan"), "fit_ok": False}


def summarize_csv(path: str | Path) -> dict:
    df = pd.read_csv(path)
    task = str(df["task"].iloc[0])
    out = {"task": task, "n_trials": int(len(df)), "accuracy": float(df["correct"].mean()), "median_rt_s": float(df["rt_s"].median())}
    if task == "figure_ground":
        out["dprime"] = dprime_binary(df, "figure_present")
    elif task == "kanizsa":
        out["dprime"] = dprime_binary(df, "contour")
        out.update(kanizsa_threshold(df))
        out["accuracy_by_soa"] = df.groupby("soa_ms_requested")["correct"].mean().to_dict()
    elif task == "occluded_object":
        out["accuracy_by_occlusion_mask"] = (
            df.groupby(["occlusion_level_nominal", "masked"])["correct"].mean().to_dict()
        )
    return out
