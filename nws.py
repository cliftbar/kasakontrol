from datetime import datetime

import pytz
import requests

from rocketry import Rocketry
from requests import Response
from sqlalchemy import desc
from sqlalchemy.future import select
from sqlite import SqliteStore,  GenericQuery
from timeseries import Timeseries, TimeseriesID, DatetimeMask, NumericTimeseries

app: Rocketry = Rocketry()


# https://forecast.weather.gov/MapClick.php?lat=45.5234&lon=-122.6762&lg=ep&FcstType=graphical
# https://api.weather.gov/points/45.53,-122.67
# https://api.weather.gov/gridpoints/PQR/112,103/forecast/hourly


@app.task("daily between 00:00 and 11:59 | daily between 12:00 and 23:59")
def data_collect_loop():
    datastore: SqliteStore = SqliteStore("timeseries", [Timeseries, TimeseriesID, DatetimeMask])

    data_ts: datetime = datetime.now(tz=pytz.UTC)
    resp: Response = requests.get("https://api.weather.gov/gridpoints/PQR/112,103/forecast/hourly")

    periods: list[dict] = resp.json()["properties"]["periods"]
    periods_to_store: list[Timeseries] = []
    for p in periods[:24]:
        ts: datetime = datetime.fromisoformat(p.pop("startTime")).astimezone(pytz.UTC)
        temp: float = p["temperature"]

        row: NumericTimeseries = NumericTimeseries(series_id="nws-hourly-forecast",
                                                   ts=ts,
                                                   value_=temp,
                                                   version_ts=data_ts,
                                                   row_metadata=p)
        periods_to_store.append(row)

    datastore.store_rows(periods_to_store)

    stmt: GenericQuery[NumericTimeseries] = (select(NumericTimeseries).offset(1).limit(1)
                                             .order_by(desc(NumericTimeseries.version_ts)))
    rows = datastore.fetch_entities(stmt)
    print(f"{rows[0].value} {type(rows[0].value)}")
    stmt: GenericQuery[Timeseries] = select(Timeseries).limit(1)
    tsrows: list[Timeseries] = datastore.fetch_entities(stmt)
    print(f"{tsrows[0].value} {type(tsrows[0].value)}")

    print(f"forecast stored at {data_ts.isoformat()}")


if __name__ == "__main__":
    app.run()
    # data_collect_loop()
