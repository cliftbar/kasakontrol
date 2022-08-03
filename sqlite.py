from abc import abstractmethod
from typing import Type

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()


# https://stackoverflow.com/questions/49581907/when-inheriting-sqlalchemy-class-from-abstract-class-exception-thrown-metaclass
class BaseWithMigrations(Base):
    __abstract__ = True

    @classmethod
    @abstractmethod
    def migrations(cls) -> list[str]:
        pass


class SqliteStore:
    def __init__(self, db_filename: str, models: list[Type[BaseWithMigrations]]):
        self.engine = create_engine(f"sqlite:///{db_filename}.sqlite", echo=False, future=True)
        Base.metadata.create_all(self.engine)

        self.session: Session = Session(self.engine)
        with self.session.begin() as tx:
            for model in models:
                for migration in model.migrations():
                    self.ddl_statement(self.session, migration)
            print(f"migrations done")
            tx.commit()

    @staticmethod
    def ddl_statement(session: Session, statement: str):
        # print(statement)
        try:
            session.execute(statement)
        except OperationalError as oe:
            msg = str(oe)
            # print(msg)
            if "duplicate" not in msg:
                raise oe
        except IntegrityError as ie:
            msg = str(ie)
            # print(msg)
            if "UNIQUE constraint failed" not in msg:
                raise ie

    def store_row(self, row: Base):
        return self.store_rows([row])

    def store_rows(self, rows: list[Base]):
        with self.session.begin():
            self.session.add_all(rows)
            self.session.commit()

    def fetch_rows(self, stmt):
        # with self.session.begin():
        print(stmt)
        res = self.session.execute(statement=stmt).all()[0]

        return res
