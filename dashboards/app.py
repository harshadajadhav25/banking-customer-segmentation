"""Interactive dashboard for customer segments and recommendations."""

import os

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine


st.set_page_config(
    page_title="Banking Customer Intelligence",
    page_icon="🏦",
    layout="wide",
)


@st.cache_resource
def create_database_engine():
    """Create one reusable database connection engine."""

    load_dotenv()

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB"),
    )

    return create_engine(database_url)


@st.cache_data(ttl=300)
def load_dashboard_data():
    """Load customer segments and recommendations from PostgreSQL."""

    engine = create_database_engine()

    customer_query = """
        SELECT *
        FROM analytics.mart_customer_segments
    """

    recommendation_query = """
        SELECT *
        FROM analytics.mart_product_recommendations
    """

    customers = pd.read_sql(customer_query, engine)
    recommendations = pd.read_sql(recommendation_query, engine)

    return customers, recommendations


def main():
    """Display the banking customer intelligence dashboard."""

    st.title("Banking Customer Intelligence")

    st.caption(
        "Customer segmentation and personalized product recommendations"
    )

    try:
        customers, recommendations = load_dashboard_data()
    except Exception as error:
        st.error(
            "The dashboard could not connect to PostgreSQL. "
            "Make sure Docker Desktop and the database container are running."
        )
        st.exception(error)
        st.stop()

    total_customers = customers["customer_id"].nunique()
    total_segments = customers["segment_name"].nunique()
    total_recommendations = len(recommendations)

    average_recommendations = (
        total_recommendations / total_customers
    )

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)

    metric_1.metric(
        "Customers",
        f"{total_customers:,}",
    )

    metric_2.metric(
        "Customer Segments",
        f"{total_segments:,}",
    )

    metric_3.metric(
        "Recommendations",
        f"{total_recommendations:,}",
    )

    metric_4.metric(
        "Average per Customer",
        f"{average_recommendations:.2f}",
    )

    st.divider()

    segment_summary = (
        customers
        .groupby("segment_name", as_index=False)
        .agg(
            customer_count=("customer_id", "nunique"),
            average_balance=("average_balance", "mean"),
            average_product_count=(
                "banking_product_count",
                "mean",
            ),
        )
        .sort_values(
            "customer_count",
            ascending=False,
        )
    )

    segment_summary["customer_percentage"] = (
        segment_summary["customer_count"]
        / total_customers
        * 100
    )

    recommendation_summary = (
        recommendations
        .groupby("recommended_product", as_index=False)
        .agg(
            recommendation_count=(
                "recommendation_id",
                "count",
            ),
            average_score=(
                "recommendation_score",
                "mean",
            ),
        )
        .sort_values(
            "recommendation_count",
            ascending=False,
        )
    )

    segment_chart = (
        alt.Chart(segment_summary)
        .mark_bar(
            color="#4C78A8",
            cornerRadiusEnd=4,
        )
        .encode(
            x=alt.X(
                "customer_count:Q",
                title="Number of Customers",
            ),
            y=alt.Y(
                "segment_name:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=250),
            ),
            tooltip=[
                alt.Tooltip(
                    "segment_name:N",
                    title="Segment",
                ),
                alt.Tooltip(
                    "customer_count:Q",
                    title="Customers",
                    format=",",
                ),
                alt.Tooltip(
                    "customer_percentage:Q",
                    title="Percentage",
                    format=".2f",
                ),
            ],
        )
        .properties(height=350)
    )

    recommendation_chart = (
        alt.Chart(recommendation_summary)
        .mark_bar(
            color="#59A14F",
            cornerRadiusEnd=4,
        )
        .encode(
            x=alt.X(
                "recommendation_count:Q",
                title="Number of Recommendations",
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
        .properties(height=350)
    )

    left_chart, right_chart = st.columns(2)

    with left_chart:
        st.subheader("Customers by Segment")

        st.altair_chart(
            segment_chart,
            use_container_width=True,
        )

    with right_chart:
        st.subheader("Recommendations by Product")

        st.altair_chart(
            recommendation_chart,
            use_container_width=True,
        )

    st.subheader("Segment Summary")

    display_summary = segment_summary.copy()

    display_summary["average_balance"] = (
        display_summary["average_balance"].round(2)
    )

    display_summary["average_product_count"] = (
        display_summary["average_product_count"].round(2)
    )

    display_summary["customer_percentage"] = (
        display_summary["customer_percentage"].round(2)
    )

    display_summary = display_summary.rename(
        columns={
            "segment_name": "Segment",
            "customer_count": "Customers",
            "average_balance": "Average Balance",
            "average_product_count": "Average Products",
            "customer_percentage": "Customer Percentage",
        }
    )

    st.dataframe(
        display_summary,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Customer Recommendation Explorer")

    customer_ids = sorted(
        customers["customer_id"].unique()
    )

    selected_customer_id = st.selectbox(
        "Select a customer",
        options=customer_ids,
        format_func=lambda customer_id: (
            f"Customer {int(customer_id)}"
        ),
    )

    st.caption(
        "Customer IDs come from the original banking dataset and are not "
        "sequential. Only the 4,500 primary account owners included in the "
        "segmentation model appear here, so some ID numbers are expected "
        "to be missing."
    )

    selected_customer = customers.loc[
        customers["customer_id"] == selected_customer_id
    ].iloc[0]

    customer_recommendations = (
        recommendations.loc[
            recommendations["customer_id"]
            == selected_customer_id
        ]
        .sort_values("recommendation_rank")
    )

    customer_metric_1, customer_metric_2, customer_metric_3 = (
        st.columns(3)
    )

    customer_metric_1.metric(
        "Segment",
        selected_customer["segment_name"],
    )

    customer_metric_2.metric(
        "Average Balance",
        f"{selected_customer['average_balance']:,.2f}",
    )

    customer_metric_3.metric(
        "Banking Products",
        int(selected_customer["banking_product_count"]),
    )

    st.write("Recommended Products")

    recommendation_display = customer_recommendations[
        [
            "recommendation_rank",
            "recommended_product",
            "recommendation_score",
            "recommendation_reason",
        ]
    ].rename(
        columns={
            "recommendation_rank": "Rank",
            "recommended_product": "Recommended Product",
            "recommendation_score": "Score",
            "recommendation_reason": "Reason",
        }
    )

    st.dataframe(
        recommendation_display,
        use_container_width=True,
        hide_index=True,
    )
    st.success("Dashboard data loaded successfully.")


if __name__ == "__main__":
    main()