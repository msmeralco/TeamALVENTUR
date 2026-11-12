"""One Plotly look for every notebook, and the "Simulated data" label every chart carries.

Charts render as PNG so they show on GitHub. Set SILIP_PLOTLY_RENDERER=notebook for interactive
charts while exploring locally.
"""

from __future__ import annotations

import os

import plotly.graph_objects as go
import plotly.io as pio

# Categorical slots in fixed order (dataviz reference palette, light mode).
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQUENTIAL = ["#eaf2fc", "#9cc3ef", "#2a78d6", "#0f3f7a"]  # one hue, light to dark
DIVERGING = [[0, "#2a78d6"], [0.5, "#e6e5e1"], [1, "#e34948"]]  # blue, gray midpoint, red
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"

pio.templates["silip"] = go.layout.Template(
    layout=go.Layout(
        font={"family": "Inter, Arial, sans-serif", "size": 13, "color": INK},
        paper_bgcolor="#fcfcfb",
        plot_bgcolor="#fcfcfb",
        colorway=COLORS,
        xaxis={"gridcolor": GRID, "linecolor": MUTED, "zeroline": False},
        yaxis={"gridcolor": GRID, "linecolor": MUTED, "zeroline": False},
        legend={"orientation": "h", "y": -0.2},
        margin={"t": 80, "l": 70, "r": 30, "b": 70},
    )
)
pio.templates.default = "silip"
pio.renderers.default = os.environ.get("SILIP_PLOTLY_RENDERER", "png")
pio.defaults.default_width, pio.defaults.default_height = 900, 450


def label(fig: go.Figure, title: str, x: str | None = None, y: str | None = None) -> go.Figure:
    """Title, axis labels with units, and the "Simulated data" note every chart must carry."""
    fig.update_layout(title={"text": f"{title}<br><sup>Simulated data</sup>", "x": 0.01})
    if x is not None:
        fig.update_xaxes(title_text=x)
    if y is not None:
        fig.update_yaxes(title_text=y)
    return fig
