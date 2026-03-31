"""
Paystand Cohort Pricing Impact Model

Compares Standard pricing vs Revenue-Optimized vs Margin%-Optimized
pricing applied to a full deal cohort, showing 3-year financials,
break-even, and revenue impact.
"""
import streamlit as st

st.set_page_config(
    page_title="Paystand Cohort Impact Model",
    page_icon="paystand_logo.png",
    layout="wide",
)

st.markdown(
    """<style>
    /* Bigger text in all dataframe tables */
    .stDataFrame table,
    .stDataFrame th,
    .stDataFrame td,
    div[data-testid="stDataFrame"] table,
    div[data-testid="stDataFrame"] th,
    div[data-testid="stDataFrame"] td,
    .dvn-scroller table,
    .dvn-scroller th,
    .dvn-scroller td,
    [data-testid="glideDataEditor"] * {
        font-size: 1.15rem !important;
    }
    /* Blue subheaders to match title */
    h2, h3, [data-testid="stSubheader"] {
        color: #001F5B !important;
    }
    /* Blue primary button */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background-color: #003B91 !important;
        border-color: #003B91 !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {
        background-color: #002D6F !important;
        border-color: #002D6F !important;
    }
    </style>""",
    unsafe_allow_html=True,
)

import config as cfg
from ui.cohort_inputs import render_cohort_inputs, render_standard_pricing
from ui.cohort_engine import run_cohort_comparison, build_ai_scenario
from ui.cohort_display import (
    render_funnel_comparison,
    render_volume_forecast,
    render_summary_metrics,
    render_annualized_impact,
    render_scenario_header,
    render_pricing_comparison,
    render_cost_to_collect_ar,
    render_upside_breakdown,
)
from ui.cohort_charts import (
    render_break_even_chart,
    render_cumulative_revenue_chart,
    render_revenue_composition,
    render_insight_callouts,
)
from models.ai_agent import run_ai_scenario


def _format_changes(scenario):
    if not scenario.lever_changes:
        return None
    parts = []
    for k, (old, new) in scenario.lever_changes.items():
        label = k.replace("_", " ").title()
        if isinstance(old, str) or isinstance(new, str):
            parts.append(f"{label}: {old} → {new}")
        elif "rate" in k or "pct" in k:
            parts.append(f"{label}: {old:.2%} → {new:.2%}")
        elif "fee" in k or "cap" in k:
            parts.append(f"{label}: ${old:.2f} → ${new:.2f}")
        else:
            parts.append(f"{label}: {old} → {new}")
    return " | ".join(parts)


def main():
    logo_col, title_col = st.columns([0.06, 0.94], gap="small")
    with logo_col:
        st.image("paystand_logo.png", width=55)
    with title_col:
        st.markdown(
            '<h1 style="color: #001F5B; margin-top: -5px;">'
            "Cohort Pricing Impact Model</h1>",
            unsafe_allow_html=True,
        )

    cohort = render_cohort_inputs()
    std_pricing = render_standard_pricing()

    if st.button("Run Cohort Analysis", type="primary", use_container_width=True):
        with st.spinner("Solving for target win rate and scaling to cohort..."):
            standard, revenue_opt, margin_opt, solver_msg = run_cohort_comparison(
                sqls_per_quarter=cohort["sqls_per_quarter"],
                current_win_rate=cohort["current_win_rate"],
                avg_saas_arr=cohort["avg_saas_arr"],
                avg_impl_fee=cohort["avg_impl_fee"],
                total_arr_won=cohort["total_arr_won"],
                standard_pricing_inputs=std_pricing,
                quarterly_growth=cohort["quarterly_growth"],
                tp_contract_optin=cohort["tp_contract_optin"],
                tp_actual_usage=cohort["tp_actual_usage"],
                tp_monthly_volume=cohort["tp_monthly_volume"],
                include_float=cohort["include_float"],
                include_float_std=cohort["include_float_std"],
                include_teampay=cohort["include_teampay"],
                include_upside=cohort["include_upside"],
                include_upside_std=cohort["include_upside_std"],
                upside_total_customers=cohort["upside_total_customers"],
                vas_recommended_only=cohort["vas_recommended_only"],
            )

        st.session_state["standard"] = standard
        st.session_state["revenue_opt"] = revenue_opt
        st.session_state["margin_opt"] = margin_opt
        st.session_state["solver_msg"] = solver_msg
        st.session_state["ai_scenario"] = None
        st.session_state["ai_reasoning"] = None
        st.session_state["ai_analysis"] = None
        st.session_state["cohort_inputs"] = cohort

    if "standard" not in st.session_state:
        return

    standard = st.session_state["standard"]
    revenue_opt = st.session_state["revenue_opt"]
    margin_opt = st.session_state["margin_opt"]
    solver_msg = st.session_state["solver_msg"]

    _BOX_GREEN = (
        '<div style="padding:12px 16px;background:#e8fde8;border-left:4px solid #1B8A4E;'
        'border-radius:4px;margin-bottom:8px;color:#1B8A4E;font-size:0.95rem;">'
    )
    _BOX_BLUE = (
        '<div style="padding:12px 16px;background:#e8f4fd;border-left:4px solid #1B6AC9;'
        'border-radius:4px;margin-bottom:8px;color:#003B91;font-size:0.95rem;">'
    )

    if solver_msg:
        st.markdown(f'{_BOX_BLUE}{solver_msg}</div>', unsafe_allow_html=True)

    rev_changes = _format_changes(revenue_opt)
    margin_changes = _format_changes(margin_opt)

    if rev_changes:
        st.markdown(
            f'{_BOX_GREEN}<b>Revenue Optimized adjustments:</b> {rev_changes}</div>',
            unsafe_allow_html=True,
        )
    if margin_changes:
        _BOX_ORANGE = (
            '<div style="padding:12px 16px;background:#fef3e8;border-left:4px solid #E67E22;'
            'border-radius:4px;margin-bottom:8px;color:#a85d1a;font-size:0.95rem;">'
        )
        st.markdown(
            f'{_BOX_ORANGE}<b>$ Margin Optimized adjustments:</b> {margin_changes}</div>',
            unsafe_allow_html=True,
        )

    # ── AI Scenario Button ──────────────────────────────────────
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    ai_scenario = st.session_state.get("ai_scenario")

    st.divider()
    st.markdown(
        '<div style="font-size:0.9rem;color:#117a8b;margin-bottom:8px;font-weight:600;">'
        'Generate a GPT-4o balanced pricing scenario that optimizes across revenue, margin, and retention.</div>',
        unsafe_allow_html=True,
    )

    if not api_key or api_key == "PASTE_YOUR_KEY_HERE":
        st.warning("Add your OpenAI API key to `.streamlit/secrets.toml` to enable the AI scenario.")
    else:
        if st.button("Run AI Recommended Scenario", type="primary", use_container_width=True):
            with st.spinner("AI is testing pricing configurations (5-12 iterations)..."):
                try:
                    ci = st.session_state.get("cohort_inputs", {})
                    ai_levers, ai_reasoning = run_ai_scenario(
                        standard, revenue_opt, margin_opt, api_key=api_key,
                    )
                    ai_scen = build_ai_scenario(
                        ai_levers, standard,
                        quarterly_growth=ci.get("quarterly_growth", 0.02),
                        tp_contract_optin=ci.get("tp_contract_optin", 0.50),
                        tp_actual_usage=ci.get("tp_actual_usage", 0.20),
                        tp_monthly_volume=ci.get("tp_monthly_volume", cfg.TEAMPAY_MONTHLY_VOLUME),
                        include_float=ci.get("include_float", True),
                        include_teampay=ci.get("include_teampay", True),
                        include_upside=ci.get("include_upside", False),
                        upside_total_customers=ci.get("upside_total_customers", cfg.UPSIDE_TOTAL_CUSTOMERS),
                        vas_recommended_only=ci.get("vas_recommended_only", False),
                    )
                    st.session_state["ai_scenario"] = ai_scen
                    st.session_state["ai_reasoning"] = ai_reasoning
                    ai_scenario = ai_scen
                except Exception as e:
                    st.error(f"AI scenario failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    if ai_scenario:
        _BOX_TEAL = (
            '<div style="padding:12px 16px;background:#e8f8f5;border-left:4px solid #17A2B8;'
            'border-radius:4px;margin-bottom:8px;color:#117a8b;font-size:0.95rem;">'
        )
        ai_changes = _format_changes(ai_scenario)
        iterations_msg = st.session_state.get("ai_reasoning", "")

        # Build factual comparison from real scenario data
        def _delta_str(ai_val, other_val, fmt="$"):
            d = ai_val - other_val
            if fmt == "$":
                return f'<span style="color:{"#09ab3b" if d >= 0 else "#ff2b2b"}">${d:+,.0f}</span>'
            else:
                pp = d * 100
                return f'<span style="color:{"#09ab3b" if d >= 0 else "#ff2b2b"}">{pp:+.1f}pp</span>'

        ai_s = ai_scenario
        rev_s = revenue_opt
        mar_s = margin_opt
        comparison = (
            f"<b>vs Revenue Opt:</b> Rev {_delta_str(ai_s.three_year_revenue, rev_s.three_year_revenue)}, "
            f"Margin % {_delta_str(ai_s.three_year_margin_pct, rev_s.three_year_margin_pct, 'pp')}, "
            f"Take Rate {_delta_str(ai_s.three_year_take_rate, rev_s.three_year_take_rate, 'pp')}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"<b>vs $ Margin Opt:</b> Rev {_delta_str(ai_s.three_year_revenue, mar_s.three_year_revenue)}, "
            f"Margin % {_delta_str(ai_s.three_year_margin_pct, mar_s.three_year_margin_pct, 'pp')}, "
            f"Take Rate {_delta_str(ai_s.three_year_take_rate, mar_s.three_year_take_rate, 'pp')}"
        )

        saas_strat = ai_s.per_deal_pricing.saas_strategy
        strat_label = "Flat Monthly" if saas_strat == "flat_monthly" else "Discount & Remove"

        st.markdown(
            f'{_BOX_TEAL}'
            f'<b>AI Recommended</b> ({iterations_msg}) — Strategy: {strat_label}<br>'
            f'{ai_changes or "Same as standard"}'
            f'<br><br>{comparison}</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    render_funnel_comparison(standard, revenue_opt, margin_opt, ai=ai_scenario)

    st.divider()
    render_volume_forecast(standard, revenue_opt, margin_opt)

    st.divider()
    render_pricing_comparison(standard, revenue_opt, margin_opt, ai=ai_scenario)

    st.divider()
    render_cost_to_collect_ar(standard, revenue_opt, margin_opt, ai=ai_scenario)

    st.divider()
    render_insight_callouts(standard, revenue_opt, margin_opt)

    st.divider()
    render_summary_metrics(standard, revenue_opt, margin_opt, ai=ai_scenario)

    st.divider()
    render_break_even_chart(standard, revenue_opt, margin_opt, ai=ai_scenario)

    render_cumulative_revenue_chart(standard, revenue_opt, margin_opt, ai=ai_scenario)

    st.divider()
    render_revenue_composition(standard, revenue_opt, margin_opt, ai=ai_scenario)

    st.divider()
    render_annualized_impact(standard, revenue_opt, margin_opt, ai=ai_scenario)

    has_vas = any(
        s.upside_detail for s in [standard, revenue_opt, margin_opt]
        if s is not None
    )
    if has_vas:
        st.divider()
        render_upside_breakdown(standard, revenue_opt, margin_opt, ai=ai_scenario)


if __name__ == "__main__":
    main()
