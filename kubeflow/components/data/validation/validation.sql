CREATE TEMP FUNCTION PROCESS_SKUS_PURCHASED_FROM_SEARCH(searched_skus ARRAY<STRING>, purchased_skus ARRAY<STRING>) RETURNS ARRAY<STRUCT<sku STRING, purchase_flag BOOL> >  AS (
  /**
  Compares list of skus from the search results and the ones purchased; returns the intersection between the two.
  **/
  ARRAY(SELECT AS STRUCT sku, IF(EXISTS(SELECT 1 FROM UNNEST(purchased_skus) AS p_sku WHERE sku = p_sku), TRUE, FALSE) FROM UNNEST(searched_skus) AS sku)
);

CREATE TEMP FUNCTION PROCESS_CHANNEL_GROUP(channelGroup STRING) RETURNS STRING AS (
   REGEXP_REPLACE(LOWER(channelGroup), ' ', '_')
);

WITH search_data AS(
  SELECT
    fv,
    channel_group,
    ARRAY(
      SELECT AS STRUCT
        query,
        ARRAY_AGG(STRUCT(skus.sku AS sku, skus.purchase_flag AS purchase_flag)) AS skus
      FROM UNNEST(hits), UNNEST(skus) AS skus
      GROUP BY query
    ) AS hits
  FROM(
    SELECT
      fv,
      channel_group,
      ARRAY(
        SELECT AS STRUCT
          query,
          PROCESS_SKUS_PURCHASED_FROM_SEARCH(query_skus, purchased_skus) skus
        FROM UNNEST(hits)
      ) AS hits
    FROM(
      SELECT
        fullvisitorid AS fv,
        COALESCE(PROCESS_CHANNEL_GROUP(channelGrouping), '') AS channel_group,
        ARRAY(
          SELECT AS STRUCT
            page.pagepath AS query,
            ARRAY_AGG(productSKU IGNORE NULLS) AS query_skus,
          FROM UNNEST(hits) LEFT JOIN UNNEST(product)
          WHERE productSKU != '(not set)'
            AND NOT REGEXP_CONTAINS(page.pagepath, r'\.html')
          GROUP BY query
        ) AS hits,
        ARRAY(SELECT productSKU FROM UNNEST(hits), UNNEST(product) WHERE ecommerceAction.action_type = '6') AS purchased_skus
      FROM `bigquery-public-data.google_analytics_sample.ga_sessions*`
      WHERE TRUE
        AND REGEXP_EXTRACT(_TABLE_SUFFIX, r'.*_(\d+)$') BETWEEN '{validation_init_date}' AND '{validation_end_date}'
    )
  )
),
customer_data AS(
  SELECT
    fv,
    COALESCE((SELECT AVG(avg_ticket) FROM UNNEST(ticket_array) AS avg_ticket), 0) AS avg_ticket
  FROM(
    SELECT
      fullvisitorid AS fv,
      ARRAY_CONCAT_AGG(ARRAY((SELECT AVG(productPrice / 1e6) AS avg_ticket FROM UNNEST(hits), UNNEST(product)))) AS ticket_array
    FROM `bigquery-public-data.google_analytics_sample.ga_sessions*`
    WHERE TRUE
      AND REGEXP_EXTRACT(_TABLE_SUFFIX, r'.*_(\d+)$') BETWEEN '{validation_init_date}' AND '{validation_end_date}'
    GROUP BY fv
  )
)


SELECT
  STRUCT(
    query,
    COALESCE(channel_group, '') AS channel_group,
    COALESCE(CAST(avg_ticket AS INT64), 0) AS customer_avg_ticket
  ) AS search_keys,
  ARRAY_AGG(STRUCT(ARRAY(SELECT sku FROM UNNEST(skus) WHERE purchase_flag) AS purchased)) AS docs
FROM search_data LEFT JOIN customer_data USING(fv), UNNEST(hits)
WHERE ARRAY_LENGTH(ARRAY(SELECT sku FROM UNNEST(skus) WHERE purchase_flag)) > 0
GROUP BY query, channel_group, avg_ticket
