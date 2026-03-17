from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHARTS_DIR = Path("storage/charts")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


METRICS_INFO: dict[str, dict[str, Any]] = {
    "LCP": {
        "full_name": "Largest Contentful Paint",
        "description": "Время загрузки основного контента",
        "unit": "секунды",
        "good": 2.5,
        "poor": 4.0,
        "format": "{:.1f} с",
    },
    "FCP": {
        "full_name": "First Contentful Paint",
        "description": "Время первого появления контента",
        "unit": "секунды",
        "good": 1.8,
        "poor": 3.0,
        "format": "{:.1f} с",
    },
    "CLS": {
        "full_name": "Cumulative Layout Shift",
        "description": "Визуальная стабильность",
        "unit": "коэффициент",
        "good": 0.1,
        "poor": 0.25,
        "format": "{:.3f}",
    },
    "TBT": {
        "full_name": "Total Blocking Time",
        "description": "Время блокировки основного потока",
        "unit": "миллисекунды",
        "good": 200,
        "poor": 600,
        "format": "{:.0f} мс",
    },
    "SpeedIndex": {
        "full_name": "Speed Index",
        "description": "Скорость отображения контента",
        "unit": "секунды",
        "good": 3.4,
        "poor": 5.8,
        "format": "{:.1f} с",
    },
}

_STATUS_COLORS = {
    "good": "#4CAF50",
    "needs-improvement": "#FFC107",
    "poor": "#F44336",
}


def _metric_status(metric_name: str, value: float) -> str:
    info = METRICS_INFO[metric_name]
    if value <= info["good"]:
        return "good"
    if value <= info["poor"]:
        return "needs-improvement"
    return "poor"


def _extract_metrics_from_psi(
    psi_data: dict[str, Any],
) -> tuple[dict[str, float], float]:
    lighthouse = psi_data.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    performance = categories.get("performance", {})
    score = float(performance.get("score", 0) or 0) * 100

    audits = lighthouse.get("audits", {})

    def _parse_display_value(display_value: str) -> float:
        normalized = display_value.replace(",", ".").replace("\xa0", " ").strip().lower()
        match = re.search(r"(\d+(?:\.\d+)?)", normalized)
        if not match:
            return 0.0

        raw_value = float(match.group(1))
        if "ms" in normalized:
            return raw_value
        if "s" in normalized:
            return raw_value * 1000
        return raw_value

    def numeric(audit_id: str) -> float:
        audit = audits.get(audit_id, {})

        numeric_value = audit.get("numericValue")
        if numeric_value is not None:
            return float(numeric_value or 0)

        if audit_id == "cumulative-layout-shift":
            display_value = str(audit.get("displayValue", ""))
            match = re.search(r"(\d+(?:[\.,]\d+)?)", display_value)
            if match:
                return float(match.group(1).replace(",", "."))
            return 0.0

        display_value = str(audit.get("displayValue", ""))
        return _parse_display_value(display_value)

    metrics = {
        "LCP": numeric("largest-contentful-paint") / 1000,
        "FCP": numeric("first-contentful-paint") / 1000,
        "CLS": numeric("cumulative-layout-shift"),
        "TBT": numeric("total-blocking-time"),
        "SpeedIndex": numeric("speed-index") / 1000,
    }
    return metrics, score


def _save_chart(fig: Any, filename_prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = CHARTS_DIR / f"{filename_prefix}_{timestamp}.png"
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _create_individual_metric_chart(metric_name: str, value: float) -> Any:
    info = METRICS_INFO[metric_name]
    status = _metric_status(metric_name, value)

    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    max_value = max(value, float(info["poor"]) * 1.5)

    ax.barh([0], [max_value], color="#E0E0E0", alpha=0.3, height=0.3)
    ax.axvline(
        x=info["good"],
        color="#4CAF50",
        linestyle="--",
        linewidth=2,
        alpha=0.8,
        label=f"Хорошо (≤{info['good']})",
    )
    ax.axvline(
        x=info["poor"],
        color="#F44336",
        linestyle="--",
        linewidth=2,
        alpha=0.8,
        label=f"Плохо (≥{info['poor']})",
    )

    ax.barh([0], [value], color=_STATUS_COLORS[status], height=0.3, alpha=0.8)
    if value > max_value * 0.7:
        ax.text(
            value - max_value * 0.05,
            0,
            info["format"].format(value),
            ha="right",
            va="center",
            fontweight="bold",
            color="white",
        )
    else:
        ax.text(
            value + max_value * 0.02,
            0,
            info["format"].format(value),
            ha="left",
            va="center",
            fontweight="bold",
            color="black",
        )

    ax.set_xlim(0, max_value)
    ax.set_yticks([])
    ax.set_xlabel(f"Значение ({info['unit']})")
    ax.set_title(f"{metric_name}: {info['full_name']}", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right")
    ax.grid(axis="x", alpha=0.3)
    ax.text(
        0.02,
        0.95,
        info["description"],
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
    )
    plt.tight_layout()
    return fig


def _create_summary_chart(metrics: dict[str, float], score: float) -> Any:
    metric_names = list(metrics.keys())
    fig, axes = plt.subplots(6, 1, figsize=(10, 14))

    for idx, metric_name in enumerate(metric_names):
        value = metrics[metric_name]
        info = METRICS_INFO[metric_name]
        status = _metric_status(metric_name, value)
        ax = axes[idx]
        max_value = max(value, float(info["poor"]) * 1.5)

        ax.barh([0], [max_value], color="#E0E0E0", alpha=0.3, height=0.4)
        ax.axvline(
            x=info["good"], color="#4CAF50", linestyle="--", linewidth=2, alpha=0.8
        )
        ax.axvline(
            x=info["poor"], color="#F44336", linestyle="--", linewidth=2, alpha=0.8
        )
        ax.barh([0], [value], color=_STATUS_COLORS[status], height=0.4, alpha=0.8)

        if value > max_value * 0.7:
            ax.text(
                value - max_value * 0.05,
                0,
                info["format"].format(value),
                ha="right",
                va="center",
                fontweight="bold",
                color="white",
            )
        else:
            ax.text(
                value + max_value * 0.02,
                0,
                info["format"].format(value),
                ha="left",
                va="center",
                fontweight="bold",
                color="black",
            )

        ax.set_xlim(0, max_value)
        ax.set_yticks([])
        ax.set_ylabel(metric_name, fontweight="bold")
        ax.grid(axis="x", alpha=0.3)

    ax_score = axes[-1]
    ax_score.barh(
        ["Performance Score"], [score], color="#2196F3", alpha=0.8, height=0.4
    )
    ax_score.set_xlim(0, 100)
    if score > 50:
        ax_score.text(
            score / 2,
            0,
            f"{score:.1f}",
            ha="center",
            va="center",
            fontweight="bold",
            color="white",
        )
    else:
        ax_score.text(
            score + 5, 0, f"{score:.1f}", ha="left", va="center", fontweight="bold"
        )
    ax_score.set_yticks([])
    ax_score.set_xlabel("Оценка производительности", fontweight="bold")
    ax_score.grid(axis="x", alpha=0.3)

    fig.suptitle("Core Web Vitals Анализ", fontsize=16, fontweight="bold", y=0.98)
    plt.tight_layout()
    return fig


def generate_psi_charts(psi_data: dict[str, Any]) -> dict[str, str]:
    metrics, score = _extract_metrics_from_psi(psi_data)
    chart_paths: dict[str, str] = {}

    for metric_name, value in metrics.items():
        fig = _create_individual_metric_chart(metric_name, value)
        chart_paths[f"{metric_name.lower()}_chart"] = _save_chart(
            fig, f"{metric_name.lower()}_chart"
        )

    summary_fig = _create_summary_chart(metrics, score)
    chart_paths["summary_chart"] = _save_chart(summary_fig, "summary_chart")
    return chart_paths