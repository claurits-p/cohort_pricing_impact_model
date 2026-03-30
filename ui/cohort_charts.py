"""
Visualizations for the cohort pricing impact model.
"""
from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st

from ui.cohort_engine import CohortScenario

STD_COLOR = "#1B6AC9"
REV_COLOR = "#2ECC71"
MAR_COLOR = "#E67E22"
AI_COLOR = "#17A2B8"
DELTA_POS = "#27AE60"
DELTA_NEG = "#E74C3C"


def render_win_rate_history() -> None:
    """Historical win rate by funnel stage, displayed at the top of the report."""
    from data.win_rate_history import MONTHS, STAGES

    st.markdown("**Historical Win Rates by Funnel Stage**")

    fig = go.Figure()
    for stage_name, info in STAGES.items():
        fig.add_trace(go.Scatter(
            x=MONTHS,
            y=info["values"],
            mode="lines+markers+text",
            name=stage_name,
            line=dict(color=info["color"], width=2),
            marker=dict(size=5),
            text=[f"{v:.1f}%" for v in info["values"]],
            textposition="top center",
            textfont=dict(size=8, color=info["color"]),
        ))

    fig.update_layout(
        height=380,
        margin=dict(l=40, r=20, t=30, b=40),
        yaxis=dict(
            title="Win Rate %",
            range=[0, 100],
            ticksuffix="%",
            gridcolor="rgba(0,0,0,0.06)",
        ),
        xaxis=dict(tickangle=-45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        plot_bgcolor="white",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_break_even_chart(
    std: CohortScenario,
    ltv: CohortScenario,
    top: CohortScenario,
    ai: CohortScenario | None = None,
) -> None:
    """Cumulative margin over time with crossover points."""
    st.markdown("**Cumulative Margin Timeline**")

    years = [0, 1, 2, 3]

    def _cum_margins(scenario):
        cum = [0.0]
        running = 0.0
        for y in [1, 2, 3]:
            running += scenario.cohort_yearly[y].margin
            cum.append(running)
        return cum

    std_cum = _cum_margins(std)
    ltv_cum = _cum_margins(ltv)
    top_cum = _cum_margins(top)

    def _find_crossover(base, comp):
        for i in range(1, len(years)):
            diff = comp[i] - base[i]
            if diff >= 0:
                prev_diff = comp[i - 1] - base[i - 1]
                if prev_diff < 0:
                    frac = -prev_diff / (diff - prev_diff)
                    return years[i - 1] + frac
                return float(years[i])
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=std_cum, mode="lines+markers+text",
        name="Standard", line=dict(color=STD_COLOR, width=3),
        text=[""] + [f"${v:,.0f}" for v in std_cum[1:]],
        textposition="top left", textfont=dict(size=11),
    ))
    fig.add_trace(go.Scatter(
        x=years, y=ltv_cum, mode="lines+markers+text",
        name="Revenue Optimized", line=dict(color=REV_COLOR, width=3),
        text=[""] + [f"${v:,.0f}" for v in ltv_cum[1:]],
        textposition="top center", textfont=dict(size=11),
    ))
    fig.add_trace(go.Scatter(
        x=years, y=top_cum, mode="lines+markers+text",
        name="$ Margin Optimized", line=dict(color=MAR_COLOR, width=3),
        text=[""] + [f"${v:,.0f}" for v in top_cum[1:]],
        textposition="bottom center", textfont=dict(size=11),
    ))

    if ai is not None:
        ai_cum = _cum_margins(ai)
        fig.add_trace(go.Scatter(
            x=years, y=ai_cum, mode="lines+markers+text",
            name="AI Recommended", line=dict(color=AI_COLOR, width=3),
            text=[""] + [f"${v:,.0f}" for v in ai_cum[1:]],
            textposition="bottom left", textfont=dict(size=11),
        ))

    ltv_cross = _find_crossover(std_cum, ltv_cum)
    if ltv_cross is not None:
        label = f"Revenue break-even: Year {int(ltv_cross)}" if ltv_cross == int(ltv_cross) else f"Revenue break-even: ~Year {ltv_cross:.1f}"
        fig.add_vline(x=ltv_cross, line_dash="dash", line_color=REV_COLOR,
                      annotation_text=label, annotation_position="top right",
                      annotation_font_color=REV_COLOR)

    top_cross = _find_crossover(std_cum, top_cum)
    if top_cross is not None and top_cross != ltv_cross:
        label = f"$ Margin break-even: Year {int(top_cross)}" if top_cross == int(top_cross) else f"$ Margin break-even: ~Year {top_cross:.1f}"
        fig.add_vline(x=top_cross, line_dash="dash", line_color=MAR_COLOR,
                      annotation_text=label, annotation_position="bottom right",
                      annotation_font_color=MAR_COLOR)

    if ai is not None:
        ai_cross = _find_crossover(std_cum, ai_cum)
        if ai_cross is not None and ai_cross != ltv_cross and ai_cross != top_cross:
            label = f"AI break-even: Year {int(ai_cross)}" if ai_cross == int(ai_cross) else f"AI break-even: ~Year {ai_cross:.1f}"
            fig.add_vline(x=ai_cross, line_dash="dash", line_color=AI_COLOR,
                          annotation_text=label, annotation_position="top left",
                          annotation_font_color=AI_COLOR)

    fig.update_layout(
        xaxis_title="Year", yaxis_title="Cumulative Margin ($)",
        xaxis=dict(tickmode="array", tickvals=[0, 1, 2, 3], ticktext=["Year 0", "Year 1", "Year 2", "Year 3"]),
        yaxis=dict(tickformat="$,.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=40), height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_cumulative_revenue_chart(
    std: CohortScenario,
    ltv: CohortScenario,
    top: CohortScenario,
    ai: CohortScenario | None = None,
) -> None:
    """Cumulative revenue over time — mirrors the margin timeline."""
    st.markdown("**Cumulative Revenue Timeline**")

    years = [0, 1, 2, 3]

    def _cum_revenue(scenario):
        cum = [0.0]
        running = 0.0
        for y in [1, 2, 3]:
            running += scenario.cohort_yearly[y].total_revenue
            cum.append(running)
        return cum

    std_cum = _cum_revenue(std)
    ltv_cum = _cum_revenue(ltv)
    top_cum = _cum_revenue(top)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=std_cum, mode="lines+markers+text",
        name="Standard", line=dict(color=STD_COLOR, width=3),
        text=[""] + [f"${v:,.0f}" for v in std_cum[1:]],
        textposition="top left", textfont=dict(size=11),
    ))
    fig.add_trace(go.Scatter(
        x=years, y=ltv_cum, mode="lines+markers+text",
        name="Revenue Optimized", line=dict(color=REV_COLOR, width=3),
        text=[""] + [f"${v:,.0f}" for v in ltv_cum[1:]],
        textposition="top center", textfont=dict(size=11),
    ))
    fig.add_trace(go.Scatter(
        x=years, y=top_cum, mode="lines+markers+text",
        name="$ Margin Optimized", line=dict(color=MAR_COLOR, width=3),
        text=[""] + [f"${v:,.0f}" for v in top_cum[1:]],
        textposition="bottom center", textfont=dict(size=11),
    ))

    if ai is not None:
        ai_cum = _cum_revenue(ai)
        fig.add_trace(go.Scatter(
            x=years, y=ai_cum, mode="lines+markers+text",
            name="AI Recommended", line=dict(color=AI_COLOR, width=3),
            text=[""] + [f"${v:,.0f}" for v in ai_cum[1:]],
            textposition="bottom left", textfont=dict(size=11),
        ))

    fig.update_layout(
        xaxis_title="Year", yaxis_title="Cumulative Revenue ($)",
        xaxis=dict(tickmode="array", tickvals=[0, 1, 2, 3], ticktext=["Year 0", "Year 1", "Year 2", "Year 3"]),
        yaxis=dict(tickformat="$,.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=40), height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_revenue_composition(
    std: CohortScenario,
    ltv: CohortScenario,
    top: CohortScenario,
    ai: CohortScenario | None = None,
) -> None:
    """Stacked bar showing revenue mix by year for all three or four scenarios."""
    st.markdown("**Revenue Composition by Year**")

    categories = ["SaaS", "CC", "ACH", "Float", "Impl Fee", "TP SaaS", "TP Proc"]
    colors = ["#3498DB", "#1B6AC9", "#2980B9", "#1ABC9C", "#95A5A6", "#9B59B6", "#8E44AD"]

    def _year_vals(s: CohortScenario, y: int) -> list[float]:
        cy = s.cohort_yearly[y]
        return [cy.saas_revenue, cy.cc_revenue, cy.ach_revenue,
                cy.float_income, cy.impl_fee_revenue,
                cy.teampay_saas_revenue, cy.teampay_processing_revenue]

    if ai is not None:
        x_labels = [
            "Std Y1", "Rev Y1", "$Mar Y1", "AI Y1",
            "Std Y2", "Rev Y2", "$Mar Y2", "AI Y2",
            "Std Y3", "Rev Y3", "$Mar Y3", "AI Y3",
        ]
    else:
        x_labels = [
            "Std Y1", "Rev Y1", "$Mar Y1",
            "Std Y2", "Rev Y2", "$Mar Y2",
            "Std Y3", "Rev Y3", "$Mar Y3",
        ]
    _label_color_map = {"Std": STD_COLOR, "Rev": REV_COLOR, "$Mar": MAR_COLOR, "AI": AI_COLOR}
    def _tick_color(lab):
        for prefix, color in _label_color_map.items():
            if lab.startswith(prefix):
                return color
        return "#333"
    tick_colors = [_tick_color(lab) for lab in x_labels]

    all_vals: list[list[float]] = []
    for y in (1, 2, 3):
        all_vals.append(_year_vals(std, y))
        all_vals.append(_year_vals(ltv, y))
        all_vals.append(_year_vals(top, y))
        if ai is not None:
            all_vals.append(_year_vals(ai, y))

    fig = go.Figure()
    for i, cat in enumerate(categories):
        y_vals = [bar[i] for bar in all_vals]
        texts = [f"${v:,.0f}" if v > 50_000 else "" for v in y_vals]
        fig.add_trace(go.Bar(
            x=x_labels, y=y_vals,
            name=cat, marker_color=colors[i],
            text=texts, textposition="inside",
            textfont=dict(color="white", size=11),
        ))

    fig.update_layout(
        barmode="stack",
        yaxis=dict(tickformat="$,.0f", tickfont=dict(size=14)),
        xaxis=dict(
            tickfont=dict(size=13, weight="bold"),
            tickvals=list(range(len(x_labels))),
            ticktext=[
                f'<span style="color:{c}">{lab}</span>'
                for lab, c in zip(x_labels, tick_colors)
            ],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=13)),
        margin=dict(t=50, b=40), height=650,
    )

    bar_totals = [sum(bar) for bar in all_vals]
    for i, (label, total) in enumerate(zip(x_labels, bar_totals)):
        fig.add_annotation(
            x=label, y=total,
            text=f"<b>${total:,.0f}</b>",
            showarrow=False,
            yshift=12,
            font=dict(size=12, color=_tick_color(label)),
        )

    if ai is not None:
        for x_pos in [3.5, 7.5]:
            fig.add_vline(x=x_pos, line_dash="dot", line_color="#ccc", line_width=1)
    else:
        for x_pos in [2.5, 5.5]:
            fig.add_vline(x=x_pos, line_dash="dot", line_color="#ccc", line_width=1)

    st.plotly_chart(fig, use_container_width=True)


def render_insight_callouts(
    std: CohortScenario,
    ltv: CohortScenario,
    top: CohortScenario,
) -> None:
    """Key insight messages."""
    BOX = (
        '<div style="padding:12px 16px;background:#e8f4fd;border-left:4px solid #1B6AC9;'
        'border-radius:4px;margin-bottom:8px;color:#1B6AC9;font-size:0.95rem;">'
    )
    BOX_GREEN = (
        '<div style="padding:12px 16px;background:#e8f8ef;border-left:4px solid #2ECC71;'
        'border-radius:4px;margin-bottom:8px;color:#1a6e3a;font-size:0.95rem;">'
    )
    BOX_ORANGE = (
        '<div style="padding:12px 16px;background:#fef3e8;border-left:4px solid #E67E22;'
        'border-radius:4px;margin-bottom:8px;color:#a85d1a;font-size:0.95rem;">'
    )

    ltv_deal_delta = ltv.deals_won - std.deals_won
    top_deal_delta = top.deals_won - std.deals_won

    if ltv_deal_delta > 0 or top_deal_delta > 0:
        st.markdown(
            f'{BOX_GREEN}Optimized pricing wins <b>{ltv_deal_delta} more deals</b> (Revenue) '
            f'/ <b>{top_deal_delta} more deals</b> ($ Margin) '
            f'from the same pipeline ({std.deals_won} standard).</div>',
            unsafe_allow_html=True,
        )

    ltv_margin = ltv.three_year_margin - std.three_year_margin
    top_margin = top.three_year_margin - std.three_year_margin
    ltv_rev = ltv.three_year_revenue - std.three_year_revenue
    top_rev = top.three_year_revenue - std.three_year_revenue

    st.markdown(
        f'{BOX}3-year margin impact: Revenue <b>${ltv_margin:+,.0f}</b> &nbsp;|&nbsp; '
        f'$ Margin <b>${top_margin:+,.0f}</b></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'{BOX_ORANGE}3-year revenue impact: Revenue <b>${ltv_rev:+,.0f}</b> &nbsp;|&nbsp; '
        f'$ Margin <b>${top_rev:+,.0f}</b></div>',
        unsafe_allow_html=True,
    )
