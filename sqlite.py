from abc import abstractmethod
from enum import Enum
from typing import Type, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, Session, Query, sessionmaker, scoped_session

Base = declarative_base()


class GenericTypeVar(TypeVar, _root=True):
    def __getitem__(self, item): pass
# add more items to count as a "query" here
GenericQuery = GenericTypeVar("GenericQuery", Query, select)
M = GenericTypeVar("M")


# https://stackoverflow.com/questions/49581907/when-inheriting-sqlalchemy-class-from-abstract-class-exception-thrown-metaclass
class BaseWithMigrations(Base):
    __abstract__ = True

    @classmethod
    @abstractmethod
    def migrations(cls) -> list[str]:
        pass


class SqliteStore:
    class ParallelizationMode(Enum):
        main = "main"
        threaded = "threaded"

    def __init__(self, db_filename: str, models: list[Type[BaseWithMigrations]], ):
        self.engine = create_engine(f"sqlite:///{db_filename}.sqlite", echo=False, future=True)
        Base.metadata.create_all(self.engine)

        # self.session_factory = sessionmaker(bind=self.engine)

        self.session: Session = Session(self.engine)
        with self.session.begin() as tx:
            for model in models:
                for migration in model.migrations():
                    self.ddl_statement(self.session, migration)
            print(f"migrations done")
            tx.commit()

    @staticmethod
    def ddl_statement(session: Session, statement: str):
        try:
            session.execute(statement)
        except OperationalError as oe:
            msg = str(oe)
            if "duplicate" not in msg:
                raise oe
        except IntegrityError as ie:
            msg = str(ie)
            if "UNIQUE constraint failed" not in msg:
                raise ie

    def store_row(self, row: Base):
        return self.store_rows([row])

    def store_rows(self, rows: list[Base]):
        # session = scoped_session(self.session_factory) if new_session else self.session
        session: Session = self.session
        with session.begin():
            session.add_all(rows)

    def fetch_entities(self, stmt: GenericQuery[M], ) -> list[M]:
        res: list[M] = self.session.execute(statement=stmt).scalars().all()

        return res
