import os
from datetime import datetime, timedelta, timezone

import databento as db
from dotenv import load_dotenv
from pynescript.ast.helper import parse, unparse

load_dotenv()

# --- 1. Fetch real Databento candles ---
client = db.Historical(os.getenv("DATABENTO_API_KEY"))
end = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
start = end - timedelta(hours=6)

data = client.timeseries.get_range(
    dataset="GLBX.MDP3",
    schema="ohlcv-1m",
    symbols="NQ.v.0",
    stype_in="continuous",
    start=start.isoformat(),
    end=end.isoformat(),
)
df = data.to_df()
print(f"Fetched {len(df)} candles")

# Convert to the list-of-dicts shape hoox-pyne expects
bars = []
for ts, row in df.iterrows():
    bars.append({
        "time": int(ts.timestamp()),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": float(row["volume"]),
    })

# --- 2. A representative Pine Script ---
# Replace this with the client's actual indicator when available.
# For the spike, use a multi-feature script that exercises common Pine patterns.
PINE_SOURCE = '''
//@version=6
indicator("Spike Test", overlay=true)

fast = ta.ema(close, 9)
slow = ta.ema(close, 21)
rsi14 = ta.rsi(close, 14)

plot(fast, "EMA Fast", color=color.blue)
plot(slow, "EMA Slow", color=color.red)
plot(rsi14, "RSI", color=color.orange)
'''

# --- 3. Parse and check syntax ---
print("\n--- Parsing Pine source ---")
tree = parse(PINE_SOURCE)
print("Parse OK")
print("Normalized source:")
print(unparse(tree)[:500])

# --- 4. Run the script (hoox-pyne API) ---
# The exact API may vary by version. Check the installed package docs.
# If pynescript has a direct run() helper, use it; otherwise fall back
# to the Pro API HTTP endpoint (POST /run).
print("\n--- Checking available runtime entrypoints ---")
try:
    import pynescript
    print("pynescript module:", pynescript.__file__)
    print("Available names:", [n for n in dir(pynescript) if not n.startswith("_")][:20])
except Exception as e:
    print("pynescript import issue:", e)

print("\nSpike complete. Next: check the hoox-pyne docs for the exact")
print("run() call signature for version installed, then feed `bars` in.")