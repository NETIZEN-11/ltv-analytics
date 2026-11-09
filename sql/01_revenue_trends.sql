-- ============================================================================
-- Revenue Trend Analysis
-- Uses CTEs to aggregate monthly revenue, then window functions for:
--   - Running total revenue (cumulative)
--   - Month-over-month growth %
--   - 3-month moving average
-- ============================================================================

WITH monthly_revenue AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS order_month,
        SUM(CASE WHEN oi.is_returned = 0 THEN oi.line_revenue ELSE 0 END) AS net_revenue,
        COUNT(DISTINCT o.order_id) AS order_count,
        COUNT(DISTINCT o.customer_id) AS unique_customers
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY order_month
),

revenue_with_metrics AS (
    SELECT
        order_month,
        net_revenue,
        order_count,
        unique_customers,
        ROUND(net_revenue / NULLIF(order_count, 0), 2) AS avg_order_value,
        SUM(net_revenue) OVER (ORDER BY order_month) AS running_total_revenue,
        LAG(net_revenue) OVER (ORDER BY order_month) AS prev_month_revenue,
        AVG(net_revenue) OVER (
            ORDER BY order_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS moving_avg_3mo
    FROM monthly_revenue
)

SELECT
    order_month,
    net_revenue,
    order_count,
    unique_customers,
    avg_order_value,
    running_total_revenue,
    ROUND(moving_avg_3mo, 2) AS moving_avg_3mo,
    CASE
        WHEN prev_month_revenue IS NULL OR prev_month_revenue = 0 THEN NULL
        ELSE ROUND(100.0 * (net_revenue - prev_month_revenue) / prev_month_revenue, 2)
    END AS mom_growth_pct
FROM revenue_with_metrics
ORDER BY order_month;