CREATE TEMP FUNCTION PROCESS_CHANNEL_GROUP(channelGroup STRING) RETURNS STRING AS (
   REGEXP_REPLACE(LOWER(channelGroup), ' ', '_')
);


WITH search_data AS(
  SELECT
    fv,
    ARRAY(
      SELECT AS STRUCT
        query,
        ARRAY(
          SELECT AS STRUCT
            sku, click, purchase FROM UNNEST(session_skus) WHERE IF(max_position IS NOT NULL, position <= max_position, TRUE) AND IF(click = 0, RAND() < 0.01, True)
        ) AS session_skus
      FROM UNNEST(hits)
    ) as hits
  FROM(
    SELECT
      fv,
      ARRAY(
        SELECT AS STRUCT
          query,
          ARRAY(SELECT AS STRUCT sku, click, purchase, position, MAX(IF(purchase = 1, position, NULL)) OVER() AS max_position FROM UNNEST(session_skus) ORDER BY position) AS session_skus
        FROM UNNEST(hits)
        WHERE EXISTS(SELECT 1 FROM UNNEST(session_skus) WHERE click = 1) AND (SELECT SUM(purchase) FROM UNNEST(session_skus)) <= 1
      ) AS hits
    FROM(
      SELECT
      fv,
      ARRAY(
       SELECT AS STRUCT
         query,
         ARRAY_AGG(STRUCT(h.sku AS sku, IF(purchase = 1, 1, click) AS click, purchase, position)) AS session_skus
       FROM UNNEST(hits) AS h
       GROUP BY query
     ) AS hits
     FROM(
      SELECT
        fv,
        ARRAY(
          SELECT AS STRUCT
            query,
            sku,
            MAX(click) AS click,
            MAX(IF(EXISTS(SELECT 1 FROM UNNEST(purchased_skus) AS purchased_sku where purchased_sku = sku), 1, 0)) AS purchase,
            MIN(position) AS position
          FROM UNNEST(hits)
          GROUP BY query, sku
        ) AS hits
      FROM(
        SELECT
          fullvisitorid as fv,
          ARRAY(
            SELECT AS STRUCT
              page.pagepath AS query,
              productSKU AS sku,
              IF(isClick, 1, 0) AS click,
              ROW_NUMBER() OVER() AS position
            FROM UNNEST(hits) LEFT JOIN UNNEST(product)
            WHERE TRUE
              AND productSKU != '(not set)'
              AND NOT REGEXP_CONTAINS(page.pagepath, r'\.html')

          ) AS hits,
          ARRAY(SELECT productSKU FROM UNNEST(hits), UNNEST(product) WHERE ecommerceAction.action_type = '6') AS purchased_skus
        FROM `bigquery-public-data.google_analytics_sample.ga_sessions*`
        WHERE TRUE
          AND REGEXP_EXTRACT(_TABLE_SUFFIX, r'.*_(\d+)$') BETWEEN '20170801' AND '20170801'
        )
      )
    )
  )
),
customer_data AS(
  SELECT
    fv,
    channel_group,
    COALESCE((SELECT AVG(avg_ticket) FROM UNNEST(ticket_array) AS avg_ticket), 0) AS avg_ticket
  FROM(
    SELECT
      fullvisitorid AS fv,
      COALESCE(ARRAY_AGG(PROCESS_CHANNEL_GROUP(channelGrouping) LIMIT 1)[SAFE_OFFSET(0)], '') AS channel_group,
      ARRAY_CONCAT_AGG(ARRAY((SELECT AVG(productPrice / 1e6) AS avg_ticket FROM UNNEST(hits), UNNEST(product)))) AS ticket_array
    FROM `bigquery-public-data.google_analytics_sample.ga_sessions*`
    WHERE TRUE
      AND REGEXP_EXTRACT(_TABLE_SUFFIX, r'.*_(\d+)$') BETWEEN '20170801' AND '20170801'
    GROUP BY fv
  )
)


SELECT
  STRUCT(
    query,
    COALESCE(channel_group, '') AS channel_group,
    COALESCE(CAST(avg_ticket AS INT64), 0) AS customer_avg_ticket
  ) AS search_keys,
  ARRAY_AGG(STRUCT(session_skus AS session)) AS clickstream
FROM search_data LEFT JOIN customer_data USING(fv), UNNEST(hits)
WHERE ARRAY_LENGTH(session_skus) BETWEEN 3 AND 500
GROUP BY query, channel_group,avg_ticket
