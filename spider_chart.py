from __future__ import annotations
import plotly.graph_objects as go
import pandas as pd


def make_spider_chart(domain_df: pd.DataFrame):
    categories = domain_df["Domain"].tolist()
    values = domain_df["Score"].tolist()
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values_closed, theta=categories_closed, fill="toself", name="SPIDER Score"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        title="DTI-SPIDER Plan Quality Scorecard"
    )
    return fig
