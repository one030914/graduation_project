import io
import numpy as np
import matplotlib.pyplot as plt

EMOTION_ORDER = [
    "Joy",
    "Angry",
    "Sad",
    "Surprised",
    "Disgusted",
    "Neutral",
]

def build_emotion_radar_chart(emotions: dict[str, int]) -> io.BytesIO:
    # 固定順序，避免每次軸順序不同
    labels = EMOTION_ORDER
    values = [int(emotions.get(label, 0)) for label in labels]

    total = sum(values) or 1
    values = [v / total for v in values]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()

    # 雷達圖要閉合
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    color_line = "#1C4D8D"
    color_fill = "#4988C4"
    color_label = "#757575"
    color_grid = "#ababab"

    ax.plot(angles, values, linewidth=2.0, color=color_line)
    ax.fill(angles, values, alpha=0.15, color=color_fill)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12, color=color_label)
    ax.tick_params(axis="x", pad=18)

    # 依照最大占比自動縮放半徑上限，避免「平均分布」時看起來太扁
    # - 上限 = max_ratio * padding，並設下限避免過度放大
    max_ratio = max(values[:-1]) if values else 0.0
    rmax = min(1.0, max(0.3, max_ratio * 1.25))

    ticks = [rmax * t for t in (0.2, 0.4, 0.6, 0.8, 1.0)]
    ax.set_yticks(ticks)
    ax.set_yticklabels(
        [f"{int(round(t * 100))}%" for t in ticks],
        fontsize=10,
        color=color_label,
    )
    ax.set_ylim(0, rmax)

    # 網格線與脊線樣式
    ax.grid(color=color_grid, linestyle="-", linewidth=0.8)
    ax.spines["polar"].set_color(color_grid)
    ax.spines["polar"].set_linewidth(1.0)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf