"""
KPI Card components for Studio21 Dashboard.
Provides reusable metric card functions using native Streamlit components.
"""

import streamlit as st
from typing import Optional


def render_kpi_card(
    title: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None
) -> None:
    """
    Render a KPI card using native Streamlit metric component.
    
    Args:
        title: Metric title/label
        value: Formatted metric value (already formatted as string)
        delta: Optional delta value (formatted as string)
        delta_color: Color scheme for delta - "normal", "inverse", or "off"
        help_text: Optional tooltip text explaining the metric
    """
    st.metric(
        label=title,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def render_kpi_grid(metrics: list[dict]) -> None:
    """
    Render a grid of KPI cards in equal-width columns.
    
    Args:
        metrics: List of metric dictionaries with keys:
            - title (str): Metric title
            - value (str): Formatted value
            - delta (Optional[str]): Delta value
            - delta_color (str): "normal", "inverse", or "off"
            - help_text (Optional[str]): Tooltip text
            
    Example:
        metrics = [
            {
                "title": "Receita Bruta",
                "value": "R$ 125.450,00",
                "delta": "+12,5%",
                "delta_color": "normal",
                "help_text": "Total de receitas no período"
            },
            # ... more metrics
        ]
        render_kpi_grid(metrics)
    """
    if not metrics:
        return
    
    # Create columns based on number of metrics
    cols = st.columns(len(metrics))
    
    # Render each metric in its column
    for col, metric in zip(cols, metrics):
        with col:
            render_kpi_card(
                title=metric.get("title", ""),
                value=metric.get("value", ""),
                delta=metric.get("delta"),
                delta_color=metric.get("delta_color", "normal"),
                help_text=metric.get("help_text")
            )


def render_section_header(title: str, subtitle: Optional[str] = None) -> None:
    """
    Render a section header using native Streamlit components.
    
    Args:
        title: Section title
        subtitle: Optional subtitle or description
    """
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
    st.markdown("---")
