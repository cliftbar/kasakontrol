from datetime import datetime
from typing import Any, Union

import sqlalchemy
from sqlalchemy import Column, func, TEXT, types
from sqlalchemy.dialects.sqlite import DATETIME
from sqlalchemy.ext.hybrid import hybrid_property

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

    # @declared_attr
    # def value(self) -> str:
    #     return Column("value", TEXT, nullable=False)

    @property
    def value(self) -> str:
        return self.value_

    @value.setter
    def value(self, value: str) -> None:
        self.value_ = value
    # #
    # # @value.setter
    # def value(self, value: str) -> None:
    #     self._value = str(value)

    @classmethod
    def migrations(cls) -> list[str]:
        return []


# class Timeseries(BaseWithMigrations):
#     __tablename__ = "timeseries"
#
#     series_id: str = Column(TEXT, primary_key=True, nullable=False)
#     ts: datetime = Column(DATETIME, primary_key=True, nullable=False)
#     version_ts: datetime = Column(DATETIME, primary_key=True, nullable=False)
#     _value: str = Column("value", TEXT, nullable=False)
#     row_metadata: dict = Column(sqlalchemy.JSON)
#     created_at: datetime = Column(DATETIME, server_default=func.now())
#
#     # @declared_attr
#     # def value(self) -> str:
#     #     return Column("value", TEXT, nullable=False)
#
#     @hybrid_property
#     def value(self) -> str:
#         return self._value
#
#     @value.setter
#     def value(self, value: str) -> None:
#         self._value = value
#     # #
#     # # @value.setter
#     # def value(self, value: str) -> None:
#     #     self._value = str(value)
#
#     @classmethod
#     def migrations(cls) -> list[str]:
#         return []
