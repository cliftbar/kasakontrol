WITH ver AS (
    SELECT
        MAX(DATETIME(strftime(mask.mask_value, version_ts))) as max_ver,
        MIN(DATETIME(strftime(mask.mask_value, version_ts))) as min_ver,
        DATETIME(ts) as ts_dt,
        DATETIME(strftime(mask.mask_value, ts)) AS masked_ts
    FROM versioned_timeseries
    INNER JOIN ts_mask mask
        ON 'hour' == mask.mask
    WHERE DATETIME('2022-07-17 04:55:40') < DATETIME(ts)
    GROUP BY ts, series_id
--     ORDER BY DATETIME(ts) DESC
)
SELECT
    *
FROM versioned_timeseries
    INNER JOIN ts_mask mask
        ON 'hour' == mask.mask
INNER JOIN ver
    ON ver.masked_ts = DATETIME(strftime(mask.mask_value, versioned_timeseries.ts))
        AND ver.max_ver = DATETIME(strftime(mask.mask_value, versioned_timeseries.version_ts))
ORDER BY ts_dt DESC