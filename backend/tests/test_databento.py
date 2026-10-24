import os
from datetime import datetime, timedelta, timezone

import databento as db
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DATABENTO_API_KEY")
if not API_KEY:
    raise SystemExit("Set DATABENTO_API_KEY in backend/.env")

client = db.Historical(API_KEY)

# Use a fixed, known-open historical window (avoids "end after available end").
# Use data safely older than 24 hours to stay within free credits.
end = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
start = end - timedelta(hours=6)
print(f"Requesting NQ.v.0 ohlcv-1m from {start} to {end}")

data = client.timeseries.get_range(
    dataset="GLBX.MDP3",
    schema="ohlcv-1m",
    symbols="NQ.v.0",
    stype_in="continuous",
    start=start.isoformat(),
    end=end.isoformat(),
)

df = data.to_df()
print(f"\nRows returned: {len(df)}")
if len(df) > 0:
    print("\nColumns:", list(df.columns))
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())
    print("\nLast 3 rows:")
    print(df.tail(3).to_string())
else:
    print("No data — market may be closed. Try a weekday during US market hours.")