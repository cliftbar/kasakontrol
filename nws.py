from datetime import datetime

import pytz
import requests

from rocketry import Rocketry
from requests import Response
from rocketry.conditions.api import cron
from sqlite import SqliteStore
from timeseries import Timeseries, TimeseriesID, DatetimeMask, NumericTimeseries

app: Rocketry = Rocketry(config={
    'task_execution': 'thread'
})

ds: SqliteStore = SqliteStore("timeseries", [Timeseries, TimeseriesID, DatetimeMask])


# https://forecast.weather.gov/MapClick.php?lat=45.5234&lon=-122.6762&lg=ep&FcstType=graphical
# https://api.weather.gov/points/45.53,-122.67
# https://api.weather.gov/gridpoints/PQR/112,103/forecast/hourly
def collect_forecasts(data_ts: datetime) -> list[Timeseries]:
    resp: Response = requests.get("https://api.weather.gov/gridpoints/PQR/112,103/forecast/hourly", timeout=10)

    periods: list[dict] = resp.json()["properties"]["periods"]
    ret: list[Timeseries] = []
    for p in periods[:24]:
        ts: datetime = datetime.fromisoformat(p.pop("startTime")).astimezone(pytz.UTC)
        temp: float = p["temperature"]

        row: NumericTimeseries = NumericTimeseries(series_id="nws-hourly-forecast",
                                                   ts=ts,
                                                   value_=temp,
                                                   version_ts=data_ts,
                                                   row_metadata=p)
        ret.append(row)

    return ret


# https://api.weather.gov/stations/KPDX/observations/latest
def current_observation(data_ts: datetime) -> list[Timeseries]:
    resp: Response = requests.get("https://api.weather.gov/stations/KPDX/observations/latest")
    obs: dict = resp.json()["properties"]

    ts: datetime = datetime.fromisoformat(obs["timestamp"]).astimezone(pytz.UTC)
    temp: float = obs["temperature"]["value"]

    row: NumericTimeseries = NumericTimeseries(series_id="nws-observations",
                                               ts=ts,
                                               value_=temp,
                                               version_ts=data_ts,
                                               row_metadata=obs)

    return [row]


@app.task("daily between 00:00 and 11:59 | daily between 12:00 and 23:59")
def twice_a_day_loop():
    data_ts: datetime = datetime.now(tz=pytz.UTC)
    forecasts: list[Timeseries] = collect_forecasts(data_ts)
    # print("forecast store")
    ds.store_rows(forecasts)
    print(f"forecast stored at {data_ts.isoformat()}")

    # stmt: GenericQuery[NumericTimeseries] = (select(NumericTimeseries).offset(1).limit(1)
    #                                          .order_by(desc(NumericTimeseries.version_ts)))
    # rows = datastore.fetch_entities(stmt)
    # print(f"{rows[0].value} {type(rows[0].value)}")
    # stmt: GenericQuery[Timeseries] = select(Timeseries).limit(1)
    # tsrows: list[Timeseries] = datastore.fetch_entities(stmt)
    # print(f"{tsrows[0].value} {type(tsrows[0].value)}")


@app.task(cron("*/20 * * * *"))
def minutely_loop():
    data_ts: datetime = datetime.now(tz=pytz.UTC)
    obs: list[Timeseries] = current_observation(data_ts)
    # print("hi minutely")
    ds.store_rows(obs)
    print(f"Observation stored at {data_ts.isoformat()}")


if __name__ == "__main__":
    print("run")
    app.run()
    # twice_a_day_loop()
