SELECT
  sku,
  name,
  category,
  COALESCE(global_price, 0) AS price,
  STRUCT(
    STRUCT(
      COALESCE(global_impressions, 0) AS impressions,
      COALESCE(global_clicks, 0) AS clicks,
      COALESCE(IF(MAX(global_clicks) / MAX(global_impressions) > 1, 1, MAX(global_clicks) / MAX(global_impressions)), 0) AS CTR
    ) AS global,
    STRUCT(
      CASE WHEN channel = 'Organic Search' THEN STRUCT(COALESCE(IF(SUM(clicks) / COALESCE(SUM(impressions), 1) > 1, 1, SUM(clicks) / COALESCE(SUM(impressions), 1)), 0) AS CTR) ELSE STRUCT(0 AS CTR) END AS organic_search,
      CASE WHEN channel = 'Direct' THEN STRUCT(COALESCE(IF(SUM(clicks) / COALESCE(SUM(impressions), 1) > 1, 1, SUM(clicks) / COALESCE(SUM(impressions), 1)), 0) AS CTR) ELSE STRUCT(0 AS CTR) END AS direct,
      CASE WHEN channel = 'Referral' THEN STRUCT(COALESCE(IF(SUM(clicks) / COALESCE(SUM(impressions), 1) > 1, 1, SUM(clicks) / COALESCE(SUM(impressions), 1)), 0) AS CTR) ELSE STRUCT(0 AS CTR) END AS referral,
      CASE WHEN channel = 'Paid Search' THEN STRUCT(COALESCE(IF(SUM(clicks) / COALESCE(SUM(impressions), 1) > 1, 1, SUM(clicks) / COALESCE(SUM(impressions), 1)), 0) AS CTR) ELSE STRUCT(0 AS CTR) END AS paid_search,
      CASE WHEN channel = 'Display' THEN STRUCT(COALESCE(IF(SUM(clicks) / COALESCE(SUM(impressions), 1) > 1, 1, SUM(clicks) / COALESCE(SUM(impressions), 1)), 0) AS CTR) ELSE STRUCT(0 AS CTR) END AS display,
      CASE WHEN channel = 'Affiliates' THEN STRUCT(COALESCE(IF(SUM(clicks) / COALESCE(SUM(impressions), 1) > 1, 1, SUM(clicks) / COALESCE(SUM(impressions), 1)), 0) AS CTR) ELSE STRUCT(0 AS CTR) END AS affiliates,
      CASE WHEN channel = 'Social' THEN STRUCT(COALESCE(IF(SUM(clicks) / COALESCE(SUM(impressions), 1) > 1, 1, SUM(clicks) / COALESCE(SUM(impressions), 1)), 0) AS CTR) ELSE STRUCT(0 AS CTR) END AS social
    ) AS channel
  ) AS performances
FROM(
  SELECT DISTINCT
    sku,
    channel,
    name,
    REGEXP_REPLACE(category, '/', ' ') AS category,
    SUM(impressions) OVER(PARTITION BY sku) AS global_impressions,
    impressions,
    SUM(clicks) OVER(PARTITION BY sku) AS global_clicks,
    clicks,
    AVG(price) OVER(PARTITION BY sku) AS global_price,
  FROM(
    SELECT
      ARRAY(
        SELECT AS STRUCT
          channelGrouping AS channel,
          productSku AS sku,
          v2ProductCategory AS category,
          v2ProductName AS name,
          SUM(CAST(isImpression AS INT64)) AS impressions,
          SUM(CAST(isClick AS INT64)) AS clicks,
          AVG(productPrice / 1e6) AS price
        FROM UNNEST(hits), UNNEST(product)
        GROUP BY channel, sku, category, name
      ) AS products
    FROM `bigquery-public-data.google_analytics_sample.ga_sessions*`
    WHERE TRUE
      AND REGEXP_EXTRACT(_TABLE_SUFFIX, r'.*_(\d+)$') BETWEEN '20160801' AND '20170801'
  ), UNNEST(products)
)
WHERE TRUE
  AND global_impressions > 0
GROUP BY
  sku,
  channel,
  name,
  category,
  global_impressions,
  global_clicks,
  global_price
