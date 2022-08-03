-- Scenario Timeseries
WITH cte AS (
    SELECT
        easy_ver,
--         MAX(easy_ts) as max_ts,
        MIN(easy_ts) as min_ts,
    LAG(easy_ts, 1, NULL) OVER (ORDER BY easy_ver DESC) as lag_ts
    FROM versioned_timeseries
    WHERE DATETIME('2022-07-17 04:55:40') < DATETIME(ts)
    GROUP BY easy_ver, series_id
    ORDER BY easy_ver DESC
)
SELECT
    *
FROM versioned_timeseries vt
INNER JOIN cte
    ON vt.easy_ver = cte.easy_ver
        AND cte.min_ts <= vt.easy_ts
        AND vt.easy_ts < ifnull(lag_ts, vt.easy_ts+1)
ORDER BY easy_ts DESC;

-- Scenario Timeseries
WITH cte AS (
    SELECT
        version_ts,
--         MAX(easy_ts) as max_ts,
        MIN(ts) as min_ts,
    LAG(ts, 1, NULL) OVER (ORDER BY version_ts DESC) as lag_ts
    FROM versioned_timeseries
    WHERE DATETIME('2022-07-17 04:55:40') < DATETIME(ts)
    GROUP BY version_ts, series_id
--     ORDER BY easy_ver DESC
)
SELECT
    *
FROM versioned_timeseries vt
INNER JOIN cte
    ON vt.version_ts = cte.version_ts
        AND cte.min_ts <= vt.ts
        AND vt.ts < ifnull(lag_ts, vt.ts+1)
ORDER BY ts DESC;