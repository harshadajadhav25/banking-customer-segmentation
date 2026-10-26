"""Deployment-ready banking customer intelligence dashboard."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Banking Customer Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


SEGMENT_COLORS = {
    "High-Value Multi-Product": "#2F80ED",
    "Everyday Cash-Focused": "#56CCF2",
    "Mature Transfer-Focused": "#27AE60",
    "High-Flow Financially Volatile": "#F2994A",
    "Low-Engagement Dormant": "#EB5757",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIRECTORY = PROJECT_ROOT / "data" / "dashboard"
CUSTOMER_DATA_FILE = DATA_DIRECTORY / "customer_segments.csv"
RECOMMENDATION_DATA_FILE = (
    DATA_DIRECTORY / "product_recommendations.csv"
)


def apply_dashboard_style():
    """Apply the visual theme used across the dashboard."""

    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(
                    circle at top right,
                    rgba(47, 128, 237, 0.10),
                    transparent 28%
                ),
                #07111f;
        }

        .block-container {
            max-width: 1550px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(
                180deg,
                #0b1e33 0%,
                #07111f 100%
            );
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        [data-testid="stMetric"] {
            background: linear-gradient(
                145deg,
                rgba(17, 45, 72, 0.96),
                rgba(10, 29, 48, 0.96)
            );
            border: 1px solid rgba(86, 204, 242, 0.18);
            border-radius: 14px;
            padding: 18px 20px;
            min-height: 126px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
        }

        [data-testid="stMetricLabel"] {
            color: #9fb6cb;
            font-size: 0.88rem;
        }

        [data-testid="stMetricValue"] {
            color: #ffffff;
            font-weight: 700;
        }

        .dashboard-header {
            background: linear-gradient(
                110deg,
                #123d60 0%,
                #0d2b47 58%,
                #071827 100%
            );
            border: 1px solid rgba(86, 204, 242, 0.20);
            border-radius: 18px;
            padding: 24px 28px;
            margin-bottom: 18px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
        }

        .dashboard-eyebrow {
            color: #56ccf2;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }

        .dashboard-title {
            color: #ffffff;
            font-size: 2rem;
            font-weight: 750;
            margin: 0;
        }

        .dashboard-subtitle {
            color: #b7c9d9;
            font-size: 0.96rem;
            margin-top: 7px;
            margin-bottom: 0;
        }

        .section-label {
            color: #56ccf2;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-top: 8px;
            margin-bottom: 2px;
        }

        div[data-testid="stTabs"] button {
            font-weight: 650;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_dashboard_data():
    """Load deployment-safe customer and recommendation CSV files."""

    missing_files = [
        str(path)
        for path in [CUSTOMER_DATA_FILE, RECOMMENDATION_DATA_FILE]
        if not path.exists()
    ]
    if missing_files:
        raise FileNotFoundError(
            "Missing dashboard data files: " + ", ".join(missing_files)
        )

    customers = pd.read_csv(CUSTOMER_DATA_FILE)
    recommendations = pd.read_csv(
        RECOMMENDATION_DATA_FILE,
        parse_dates=["snapshot_date", "generated_at"],
    )

    boolean_columns = ["has_card", "has_loan"]
    for column_name in boolean_columns:
        if customers[column_name].dtype != bool:
            customers[column_name] = (
                customers[column_name]
                .astype(str)
                .str.strip()
                .str.lower()
                .map({"true": True, "false": False, "1": True, "0": False})
                .fillna(False)
                .astype(bool)
            )

    customers = customers.sort_values("customer_id").reset_index(drop=True)
    recommendations = recommendations.sort_values(
        ["customer_id", "recommendation_rank"]
    ).reset_index(drop=True)

    return customers, recommendations


def compact_number(value):
    """Format large numbers for KPI cards."""

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def build_segment_summary(customers):
    """Create one summary record for every customer segment."""

    summary = (
        customers.groupby("segment_name", as_index=False)
        .agg(
            customer_count=("customer_id", "nunique"),
            transaction_count=("transaction_count", "sum"),
            transaction_volume=("total_transaction_volume", "sum"),
            average_balance=("average_balance", "mean"),
            latest_balance=("latest_balance", "mean"),
            product_count=("banking_product_count", "mean"),
            inactivity_days=("days_since_last_transaction", "mean"),
        )
    )

    summary["customer_percentage"] = (
        summary["customer_count"]
        / customers["customer_id"].nunique()
        * 100
    )

    return summary


def segment_color_scale(segment_order):
    """Return a stable Altair color scale for the visible segments."""

    return alt.Scale(
        domain=segment_order,
        range=[SEGMENT_COLORS[segment] for segment in segment_order],
    )


def build_overview(customers, recommendations):
    """Render the executive overview tab."""

    segment_summary = build_segment_summary(customers)
    segment_order = (
        segment_summary.sort_values("customer_count", ascending=False)[
            "segment_name"
        ].tolist()
    )
    color_scale = segment_color_scale(segment_order)

    left_chart, right_chart = st.columns([1, 1.35], gap="large")

    with left_chart:
        st.subheader("Customer Portfolio")

        customer_donut = (
            alt.Chart(segment_summary)
            .mark_arc(innerRadius=75, outerRadius=125, cornerRadius=5)
            .encode(
                theta=alt.Theta("customer_count:Q", stack=True),
                color=alt.Color(
                    "segment_name:N",
                    scale=color_scale,
                    legend=alt.Legend(
                        title=None,
                        orient="bottom",
                        columns=1,
                        labelLimit=260,
                    ),
                ),
                tooltip=[
                    alt.Tooltip("segment_name:N", title="Segment"),
                    alt.Tooltip(
                        "customer_count:Q",
                        title="Customers",
                        format=",",
                    ),
                    alt.Tooltip(
                        "customer_percentage:Q",
                        title="Portfolio Share",
                        format=".2f",
                    ),
                ],
            )
            .properties(height=390)
        )

        st.altair_chart(customer_donut, use_container_width=True)

    with right_chart:
        st.subheader("Average Balance by Segment")

        balance_chart = (
            alt.Chart(segment_summary)
            .mark_bar(cornerRadiusEnd=5)
            .encode(
                x=alt.X(
                    "average_balance:Q",
                    title="Average Balance (CZK)",
                ),
                y=alt.Y(
                    "segment_name:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(labelLimit=260),
                ),
                color=alt.Color(
                    "segment_name:N",
                    scale=color_scale,
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("segment_name:N", title="Segment"),
                    alt.Tooltip(
                        "average_balance:Q",
                        title="Average Balance",
                        format=",.2f",
                    ),
                    alt.Tooltip(
                        "customer_count:Q",
                        title="Customers",
                        format=",",
                    ),
                ],
            )
            .properties(height=390)
        )

        st.altair_chart(balance_chart, use_container_width=True)

    transaction_column, adoption_column = st.columns(2, gap="large")

    with transaction_column:
        st.subheader("Transaction Volume by Segment")

        volume_chart = (
            alt.Chart(segment_summary)
            .mark_bar(cornerRadiusEnd=5)
            .encode(
                x=alt.X(
                    "transaction_volume:Q",
                    title="Total Transaction Volume (CZK)",
                ),
                y=alt.Y(
                    "segment_name:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(labelLimit=260),
                ),
                color=alt.Color(
                    "segment_name:N",
                    scale=color_scale,
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("segment_name:N", title="Segment"),
                    alt.Tooltip(
                        "transaction_volume:Q",
                        title="Transaction Volume",
                        format=",.0f",
                    ),
                    alt.Tooltip(
                        "transaction_count:Q",
                        title="Transactions",
                        format=",",
                    ),
                ],
            )
            .properties(height=350)
        )

        st.altair_chart(volume_chart, use_container_width=True)

    with adoption_column:
        st.subheader("Product Adoption by Segment")

        product_adoption = (
            customers.groupby("segment_name", as_index=False)
            .agg(Card=("has_card", "mean"), Loan=("has_loan", "mean"))
        )
        product_adoption[["Card", "Loan"]] *= 100
        product_adoption = product_adoption.melt(
            id_vars="segment_name",
            var_name="product",
            value_name="adoption_rate",
        )

        adoption_chart = (
            alt.Chart(product_adoption)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X(
                    "adoption_rate:Q",
                    title="Customer Adoption Rate (%)",
                ),
                y=alt.Y(
                    "segment_name:N",
                    title=None,
                    sort=segment_order,
                    axis=alt.Axis(labelLimit=260),
                ),
                color=alt.Color(
                    "product:N",
                    title="Product",
                    scale=alt.Scale(
                        domain=["Card", "Loan"],
                        range=["#56CCF2", "#F2994A"],
                    ),
                ),
                yOffset="product:N",
                tooltip=[
                    alt.Tooltip("segment_name:N", title="Segment"),
                    alt.Tooltip("product:N", title="Product"),
                    alt.Tooltip(
                        "adoption_rate:Q",
                        title="Adoption Rate",
                        format=".2f",
                    ),
                ],
            )
            .properties(height=350)
        )

        st.altair_chart(adoption_chart, use_container_width=True)

    region_column, recommendation_column = st.columns(2, gap="large")

    with region_column:
        st.subheader("Customers by Region")

        regional_summary = (
            customers.groupby("region_name", as_index=False)
            .agg(customer_count=("customer_id", "nunique"))
            .sort_values("customer_count", ascending=False)
        )

        region_chart = (
            alt.Chart(regional_summary)
            .mark_bar(color="#2F80ED", cornerRadiusEnd=4)
            .encode(
                x=alt.X("customer_count:Q", title="Customers"),
                y=alt.Y(
                    "region_name:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(labelLimit=220),
                ),
                tooltip=[
                    alt.Tooltip("region_name:N", title="Region"),
                    alt.Tooltip(
                        "customer_count:Q",
                        title="Customers",
                        format=",",
                    ),
                ],
            )
            .properties(height=360)
        )

        st.altair_chart(region_chart, use_container_width=True)

    with recommendation_column:
        st.subheader("Recommendations by Product")

        recommendation_summary = (
            recommendations.groupby("recommended_product", as_index=False)
            .agg(
                recommendation_count=("recommendation_id", "count"),
                average_score=("recommendation_score", "mean"),
            )
            .sort_values("recommendation_count", ascending=False)
        )

        recommendation_chart = (
            alt.Chart(recommendation_summary)
            .mark_bar(color="#27AE60", cornerRadiusEnd=4)
            .encode(
                x=alt.X(
                    "recommendation_count:Q",
                    title="Recommendations",
                ),
                y=alt.Y(
                    "recommended_product:N",
                    title=None,
                    sort="-x",
                    axis=alt.Axis(labelLimit=250),
                ),
                tooltip=[
                    alt.Tooltip(
                        "recommended_product:N",
                        title="Product",
                    ),
                    alt.Tooltip(
                        "recommendation_count:Q",
                        title="Recommendations",
                        format=",",
                    ),
                    alt.Tooltip(
                        "average_score:Q",
                        title="Average Score",
                        format=".2f",
                    ),
                ],
            )
            .properties(height=360)
        )

        st.altair_chart(recommendation_chart, use_container_width=True)


def build_segment_intelligence(customers):
    """Render detailed behavioral intelligence for customer segments."""

    st.markdown(
        '<div class="section-label">Segment intelligence</div>',
        unsafe_allow_html=True,
    )

    available_segments = (
        customers["segment_name"]
        .dropna()
        .sort_values()
        .unique()
        .tolist()
    )

    selected_segment = st.selectbox(
        "Focus segment",
        options=available_segments,
        key="segment_intelligence_selector",
    )

    segment_customers = customers.loc[
        customers["segment_name"] == selected_segment
    ].copy()

    description_values = segment_customers[
        "segment_description"
    ].dropna()
    if not description_values.empty:
        st.info(description_values.iloc[0])

    portfolio_customer_count = customers["customer_id"].nunique()
    segment_customer_count = segment_customers["customer_id"].nunique()
    segment_share = (
        segment_customer_count / portfolio_customer_count * 100
    )

    comparison_metrics = {
        "average_balance": (
            segment_customers["average_balance"].mean(),
            customers["average_balance"].mean(),
        ),
        "transaction_count": (
            segment_customers["transaction_count"].mean(),
            customers["transaction_count"].mean(),
        ),
        "transaction_volume": (
            segment_customers["total_transaction_volume"].mean(),
            customers["total_transaction_volume"].mean(),
        ),
        "product_count": (
            segment_customers["banking_product_count"].mean(),
            customers["banking_product_count"].mean(),
        ),
        "inactivity": (
            segment_customers["days_since_last_transaction"].mean(),
            customers["days_since_last_transaction"].mean(),
        ),
    }

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_4, metric_5, metric_6 = st.columns(3)

    metric_1.metric(
        "Customers",
        f"{segment_customer_count:,}",
        delta=f"{segment_share:.2f}% of filtered portfolio",
        delta_color="off",
    )

    segment_value, portfolio_value = comparison_metrics["average_balance"]
    metric_2.metric(
        "Average Balance",
        f"{segment_value:,.0f} CZK",
        delta=f"{segment_value - portfolio_value:,.0f} vs portfolio",
    )

    segment_value, portfolio_value = comparison_metrics["transaction_count"]
    metric_3.metric(
        "Average Transactions",
        f"{segment_value:,.1f}",
        delta=f"{segment_value - portfolio_value:,.1f} vs portfolio",
    )

    segment_value, portfolio_value = comparison_metrics["transaction_volume"]
    metric_4.metric(
        "Average Transaction Volume",
        f"{compact_number(segment_value)} CZK",
        delta=(
            f"{compact_number(segment_value - portfolio_value)} "
            "vs portfolio"
        ),
    )

    segment_value, portfolio_value = comparison_metrics["product_count"]
    metric_5.metric(
        "Average Products",
        f"{segment_value:.2f}",
        delta=f"{segment_value - portfolio_value:.2f} vs portfolio",
    )

    segment_value, portfolio_value = comparison_metrics["inactivity"]
    metric_6.metric(
        "Average Inactivity",
        f"{segment_value:.1f} days",
        delta=f"{segment_value - portfolio_value:.1f} days vs portfolio",
        delta_color="inverse",
    )

    st.write("")

    profile_definitions = [
        ("Average Balance", "average_balance"),
        ("Latest Balance", "latest_balance"),
        ("Transactions", "transaction_count"),
        ("Transaction Volume", "total_transaction_volume"),
        ("Product Count", "banking_product_count"),
        ("Negative Balance Activity", "negative_balance_percentage"),
    ]
    profile_values = []

    for metric_label, column_name in profile_definitions:
        selected_value = segment_customers[column_name].mean()
        overall_value = customers[column_name].mean()
        index_value = (
            selected_value / overall_value * 100
            if overall_value != 0
            else 100
        )
        profile_values.append(
            {
                "metric": metric_label,
                "index_value": index_value,
                "segment_value": selected_value,
                "portfolio_value": overall_value,
            }
        )

    profile_data = pd.DataFrame(profile_values)
    maximum_index = max(160, profile_data["index_value"].max() + 10)

    profile_chart = (
        alt.Chart(profile_data)
        .mark_bar(cornerRadiusEnd=5)
        .encode(
            x=alt.X(
                "index_value:Q",
                title="Index versus Filtered Portfolio Average",
                scale=alt.Scale(domain=[0, maximum_index]),
            ),
            y=alt.Y(
                "metric:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=220),
            ),
            color=alt.condition(
                "datum.index_value >= 100",
                alt.value("#27AE60"),
                alt.value("#2F80ED"),
            ),
            tooltip=[
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip(
                    "index_value:Q",
                    title="Portfolio Index",
                    format=".1f",
                ),
                alt.Tooltip(
                    "segment_value:Q",
                    title="Segment Value",
                    format=",.2f",
                ),
                alt.Tooltip(
                    "portfolio_value:Q",
                    title="Portfolio Value",
                    format=",.2f",
                ),
            ],
        )
        .properties(height=370)
    )

    benchmark_line = (
        alt.Chart(pd.DataFrame({"benchmark": [100]}))
        .mark_rule(
            color="#F2994A",
            strokeDash=[6, 4],
            strokeWidth=2,
        )
        .encode(x="benchmark:Q")
    )

    activity_summary = pd.DataFrame(
        {
            "Activity": [
                "Card Withdrawals",
                "Cash Deposits",
                "Incoming Transfers",
                "Outgoing Transfers",
            ],
            "Selected Segment": [
                segment_customers["card_withdrawal_count"].mean(),
                segment_customers["cash_deposit_count"].mean(),
                segment_customers["incoming_transfer_count"].mean(),
                segment_customers["outgoing_transfer_count"].mean(),
            ],
            "Portfolio Average": [
                customers["card_withdrawal_count"].mean(),
                customers["cash_deposit_count"].mean(),
                customers["incoming_transfer_count"].mean(),
                customers["outgoing_transfer_count"].mean(),
            ],
        }
    )

    activity_long = activity_summary.melt(
        id_vars="Activity",
        var_name="Group",
        value_name="Average Count",
    )

    activity_chart = (
        alt.Chart(activity_long)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Average Count:Q", title="Average Activity Count"),
            y=alt.Y(
                "Activity:N",
                title=None,
                axis=alt.Axis(labelLimit=200),
            ),
            color=alt.Color(
                "Group:N",
                scale=alt.Scale(
                    domain=["Selected Segment", "Portfolio Average"],
                    range=["#56CCF2", "#5D6D7E"],
                ),
            ),
            yOffset="Group:N",
            tooltip=[
                alt.Tooltip("Activity:N", title="Activity"),
                alt.Tooltip("Group:N", title="Comparison"),
                alt.Tooltip(
                    "Average Count:Q",
                    title="Average Count",
                    format=".2f",
                ),
            ],
        )
        .properties(height=370)
    )

    profile_column, activity_column = st.columns(2, gap="large")

    with profile_column:
        st.subheader("Behavioral Profile Index")
        st.caption("100 represents the filtered portfolio average.")
        st.altair_chart(
            profile_chart + benchmark_line,
            use_container_width=True,
        )

    with activity_column:
        st.subheader("Transaction Mode Comparison")
        st.caption(
            "Selected segment compared with the filtered portfolio."
        )
        st.altair_chart(activity_chart, use_container_width=True)

    ownership_column, comparison_column = st.columns(
        [0.8, 1.5],
        gap="large",
    )

    with ownership_column:
        st.subheader("Product Ownership")

        ownership_data = pd.DataFrame(
            {
                "Product": [
                    "Payment Card",
                    "Loan",
                    "Scheduled Payments",
                ],
                "Ownership Rate": [
                    segment_customers["has_card"].mean() * 100,
                    segment_customers["has_loan"].mean() * 100,
                    (
                        segment_customers["payment_order_count"] > 0
                    ).mean()
                    * 100,
                ],
            }
        )

        ownership_chart = (
            alt.Chart(ownership_data)
            .mark_bar(color="#F2994A", cornerRadiusEnd=5)
            .encode(
                x=alt.X(
                    "Ownership Rate:Q",
                    title="Customer Ownership Rate (%)",
                    scale=alt.Scale(domain=[0, 100]),
                ),
                y=alt.Y("Product:N", title=None, sort="-x"),
                tooltip=[
                    alt.Tooltip("Product:N", title="Product"),
                    alt.Tooltip(
                        "Ownership Rate:Q",
                        title="Ownership Rate",
                        format=".2f",
                    ),
                ],
            )
            .properties(height=260)
        )

        st.altair_chart(ownership_chart, use_container_width=True)

    with comparison_column:
        st.subheader("All Segment Comparison")

        comparison_table = (
            customers.groupby("segment_name", as_index=False)
            .agg(
                Customers=("customer_id", "nunique"),
                Average_Balance=("average_balance", "mean"),
                Average_Transactions=("transaction_count", "mean"),
                Average_Volume=("total_transaction_volume", "mean"),
                Average_Products=("banking_product_count", "mean"),
                Card_Rate=("has_card", "mean"),
                Loan_Rate=("has_loan", "mean"),
            )
        )
        comparison_table["Card_Rate"] *= 100
        comparison_table["Loan_Rate"] *= 100
        comparison_table = comparison_table.rename(
            columns={
                "segment_name": "Segment",
                "Average_Balance": "Average Balance",
                "Average_Transactions": "Average Transactions",
                "Average_Volume": "Average Volume",
                "Average_Products": "Average Products",
                "Card_Rate": "Card Rate (%)",
                "Loan_Rate": "Loan Rate (%)",
            }
        )
        numeric_columns = comparison_table.select_dtypes(
            include="number"
        ).columns
        comparison_table[numeric_columns] = comparison_table[
            numeric_columns
        ].round(2)

        st.dataframe(
            comparison_table,
            use_container_width=True,
            hide_index=True,
        )


def build_recommendation_analytics(recommendations):
    """Render recommendation performance and targeting analytics."""

    st.markdown(
        '<div class="section-label">Recommendation analytics</div>',
        unsafe_allow_html=True,
    )

    product_options = sorted(
        recommendations["recommended_product"].dropna().unique()
    )

    filter_1, filter_2, filter_3 = st.columns([1.4, 1, 1])

    with filter_1:
        selected_products = st.multiselect(
            "Recommended products",
            options=product_options,
            default=[],
            placeholder="All products",
            key="recommendation_product_filter",
        )

    with filter_2:
        selected_rank = st.selectbox(
            "Recommendation rank",
            options=["All ranks", "Rank 1", "Rank 2", "Rank 3"],
            key="recommendation_rank_filter",
        )

    with filter_3:
        minimum_score = st.slider(
            "Minimum score",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            key="recommendation_score_filter",
        )

    active_products = selected_products or product_options

    filtered = recommendations.loc[
        recommendations["recommended_product"].isin(active_products)
        & (recommendations["recommendation_score"] >= minimum_score)
    ].copy()

    if selected_rank != "All ranks":
        rank_value = int(selected_rank.split()[-1])
        filtered = filtered.loc[
            filtered["recommendation_rank"] == rank_value
        ].copy()

    if filtered.empty:
        st.warning("No recommendations match the selected filters.")
        return

    recommendation_count = len(filtered)
    customer_count = filtered["customer_id"].nunique()
    average_score = filtered["recommendation_score"].mean()
    average_per_customer = recommendation_count / customer_count
    rank_one_count = int(
        (filtered["recommendation_rank"] == 1).sum()
    )
    top_product = filtered["recommended_product"].value_counts().idxmax()

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_4, metric_5, metric_6 = st.columns(3)

    metric_1.metric("Recommendations", f"{recommendation_count:,}")
    metric_2.metric("Customers Reached", f"{customer_count:,}")
    metric_3.metric("Average Score", f"{average_score:.1f}")
    metric_4.metric("Average per Customer", f"{average_per_customer:.2f}")
    metric_5.metric("Rank 1 Recommendations", f"{rank_one_count:,}")
    metric_6.metric("Leading Product", top_product)

    st.write("")

    product_summary = (
        filtered.groupby("recommended_product", as_index=False)
        .agg(
            recommendation_count=("recommendation_id", "count"),
            customer_count=("customer_id", "nunique"),
            average_score=("recommendation_score", "mean"),
        )
        .sort_values("recommendation_count", ascending=False)
    )

    count_chart = (
        alt.Chart(product_summary)
        .mark_bar(color="#27AE60", cornerRadiusEnd=5)
        .encode(
            x=alt.X("recommendation_count:Q", title="Recommendations"),
            y=alt.Y(
                "recommended_product:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=250),
            ),
            tooltip=[
                alt.Tooltip("recommended_product:N", title="Product"),
                alt.Tooltip(
                    "recommendation_count:Q",
                    title="Recommendations",
                    format=",",
                ),
                alt.Tooltip(
                    "customer_count:Q",
                    title="Customers",
                    format=",",
                ),
            ],
        )
        .properties(height=350)
    )

    score_chart = (
        alt.Chart(product_summary)
        .mark_bar(color="#F2994A", cornerRadiusEnd=5)
        .encode(
            x=alt.X(
                "average_score:Q",
                title="Average Recommendation Score",
                scale=alt.Scale(domain=[0, 100]),
            ),
            y=alt.Y(
                "recommended_product:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=250),
            ),
            tooltip=[
                alt.Tooltip("recommended_product:N", title="Product"),
                alt.Tooltip(
                    "average_score:Q",
                    title="Average Score",
                    format=".2f",
                ),
            ],
        )
        .properties(height=350)
    )

    count_column, score_column = st.columns(2, gap="large")

    with count_column:
        st.subheader("Recommendation Demand")
        st.altair_chart(count_chart, use_container_width=True)

    with score_column:
        st.subheader("Recommendation Strength")
        st.altair_chart(score_chart, use_container_width=True)

    heatmap_data = (
        filtered.groupby(
            ["segment_name", "recommended_product"],
            as_index=False,
        )
        .agg(recommendation_count=("recommendation_id", "count"))
    )

    heatmap_base = alt.Chart(heatmap_data).encode(
        x=alt.X(
            "recommended_product:N",
            title="Recommended Product",
            axis=alt.Axis(labelAngle=-35, labelLimit=190),
        ),
        y=alt.Y(
            "segment_name:N",
            title=None,
            axis=alt.Axis(labelLimit=250),
        ),
    )

    heatmap = heatmap_base.mark_rect(cornerRadius=3).encode(
        color=alt.Color(
            "recommendation_count:Q",
            title="Recommendations",
            scale=alt.Scale(scheme="blues"),
        ),
        tooltip=[
            alt.Tooltip("segment_name:N", title="Segment"),
            alt.Tooltip("recommended_product:N", title="Product"),
            alt.Tooltip(
                "recommendation_count:Q",
                title="Recommendations",
                format=",",
            ),
        ],
    )

    heatmap_labels = heatmap_base.mark_text(fontWeight="bold").encode(
        text=alt.Text("recommendation_count:Q", format=","),
        color=alt.condition(
            "datum.recommendation_count > 700",
            alt.value("white"),
            alt.value("#dce9f5"),
        ),
    )

    rank_summary = (
        filtered.groupby(
            ["recommended_product", "recommendation_rank"],
            as_index=False,
        )
        .agg(recommendation_count=("recommendation_id", "count"))
    )
    rank_summary["Rank"] = (
        "Rank " + rank_summary["recommendation_rank"].astype(str)
    )

    rank_chart = (
        alt.Chart(rank_summary)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("recommendation_count:Q", title="Recommendations"),
            y=alt.Y(
                "recommended_product:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=240),
            ),
            color=alt.Color(
                "Rank:N",
                scale=alt.Scale(
                    domain=["Rank 1", "Rank 2", "Rank 3"],
                    range=["#2F80ED", "#56CCF2", "#F2994A"],
                ),
            ),
            order=alt.Order("recommendation_rank:Q"),
            tooltip=[
                alt.Tooltip("recommended_product:N", title="Product"),
                alt.Tooltip("Rank:N", title="Rank"),
                alt.Tooltip(
                    "recommendation_count:Q",
                    title="Recommendations",
                    format=",",
                ),
            ],
        )
        .properties(height=350)
    )

    heatmap_column, rank_column = st.columns([1.25, 1], gap="large")

    with heatmap_column:
        st.subheader("Segment–Product Opportunity Matrix")
        st.altair_chart(
            (heatmap + heatmap_labels).properties(height=350),
            use_container_width=True,
        )

    with rank_column:
        st.subheader("Recommendation Rank Mix")
        st.altair_chart(rank_chart, use_container_width=True)

    st.subheader("Recommendation Detail")

    detail_table = filtered[
        [
            "customer_id",
            "segment_name",
            "recommended_product",
            "recommendation_rank",
            "recommendation_score",
            "recommendation_reason",
        ]
    ].copy()

    detail_table = detail_table.rename(
        columns={
            "customer_id": "Customer ID",
            "segment_name": "Segment",
            "recommended_product": "Recommended Product",
            "recommendation_rank": "Rank",
            "recommendation_score": "Score",
            "recommendation_reason": "Reason",
        }
    ).sort_values(["Score", "Rank"], ascending=[False, True])

    st.dataframe(
        detail_table,
        use_container_width=True,
        hide_index=True,
        height=420,
    )


def build_customer_360(customers, recommendations):
    """Render an individual customer profile and recommendation view."""

    st.markdown('<div class="section-label">Customer 360 explorer</div>', unsafe_allow_html=True)
    st.caption("Search any customer ID to inspect behavior, segment context and personalized recommendations.")

    customer_ids = sorted(customers["customer_id"].dropna().astype(int).unique().tolist())
    if not customer_ids:
        st.warning("No customers are available for the current filters.")
        return

    selector_column, context_column = st.columns([1, 2], gap="large")
    with selector_column:
        selected_id = st.selectbox(
            "Search customer ID",
            customer_ids,
            format_func=lambda value: f"Customer {value}",
            key="customer_360_selector",
            help="Click the field and type an ID. Every customer allowed by the sidebar filters is included.",
        )

    customer = customers.loc[customers["customer_id"].astype(int) == selected_id].iloc[0]
    customer_recommendations = recommendations.loc[
        recommendations["customer_id"].astype(int) == selected_id
    ].sort_values("recommendation_rank")

    with context_column:
        st.info(
            f"Customer {selected_id} belongs to the **{customer['segment_name']}** "
            f"segment and is located in **{customer['region_name']}**."
        )

    profile_columns = st.columns(4)
    profile_columns[0].metric("Customer ID", str(selected_id))
    profile_columns[1].metric("Account ID", str(int(customer["account_id"])))
    profile_columns[2].metric("Segment", customer["segment_name"])
    profile_columns[3].metric("Region", customer["region_name"])

    st.subheader("Customer Snapshot")
    snapshot = st.columns(3) + st.columns(3)
    snapshot[0].metric("Average Balance", f"{customer['average_balance']:,.0f} CZK")
    snapshot[1].metric("Latest Balance", f"{customer['latest_balance']:,.0f} CZK")
    snapshot[2].metric("Transactions", f"{int(customer['transaction_count']):,}")
    snapshot[3].metric("Transaction Volume", f"{compact_number(customer['total_transaction_volume'])} CZK")
    snapshot[4].metric("Days Since Last Transaction", f"{int(customer['days_since_last_transaction'])}")
    snapshot[5].metric("Banking Products", f"{int(customer['banking_product_count'])}")

    behavior_column, ownership_column = st.columns([1.35, 1], gap="large")
    with behavior_column:
        st.subheader("Transaction Behavior")
        behavior = pd.DataFrame({
            "Activity": ["Card Withdrawals", "Cash Deposits", "Incoming Transfers", "Outgoing Transfers"],
            "Count": [customer["card_withdrawal_count"], customer["cash_deposit_count"], customer["incoming_transfer_count"], customer["outgoing_transfer_count"]],
        })
        chart = alt.Chart(behavior).mark_bar(color="#2F80ED", cornerRadiusEnd=5).encode(
            x=alt.X("Count:Q", title="Activity Count"),
            y=alt.Y("Activity:N", title=None, sort="-x", axis=alt.Axis(labelLimit=210)),
            tooltip=[alt.Tooltip("Activity:N"), alt.Tooltip("Count:Q", format=",")],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

    with ownership_column:
        st.subheader("Product Ownership")
        ownership = {
            "Payment Card": bool(customer["has_card"]),
            "Loan": bool(customer["has_loan"]),
            "Scheduled Payments": customer["payment_order_count"] > 0,
        }
        for product, owned in ownership.items():
            st.markdown(f"### {'✅' if owned else '➖'} {product}\n{'Owned' if owned else 'Not owned'}")
        st.caption(f"Account tenure: {int(customer['account_tenure_months'])} months")

    recommendation_column, comparison_column = st.columns([1.2, 1], gap="large")
    with recommendation_column:
        st.subheader("Personalized Recommendations")
        if customer_recommendations.empty:
            st.warning("No recommendations were generated for this customer.")
        else:
            display = customer_recommendations[["recommendation_rank", "recommended_product", "recommendation_score", "recommendation_reason"]].rename(columns={
                "recommendation_rank": "Rank", "recommended_product": "Recommended Product",
                "recommendation_score": "Score", "recommendation_reason": "Reason",
            })
            st.dataframe(display, use_container_width=True, hide_index=True, height=235)

    segment_customers = customers.loc[customers["segment_name"] == customer["segment_name"]]
    with comparison_column:
        st.subheader("Customer vs Segment")
        fields = [
            ("Average Balance", "average_balance"), ("Transactions", "transaction_count"),
            ("Transaction Volume", "total_transaction_volume"), ("Banking Products", "banking_product_count"),
        ]
        comparison = pd.DataFrame([{
            "Metric": label, "Customer": customer[column],
            "Segment Average": segment_customers[column].mean(),
        } for label, column in fields])
        comparison["Index"] = (comparison["Customer"] / comparison["Segment Average"].replace(0, pd.NA) * 100).fillna(0)
        bars = alt.Chart(comparison).mark_bar(cornerRadiusEnd=5).encode(
            x=alt.X("Index:Q", title="Segment Average Index (100 = average)"),
            y=alt.Y("Metric:N", title=None),
            color=alt.condition("datum.Index >= 100", alt.value("#27AE60"), alt.value("#F2994A")),
            tooltip=["Metric:N", alt.Tooltip("Index:Q", format=".1f"), alt.Tooltip("Customer:Q", format=",.2f"), alt.Tooltip("Segment Average:Q", format=",.2f")],
        ).properties(height=235)
        line = alt.Chart(pd.DataFrame({"benchmark": [100]})).mark_rule(color="#56CCF2", strokeDash=[6, 4]).encode(x="benchmark:Q")
        st.altair_chart(bars + line, use_container_width=True)

    st.subheader("Similar Customers in the Same Segment")
    similarity_fields = ["average_balance", "transaction_count", "total_transaction_volume", "banking_product_count"]
    pool = segment_customers.loc[segment_customers["customer_id"].astype(int) != selected_id].copy()
    if pool.empty:
        st.info("No other customers are available in this segment.")
        return
    distance_fields = []
    for field in similarity_fields:
        standard_deviation = segment_customers[field].std()
        standard_deviation = 1 if pd.isna(standard_deviation) or standard_deviation == 0 else standard_deviation
        distance_field = f"{field}_distance"
        pool[distance_field] = ((pool[field] - customer[field]) / standard_deviation) ** 2
        distance_fields.append(distance_field)
    pool["distance"] = pool[distance_fields].sum(axis=1)
    similar = pool.nsmallest(5, "distance")[["customer_id", "region_name", "average_balance", "transaction_count", "total_transaction_volume", "banking_product_count"]].rename(columns={
        "customer_id": "Customer ID", "region_name": "Region", "average_balance": "Average Balance",
        "transaction_count": "Transactions", "total_transaction_volume": "Transaction Volume", "banking_product_count": "Products",
    })
    similar[["Average Balance", "Transaction Volume"]] = similar[["Average Balance", "Transaction Volume"]].round(2)
    st.dataframe(similar, use_container_width=True, hide_index=True)


def build_model_insights(customers):
    """Render model evaluation, methodology and responsible-use details."""

    st.markdown(
        '<div class="section-label">Model insights</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Transparent evaluation of the K-Means customer segmentation model."
    )

    evaluation = pd.DataFrame(
        {
            "Clusters": [2, 3, 4, 5, 6],
            "Inertia": [45918.68, 40234.79, 35121.94, 31240.28, 28436.12],
            "Silhouette Score": [0.2665, 0.2290, 0.2271, 0.2438, 0.2451],
            "Davies-Bouldin Index": [1.4649, 1.8095, 1.5786, 1.4554, 1.5098],
        }
    )

    selected_model = evaluation.loc[evaluation["Clusters"] == 5].iloc[0]
    segment_sizes = customers.groupby("segment_name")["customer_id"].nunique()

    metric_columns = st.columns(5)
    metric_columns[0].metric("Selected Clusters", "5")
    metric_columns[1].metric("Customers Scored", f"{customers['customer_id'].nunique():,}")
    metric_columns[2].metric("Features", "14")
    metric_columns[3].metric("Silhouette Score", f"{selected_model['Silhouette Score']:.4f}")
    metric_columns[4].metric("Davies-Bouldin", f"{selected_model['Davies-Bouldin Index']:.4f}")

    st.info(
        "**Why five clusters?** The five-cluster solution provides useful "
        "business differentiation while maintaining competitive separation. "
        "Although k=2 has the highest silhouette score, it creates segments "
        "that are too broad for meaningful product and engagement strategies."
    )

    inertia_column, quality_column = st.columns(2, gap="large")

    with inertia_column:
        st.subheader("Elbow Analysis")
        inertia_line = (
            alt.Chart(evaluation)
            .mark_line(point=alt.OverlayMarkDef(filled=True, size=90), color="#2F80ED", strokeWidth=3)
            .encode(
                x=alt.X("Clusters:O", title="Number of Clusters (k)"),
                y=alt.Y("Inertia:Q", title="Within-Cluster Inertia", scale=alt.Scale(zero=False)),
                tooltip=["Clusters:O", alt.Tooltip("Inertia:Q", format=",.2f")],
            )
            .properties(height=340)
        )
        selected_point = (
            alt.Chart(evaluation.loc[evaluation["Clusters"] == 5])
            .mark_point(color="#F2994A", filled=True, size=230)
            .encode(x="Clusters:O", y="Inertia:Q")
        )
        st.altair_chart(inertia_line + selected_point, use_container_width=True)

    with quality_column:
        st.subheader("Cluster Quality Comparison")
        quality = evaluation[["Clusters", "Silhouette Score", "Davies-Bouldin Index"]].melt(
            id_vars="Clusters", var_name="Metric", value_name="Score"
        )
        quality_chart = (
            alt.Chart(quality)
            .mark_line(point=True, strokeWidth=3)
            .encode(
                x=alt.X("Clusters:O", title="Number of Clusters (k)"),
                y=alt.Y("Score:Q", title="Metric Value", scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "Metric:N",
                    scale=alt.Scale(
                        domain=["Silhouette Score", "Davies-Bouldin Index"],
                        range=["#27AE60", "#F2994A"],
                    ),
                ),
                tooltip=["Clusters:O", "Metric:N", alt.Tooltip("Score:Q", format=".4f")],
            )
            .properties(height=340)
        )
        st.altair_chart(quality_chart, use_container_width=True)
        st.caption("Higher silhouette is better; lower Davies-Bouldin is better.")

    distribution_column, pipeline_column = st.columns([1.1, 1], gap="large")

    with distribution_column:
        st.subheader("Final Segment Distribution")
        distribution = segment_sizes.reset_index(name="Customers")
        distribution["Share"] = distribution["Customers"] / distribution["Customers"].sum() * 100
        distribution_chart = (
            alt.Chart(distribution)
            .mark_bar(cornerRadiusEnd=5)
            .encode(
                x=alt.X("Customers:Q", title="Customers"),
                y=alt.Y("segment_name:N", title=None, sort="-x", axis=alt.Axis(labelLimit=260)),
                color=alt.Color(
                    "segment_name:N",
                    title=None,
                    scale=alt.Scale(
                        domain=list(SEGMENT_COLORS.keys()),
                        range=list(SEGMENT_COLORS.values()),
                    ),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("segment_name:N", title="Segment"),
                    alt.Tooltip("Customers:Q", format=","),
                    alt.Tooltip("Share:Q", format=".2f", title="Share (%)"),
                ],
            )
            .properties(height=330)
        )
        st.altair_chart(distribution_chart, use_container_width=True)

    with pipeline_column:
        st.subheader("Modeling Workflow")
        workflow = pd.DataFrame(
            {
                "Step": [1, 2, 3, 4, 5],
                "Stage": [
                    "Customer 360 features",
                    "1st/99th percentile capping",
                    "Yeo-Johnson transformation",
                    "Standardization",
                    "K-Means clustering",
                ],
                "Purpose": [
                    "Create one behavioral record per customer",
                    "Reduce extreme-value influence",
                    "Handle skewed feature distributions",
                    "Place features on comparable scales",
                    "Group customers with similar behavior",
                ],
            }
        )
        st.dataframe(workflow, use_container_width=True, hide_index=True, height=330)

    feature_column, evaluation_column = st.columns([1, 1.15], gap="large")

    with feature_column:
        st.subheader("Behavioral Feature Groups")
        feature_groups = pd.DataFrame(
            {
                "Feature Group": [
                    "Engagement", "Transaction Value", "Cash Flow",
                    "Balance", "Channel Behavior", "Product Ownership",
                ],
                "Examples": [
                    "Recency, frequency and account tenure",
                    "Transaction volume and average amount",
                    "Credits, debits and net cash flow",
                    "Average, latest and negative balances",
                    "Cash, card and transfer activity",
                    "Cards, loans and scheduled payments",
                ],
            }
        )
        st.dataframe(feature_groups, use_container_width=True, hide_index=True)

    with evaluation_column:
        st.subheader("Evaluation Results")
        evaluation_display = evaluation.copy()
        evaluation_display["Selected"] = evaluation_display["Clusters"].map(
            lambda value: "✓" if value == 5 else ""
        )
        st.dataframe(evaluation_display, use_container_width=True, hide_index=True)

    st.subheader("Responsible Interpretation")
    guidance_1, guidance_2, guidance_3 = st.columns(3)
    with guidance_1:
        st.warning(
            "**Descriptive, not predictive**\n\nSegments summarize patterns "
            "in historical behavior. They do not predict an individual's future actions."
        )
    with guidance_2:
        st.warning(
            "**No eligibility decisions**\n\nDo not use clusters for credit "
            "approval, pricing, adverse action, or other high-impact decisions."
        )
    with guidance_3:
        st.warning(
            "**Monitor and review**\n\nCheck segment stability, data quality "
            "and recommendation rules whenever the pipeline is retrained."
        )

    with st.expander("Dataset and model limitations"):
        st.markdown(
            """
            - The project uses the historical, anonymized PKDD'99 Czech banking dataset.
            - Original dates and currency context are retained for transparency.
            - Cluster labels are analyst-created business interpretations.
            - Recommendation scores are explainable rule scores, not purchase probabilities.
            - Results demonstrate an analytics workflow and should not be treated as current banking behavior.
            """
        )


def main():
    """Run the interactive banking intelligence application."""

    apply_dashboard_style()

    st.markdown(
        """
        <div class="dashboard-header">
            <div class="dashboard-eyebrow">
                Customer Analytics Platform
            </div>
            <h1 class="dashboard-title">
                Banking Customer Intelligence
            </h1>
            <p class="dashboard-subtitle">
                Behavioral segmentation, portfolio analytics and
                explainable product recommendations
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        customers, recommendations = load_dashboard_data()
    except Exception as error:
        st.error(
            "The dashboard data files could not be loaded. Make sure "
            "customer_segments.csv and product_recommendations.csv are "
            "available in data/dashboard/."
        )
        st.exception(error)
        st.stop()

    st.sidebar.markdown("## Portfolio Filters")
    st.sidebar.success("Data source: deployment CSV snapshot")
    st.sidebar.caption(
        "Leave a filter empty to include all available values."
    )

    available_segments = sorted(
        customers["segment_name"].dropna().unique()
    )
    available_regions = sorted(
        customers["region_name"].dropna().unique()
    )

    selected_segments = st.sidebar.multiselect(
        "Customer segments",
        options=available_segments,
        default=[],
        placeholder="All segments",
    )
    selected_regions = st.sidebar.multiselect(
        "Regions",
        options=available_regions,
        default=[],
        placeholder="All regions",
    )

    active_segments = selected_segments or available_segments
    active_regions = selected_regions or available_regions

    filtered_customers = customers.loc[
        customers["segment_name"].isin(active_segments)
        & customers["region_name"].isin(active_regions)
    ].copy()

    selected_customer_ids = filtered_customers["customer_id"].unique()
    filtered_recommendations = recommendations.loc[
        recommendations["customer_id"].isin(selected_customer_ids)
    ].copy()

    if filtered_customers.empty:
        st.warning("No customers match the selected filter combination.")
        st.stop()

    total_customers = filtered_customers["customer_id"].nunique()
    total_transactions = filtered_customers["transaction_count"].sum()
    total_volume = filtered_customers["total_transaction_volume"].sum()
    average_balance = filtered_customers["average_balance"].mean()
    card_adoption = filtered_customers["has_card"].mean() * 100
    loan_adoption = filtered_customers["has_loan"].mean() * 100

    st.markdown(
        '<div class="section-label">Filtered portfolio</div>',
        unsafe_allow_html=True,
    )

    metric_1, metric_2, metric_3 = st.columns(3)
    metric_4, metric_5, metric_6 = st.columns(3)

    metric_1.metric("Customers", f"{total_customers:,}")
    metric_2.metric("Transactions", compact_number(total_transactions))
    metric_3.metric(
        "Transaction Volume",
        f"{compact_number(total_volume)} CZK",
    )
    metric_4.metric(
        "Average Balance",
        f"{average_balance:,.0f} CZK",
    )
    metric_5.metric("Card Adoption", f"{card_adoption:.1f}%")
    metric_6.metric("Loan Adoption", f"{loan_adoption:.1f}%")

    st.write("")

    (
        overview_tab,
        segment_tab,
        recommendation_tab,
        customer_tab,
        model_tab,
    ) = st.tabs(
        [
            "Overview",
            "Segments",
            "Recommendations",
            "Customer 360",
            "Model Insights",
        ]
    )

    with overview_tab:
        build_overview(filtered_customers, filtered_recommendations)

    with segment_tab:
        build_segment_intelligence(filtered_customers)

    with recommendation_tab:
        build_recommendation_analytics(filtered_recommendations)

    with customer_tab:
        build_customer_360(filtered_customers, filtered_recommendations)

    with model_tab:
        build_model_insights(filtered_customers)


if __name__ == "__main__":
    main()
