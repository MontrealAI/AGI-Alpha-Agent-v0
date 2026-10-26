# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1]
(root / "figures").mkdir(parents=True, exist_ok=True)
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": "#312646",
        "text.color": "#312646",
        "xtick.color": "#544b61",
        "ytick.color": "#544b61",
        "pdf.fonttype": 42,
    }
)
x = np.linspace(0, 180, 181)
fig, ax = plt.subplots(figsize=(7.1, 3.45), constrained_layout=True)
ax.plot(x, x * 65.38 / 60, color="#6b3db8", lw=2.7, label="Developer wage: US$65.38/hour")
ax.plot(x, x * 50.14 / 60, color="#23998d", lw=2.7, label="QA wage: US$50.14/hour")
ax.axhline(99, color="#b16b1a", lw=1.4, ls="--", label="US$99 price hypothesis")
for wage, color in [(65.38, "#6b3db8"), (50.14, "#23998d")]:
    m = 99 * 60 / wage
    ax.scatter([m], [99], color=color, s=32, zorder=5)
    ax.annotate(f"{m:.1f} min", (m, 99), xytext=(m, 80), ha="center", color=color, fontsize=10)
ax.set(
    xlim=(0, 180),
    ylim=(0, 205),
    xlabel="Net competent-human work avoided (minutes)",
    ylabel="Maximum equal-cost price (US$)",
)
ax.grid(axis="y", alpha=0.15)
ax.legend(loc="upper left", frameon=False, fontsize=9)
fig.savefig(root / "figures/buyer_thresholds.pdf")
fig.savefig(root / "figures/buyer_thresholds.png", dpi=180)
plt.close(fig)
