-- dbt view: per-store daily sales, reusable in dashboards and downstream reporting.
with sales as (
    select store_id, sale_date, quantity, unit_price_eur
    from {{ source('retailops_raw', 'sales') }}
),
stores as (
    select id, name, region, city
    from {{ source('retailops_raw', 'stores') }}
)
select
    concat(s.store_id, '-', cast(s.sale_date as text)) as store_day_key,
    s.store_id,
    st.name as store_name,
    st.city,
    st.region,
    s.sale_date,
    sum(s.quantity) as total_units,
    round(sum((s.quantity * s.unit_price_eur)::numeric), 2) as revenue_eur
from sales s
join stores st on s.store_id = st.id
group by s.store_id, st.name, st.city, st.region, s.sale_date
