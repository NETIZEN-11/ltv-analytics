-- ============================================================================
-- Customer Order Frequency Analysis
-- Uses window functions to compute, per customer:
--   - order sequence number (1st order, 2nd order, etc.)
--   - days since previous order
--   - total lifetime orders & revenue
--   - a frequency rank across all customers
-- ============================================================================

WITH customer_orders AS (
    SELECT
        o.customer_id,
        o.order_id,
        o.order_date,
        SUM(oi.line_revenue) AS order_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE oi.is_returned = 0
    GROUP BY o.customer_id, o.order_id, o.order_date
),

order_sequence AS (
    SELECT
        customer_id,
        order_id,
        order_date,
        order_revenue,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS order_seq_num,
        julianday(order_date) - julianday(
            LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)
        ) AS days_since_prev_order
    FROM customer_orders
),

customer_summary AS (
    SELECT
        customer_id,
        COUNT(order_id) AS total_orders,
        SUM(order_revenue) AS lifetime_revenue,
        ROUND(AVG(days_since_prev_order), 1) AS avg_days_between_orders,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date
    FROM order_sequence
    GROUP BY customer_id
)

SELECT
    customer_id,
    total_orders,
    ROUND(lifetime_revenue, 2) AS lifetime_revenue,
    avg_days_between_orders,
    first_order_date,
    last_order_date,
    RANK() OVER (ORDER BY total_orders DESC) AS frequency_rank,
    NTILE(4) OVER (ORDER BY lifetime_revenue DESC) AS revenue_quartile
FROM customer_summary
ORDER BY total_orders DESC, lifetime_revenue DESC
LIMIT 500;