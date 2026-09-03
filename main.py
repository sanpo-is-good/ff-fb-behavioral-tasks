from __future__ import annotations

import argparse

from fffb.common import load_config, make_window, show_text
from fffb.figure_ground import run as run_figure_ground
from fffb.figure_ground_poltoratski import run as run_figure_ground_poltoratski
from fffb.kanizsa import run as run_kanizsa
from fffb.occluded_object import run as run_occluded_object


def main():
    parser = argparse.ArgumentParser(description="Behavioral FF/FB proxy tasks in PsychoPy")
    parser.add_argument(
        "task",
        choices=["figure-ground", "figure-ground-poltoratski", "kanizsa", "occluded-object", "all"],
    )
    parser.add_argument("--config", default="configs/default.json")
    parser.add_argument("--output", default="data")
    args = parser.parse_args()

    cfg = load_config(args.config)
    win = make_window(cfg)
    try:
        if args.task in ("figure-ground", "all"):
            run_figure_ground(win, cfg, args.output)
        if args.task == "figure-ground-poltoratski":
            run_figure_ground_poltoratski(win, cfg, args.output)
        if args.task in ("kanizsa", "all"):
            run_kanizsa(win, cfg, args.output)
        if args.task in ("occluded-object", "all"):
            run_occluded_object(win, cfg, args.output)
        if args.task == "all":
            show_text(win, "全課題終了しました。\nSpaceで閉じる")
    finally:
        win.close()


if __name__ == "__main__":
    main()
