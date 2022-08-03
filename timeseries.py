from enum import Enum
from typing import Union

import sqlalchemy
from sqlalchemy import Column, func, TEXT, types
from sqlalchemy.dialects.sqlite import DATETIME

from sqlite import BaseWithMigrations

from time import mktime
from datetime import datetime


class TimeseriesValue(types.TypeDecorator):
    """Used for working with epoch timestamps.

Converts datetimes into epoch on the way in.
    Converts epoch timestamps to datetimes on the way out.
    """
    impl = types.TEXT

    def process_bind_param(self, value, dialect):

        return mktime(value.timetuple())

    def process_result_value(self, value, dialect):
        return datetime.fromtimestamp(value)


class Timeseries(BaseWithMigrations):
    __tablename__ = "timeseries"

    series_id: str = Column(TEXT, primary_key=True, nullable=False)
    ts: datetime = Column(DATETIME, primary_key=True, nullable=False)
    version_ts: datetime = Column(DATETIME, primary_key=True, nullable=False)
    value_: Union[str, float] = Column("value", TEXT, nullable=False)
    row_metadata: dict = Column(sqlalchemy.JSON)
    created_at: datetime = Column(DATETIME, server_default=func.now())

    @property
    def value(self) -> str:
        return self.value_

    @value.setter
    def value(self, value: str) -> None:
        self.value_ = value

    @classmethod
    def migrations(cls) -> list[str]:
        return []


class NumericTimeseries(Timeseries):
    @property
    def value(self) -> float:
        return float(self.value_)

    @value.setter
    def value(self, value: float) -> None:
        self.value_ = str(value)


class TimeseriesID(BaseWithMigrations):
    __tablename__ = "timeseries_id"

    series_id: str = Column(TEXT, primary_key=True, nullable=False)
    row_metadata: str = Column(sqlalchemy.JSON)

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
    mask: str = Column(TEXT, primary_key=True, nullable=False)

    @classmethod
    def migrations(cls) -> list[str]:
        return [f"INSERT INTO {cls.__tablename__} VALUES ('{e.name}', '{e.value}');" for e in cls.Mask]
