"""Plotly figures used by the Streamlit dashboard."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from .predictor import DurabilityPrediction


INK = "#102326"
MUTED = "#5D7072"
GRID = "#DDE8E6"
TEAL = "#087F82"
CYAN = "#32A9D6"
CORAL = "#C76052"
AMBER = "#B87916"
PAPER = "#FFFFFF"


def _base_layout(fig: go.Figure, *, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=28, b=12),
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font=dict(family="Inter, Aptos, Segoe UI, sans-serif", color=INK, size=13),
        hoverlabel=dict(bgcolor=INK, font_color="white", bordercolor=INK),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12),
        ),
    )
    return fig


def durability_curve(
    prediction: DurabilityPrediction,
    *,
    observed_followup: float | None = None,
) -> go.Figure:
    """Posterior survival and modeled endpoint probability over time."""

    t = prediction.times
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=t,
            y=prediction.survival_high * 100,
            mode="lines",
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=prediction.survival_low * 100,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(8,127,130,0.13)",
            name="89% credible interval",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=prediction.survival_median * 100,
            mode="lines",
            line=dict(color=TEAL, width=3),
            name="Freedom from modeled endpoint",
            hovertemplate="Year %{x:.1f}<br>Event-free %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=prediction.risk_median * 100,
            mode="lines",
            line=dict(color=CORAL, width=2.2, dash="dash"),
            name="Modeled endpoint probability",
            hovertemplate="Year %{x:.1f}<br>Endpoint probability %{y:.1f}%<extra></extra>",
        )
    )

    if observed_followup is not None and np.isfinite(observed_followup) and observed_followup > 0:
        fig.add_vline(
            x=float(observed_followup),
            line_width=1,
            line_dash="dot",
            line_color=MUTED,
            annotation_text="Observed follow-up",
            annotation_position="top right",
            annotation_font_color=MUTED,
            annotation_font_size=11,
        )

    fig.update_xaxes(
        title="Years since index implant",
        range=[0, float(t.max())],
        dtick=1,
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
    )
    fig.update_yaxes(
        title="Posterior probability",
        range=[0, 100],
        dtick=20,
        ticksuffix="%",
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
    )
    return _base_layout(fig, height=430)


def time_ratio_forest(prediction: DurabilityPrediction) -> go.Figure:
    """Patient-specific AFT factor decomposition on a time-ratio scale."""

    factors = prediction.factors
    labels = [factor.label for factor in factors]
    medians = np.array([factor.ratio.median for factor in factors], dtype=float)
    lows = np.array([factor.ratio.low for factor in factors], dtype=float)
    highs = np.array([factor.ratio.high for factor in factors], dtype=float)
    colors = [
        MUTED if not factor.applied else (TEAL if factor.ratio.median >= 1 else CORAL)
        for factor in factors
    ]

    fig = go.Figure(
        go.Scatter(
            x=medians,
            y=labels,
            mode="markers",
            marker=dict(size=11, color=colors, line=dict(color="white", width=1)),
            error_x=dict(
                type="data",
                symmetric=False,
                array=np.maximum(highs - medians, 0),
                arrayminus=np.maximum(medians - lows, 0),
                color=MUTED,
                thickness=1.5,
                width=6,
            ),
            customdata=np.stack([lows, highs], axis=-1),
            hovertemplate=(
                "%{y}<br>Time ratio %{x:.2f}x"
                "<br>89% CrI %{customdata[0]:.2f}–%{customdata[1]:.2f}x<extra></extra>"
            ),
        )
    )
    fig.add_vline(x=1.0, line_color=INK, line_width=1.2, line_dash="dash")
    fig.add_annotation(
        x=1.0,
        y=1.08,
        xref="x",
        yref="paper",
        text="Reference",
        showarrow=False,
        font=dict(color=MUTED, size=11),
    )
    fig.update_xaxes(
        title="Posterior time ratio (>1 = longer modeled durability)",
        type="log",
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
    )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return _base_layout(fig, height=305)


def validation_comparison(
    *,
    bayesian: float | None,
    corrected: float | None,
) -> go.Figure:
    values = [
        bayesian,
        corrected,
        0.5,
        0.5457392652595507,
        0.5077945065981192,
    ]
    labels = [
        "Primary, apparent",
        "Primary, optimism-corrected",
        "Valve-family Weibull",
        "Penalized Cox, corrected",
        "XGBoost AFT, corrected",
    ]
    cleaned = [float(v) if v is not None else np.nan for v in values]
    colors = [TEAL, CYAN, "#A7B6B5", "#7D9696", "#A7B6B5"]
    fig = go.Figure(
        go.Bar(
            x=cleaned,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{v:.3f}" if np.isfinite(v) else "n/a" for v in cleaned],
            textposition="outside",
            hovertemplate="%{y}<br>C-index %{x:.3f}<extra></extra>",
        )
    )
    fig.add_vline(x=0.5, line_color=MUTED, line_dash="dot", line_width=1)
    fig.update_xaxes(range=[0.4, 0.7], title="Harrell's C-index", gridcolor=GRID)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_layout(showlegend=False)
    return _base_layout(fig, height=310)
