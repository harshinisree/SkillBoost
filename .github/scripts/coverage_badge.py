"""Turn pytest-cov's coverage.json into a shields.io badge description (T4-8).

Usage: python coverage_badge.py coverage.json badge.json
The output is read by https://img.shields.io/endpoint, which draws the badge.
"""
import json
import sys


def badge(percent: float) -> dict[str, object]:
    if percent >= 90:
        color = "brightgreen"
    elif percent >= 80:
        color = "green"
    elif percent >= 70:
        color = "yellow"
    else:
        color = "red"
    return {"schemaVersion": 1, "label": "coverage", "message": f"{percent:.0f}%", "color": color}


def main(source: str, target: str) -> None:
    with open(source) as f:
        percent = json.load(f)["totals"]["percent_covered"]
    with open(target, "w") as f:
        json.dump(badge(percent), f)
    print(f"coverage {percent:.1f}%")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
