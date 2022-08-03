from datetime import datetime
from enum import Enum
from typing import Any

import pytz
import requests
import sqlalchemy

from rocketry import Rocketry
from requests import Response
from sqlalchemy import Column, Text, event, INTEGER, cast, select, desc
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import InstrumentedAttribute

from sqlite import SqliteStore, BaseWithMigrations
from timeseries import Timeseries

app: Rocketry = Rocketry()


# https://forecast.weather.gov/MapClick.php?lat=45.5234&lon=-122.6762&lg=ep&FcstType=graphical
# https://api.weather.gov/points/45.53,-122.67
# https://api.weather.gov/gridpoints/PQR/112,103/forecast/hourly
class TemperatureTimeseries(Timeseries):
    # @hybrid_property
    # def value(self) -> str:
    #     return self._value
    #
    # @value.setter
    # def value(self, value: float) -> None:
    #     self._value = str(value)
    #
    # @value.getter()
    # def value(self) -> float:
    #     col: InstrumentedAttribute = self._value
    #     return col.

    @property
    def value(self) -> float:
        return float(self.value_)

    @value.setter
    def value(self, value: float) -> None:
        self.value_ = str(value)




class TimeseriesID(BaseWithMigrations):
    __tablename__ = "timeseries_id"

    series_id: str = Column(Text, primary_key=True, nullable=False)
    row_metadata: str = Column(JSON)

    @classmethod
    def migrations(cls) -> list[str]:
        return []


class DatetimeMask(BaseWithMigrations):
    class Mask(Enum):
        second = "%Y-%m-%d %H:%M:%S+00:00"
        minute = "%Y-%m-%d %H:%M:00+00:00"
        hour = "%Y-%m-%d %H:00:00+00:00"
        day = "%Y-%m-%d 00:00:00+00:00"

    __tablename__ = "datetime_mask"

    mask_name: Mask = Column(sqlalchemy.Enum(Mask), primary_key=True, nullable=False)
    mask: str = Column(Text, primary_key=True, nullable=False)

    @classmethod
    def migrations(cls) -> list[str]:
        return [f"INSERT INTO {cls.__tablename__} VALUES ('{e.name}', '{e.value}');" for e in cls.Mask]


@app.task("daily between 00:00 and 11:59 | daily between 12:00 and 23:59")
def data_collect_loop():
    datastore: SqliteStore = SqliteStore("timeseries", [Timeseries, TimeseriesID, DatetimeMask])

    data_ts: datetime = datetime.now(tz=pytz.UTC)
    resp: Response = requests.get("https://api.weather.gov/gridpoints/PQR/112,103/forecast/hourly")

    periods: list[dict] = resp.json()["properties"]["periods"]
    periods_to_store: list[Timeseries] = []
    for p in periods[:1]:
        ts: datetime = datetime.fromisoformat(p.pop("startTime")).astimezone(pytz.UTC)
        temp: float = p["temperature"]

        row: TemperatureTimeseries = TemperatureTimeseries(series_id="nws-hourly-forecast",
                                                           ts=ts,
                                                           value_=temp,
                                                           version_ts=data_ts,
                                                           row_metadata=p)
        periods_to_store.append(row)
    for p in periods[1:2]:
        ts: datetime = datetime.fromisoformat(p.pop("startTime")).astimezone(pytz.UTC)
        temp: float = p["temperature"]
        tsrow: Timeseries = Timeseries(series_id="nws-hourly-forecast",
                                       ts=ts,
                                       value_="test",
                                       version_ts=data_ts,
                                       row_metadata=p)
        periods_to_store.append(tsrow)
        # tsrow.value = str(temp)
        # row.value = temp
        # a = row.value
        # periods_to_store.append(row)
        # periods_to_store.append(tsrow)

    datastore.store_rows(periods_to_store)
    rows: TemperatureTimeseries = datastore.fetch_rows(select(TemperatureTimeseries).offset(1).limit(1).order_by(desc(TemperatureTimeseries.version_ts)))[0]
    print(f"{rows.value} {type(rows.value)}")
    tsrows: Timeseries = datastore.fetch_rows(select(Timeseries).limit(1))[0]
    print(f"{tsrows.value} {type(tsrows.value)}")

    print(f"forecast stored at {data_ts.isoformat()}")


if __name__ == "__main__":
    # app.run()
    data_collect_loop()
