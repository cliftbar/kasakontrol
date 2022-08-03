# pip install sqlalchemy matplotlib
import matplotlib.pyplot as plt
from matplotlib.pyplot import Axes

from sqlalchemy import Column, TEXT, create_engine, INTEGER
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, Session

# SQLAlchemy Setup
Base = declarative_base()
engine = create_engine(f"sqlite:///timeseries_test.sqlite", echo=False, future=True)


class Timeseries(Base):
    __tablename__ = "timeseries"

    series_id: str = Column(TEXT, primary_key=True, nullable=False)
    ts: int = Column(INTEGER, primary_key=True, nullable=False)
    version_ts: int = Column(INTEGER, primary_key=True, nullable=False)
    value: int = Column(INTEGER, nullable=False)


# Create table
Base.metadata.create_all(engine)

# Test Data
series_1: list[Timeseries] = []
max_version: int = 3
for version_ts in range(0, max_version):
    ts_0: int = 0 + version_ts  # Comment out addition of version_ts to create Versioned Points dataset
    ts_step: int = 3
    for ts in range(ts_0, 30, ts_step):
        row = Timeseries(series_id="id1", ts=ts, version_ts=version_ts, value=(version_ts + 1))
        series_1.append(row)

if True:  # False to skip re-adding data to DB, but PK will prevent dupes and the try-catch skips the dupe errors
    try:
        with Session(engine) as session:
            session.add_all(series_1)
            session.commit()
    except IntegrityError as ie:
        print("data already loaded")


# Matplotlib setup
obs_axs: list[Axes]
obs_fig, obs_axs = plt.subplots(2)
version_colors = ["ro", "go", "bo"]

# "Normal" point versioned data query: get the latest at each timestamp
versioned_points_sql: str = """
WITH ver AS (
    SELECT
        MAX(version_ts) as max_ver,
        ts
    FROM timeseries
    WHERE {0} <= ts  -- Python Variable Substitution Here
    GROUP BY ts, series_id
)
SELECT
    t.ts,
    t.version_ts,
    t.value
FROM timeseries AS t
INNER JOIN ver
    ON ver.ts = t.ts
        AND ver.max_ver = t.version_ts
ORDER BY t.ts DESC
"""

since_ts: int = 0
sql = versioned_points_sql.format(since_ts)
with Session(engine) as session:
    res_proxy = session.execute(sql)
    data: list[Timeseries] = [row for row in res_proxy]

# Build point plot
obs_axs[0].plot([d[0] for d in data], [d[2] for d in data], "k")
for ver in range(0, max_version):
    x = [d[0] for d in data if d[1] == ver]
    y = [d[2] for d in data if d[1] == ver]
    obs_axs[0].plot(x, y, version_colors[ver])
    obs_axs[0].set_title("Versioned Points")
    obs_axs[0].legend(["data", "version 0", "version 1", "version 2"])

# Scenario versioned query: Consider versions continuous
versioned_points_sql: str = """
WITH cte AS (
    SELECT
        version_ts,
        MIN(ts) as min_ts,
        LAG(ts, 1, NULL) OVER (ORDER BY version_ts DESC) as lag_ts
    FROM timeseries
    WHERE {0} <= ts  -- Python Variable Substitution Here
    GROUP BY version_ts, series_id
)
SELECT
    t.ts,
    t.version_ts,
    t.value
FROM timeseries t
INNER JOIN cte
    ON t.version_ts = cte.version_ts
        AND cte.min_ts <= t.ts
        AND t.ts < ifnull(lag_ts, t.ts+1)
ORDER BY t.ts DESC;
"""

since_ts: int = 0
sql = versioned_points_sql.format(since_ts)
with Session(engine) as session:
    res_proxy = session.execute(sql)
    data: list[Timeseries] = [row for row in res_proxy]


# Build scenario plot
obs_axs[1].plot([d[0] for d in data], [d[2] for d in data], "k")
for ver in range(0, max_version):
    x = [d[0] for d in data if d[1] == ver]
    y = [d[2] for d in data if d[1] == ver]
    obs_axs[1].plot(x, y, version_colors[ver])
    obs_axs[1].set_title("Versioned Scenario")
    obs_axs[1].legend(["data", "version 0", "version 1", "version 2"])

plt.show()
