CREATE TEMP FUNCTION PROCESS_CHANNEL_GROUP(channelGroup STRING) RETURNS STRING AS (
   REGEXP_REPLACE(LOWER(channelGroup), ' ', '_')
);


WITH search_data AS(
  SELECT
    fv,
    ARRAY(
      SELECT AS STRUCT
        query as search_term,
        ARRAY(
          SELECT AS STRUCT
            doc, click, purchase FROM UNNEST(session_docs) WHERE IF(max_position IS NOT NULL, position <= max_position, TRUE) AND IF(click = 0, RAND() < 0.01, True)
        ) AS session_docs
      FROM UNNEST(hits)
    ) as hits
  FROM(
    SELECT
      fv,
      ARRAY(
        SELECT AS STRUCT
          query,
          ARRAY(SELECT AS STRUCT doc, click, purchase, position, MAX(IF(purchase = 1, position, NULL)) OVER() AS max_position FROM UNNEST(session_docs) ORDER BY position) AS session_docs
        FROM UNNEST(hits)
        WHERE EXISTS(SELECT 1 FROM UNNEST(session_docs) WHERE click = 1) AND (SELECT SUM(purchase) FROM UNNEST(session_docs)) <= 1
      ) AS hits
    FROM(
      SELECT
      fv,
      ARRAY(
       SELECT AS STRUCT
         query,
         ARRAY_AGG(STRUCT(h.doc AS doc, IF(purchase = 1, 1, click) AS click, purchase, position)) AS session_docs
       FROM UNNEST(hits) AS h
       GROUP BY query
     ) AS hits
     FROM(
      SELECT
        fv,
        ARRAY(
          SELECT AS STRUCT
            query,
            doc,
            MAX(click) AS click,
            MAX(IF(EXISTS(SELECT 1 FROM UNNEST(purchased_docs) AS purchased_doc where purchased_doc = doc), 1, 0)) AS purchase,
            MIN(position) AS position
          FROM UNNEST(hits)
          GROUP BY query, doc
        ) AS hits
      FROM(
        SELECT
          fullvisitorid as fv,
          ARRAY(
            SELECT AS STRUCT
              page.pagepath AS query,
              productSKU AS doc,
              IF(isClick, 1, 0) AS click,
              ROW_NUMBER() OVER() AS position
            FROM UNNEST(hits) LEFT JOIN UNNEST(product)
            WHERE TRUE
              AND productSKU != '(not set)'
              AND NOT REGEXP_CONTAINS(page.pagepath, r'\.html')

          ) AS hits,
          ARRAY(SELECT productSKU FROM UNNEST(hits), UNNEST(product) WHERE ecommerceAction.action_type = '6') AS purchased_docs
        FROM `bigquery-public-data.google_analytics_sample.ga_sessions*`
        WHERE TRUE
          AND REGEXP_EXTRACT(_TABLE_SUFFIX, r'.*_(\d+)$') BETWEEN '{train_init_date}' AND '{train_end_date}'
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
      AND REGEXP_EXTRACT(_TABLE_SUFFIX, r'.*_(\d+)$') BETWEEN '{train_init_date}' AND '{train_end_date}'
    GROUP BY fv
  )
)


SELECT
  STRUCT(
    search_term,
    COALESCE(channel_group, '') AS channel_group,
    COALESCE(CAST(avg_ticket AS INT64), 0) AS customer_avg_ticket
  ) AS search_keys,
  ARRAY_AGG(STRUCT(session_docs AS session)) AS judgment_keys
FROM search_data LEFT JOIN customer_data USING(fv), UNNEST(hits)
WHERE ARRAY_LENGTH(session_docs) BETWEEN 3 AND 500
GROUP BY search_term, channel_group,avg_ticket
