"""
Pull CONTINUOUS XAU/USD (and XAG where available) bars straight from TimescaleDB
via server-side time_bucket, now that the gap has been backfilled. Writes M15
bars parquet for the rebuilt continuous study.
"""
import os
import psycopg
import pandas as pd

URL = os.environ["TIGERDATA_URL"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

BAR_SQL = """
select time_bucket(%s, time) as time,
       first(ltp, time) as open,
       max(ltp)         as high,
       min(ltp)         as low,
       last(ltp, time)  as close,
       count(*)         as ticks
from ltp
where symbol = %s
group by 1
order by 1
"""


def pull(symbol, bucket, fname):
    with psycopg.connect(URL) as conn:
        df = pd.read_sql(BAR_SQL, conn, params=(bucket, symbol))
    df["time"] = pd.to_datetime(df["time"], utc=True)
    path = os.path.join(OUT, fname)
    df.to_parquet(path, index=False)
    print(f"{symbol} {bucket}: {len(df):,} bars  {df['time'].min()} -> {df['time'].max()}  -> {fname}")
    return df


if __name__ == "__main__":
    pull("XAU_USD", "15 minutes", "cont_xau_M15.parquet")
    pull("XAG_USD", "15 minutes", "cont_xag_M15.parquet")
