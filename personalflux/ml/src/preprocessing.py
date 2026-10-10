"""Load, clean and split the Retailrocket events."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

VALID_EVENTS = {"view", "addtocart", "transaction"}

# Starting hypotheses from the SRS, not learned truths.
# Retailrocket has no clicks/saves/dismissals, so only these three exist.
EVENT_WEIGHTS = {"view": 1, "addtocart": 4, "transaction": 5}


def load_events(path: Path | None = None) -> pd.DataFrame:
    """Read the raw events CSV into a DataFrame."""
    return pd.read_csv(path or RAW / "events.csv")


def clean_events(df: pd.DataFrame) -> pd.DataFrame:
    """Validate, rename, de-duplicate, weight and time-sort the events."""
    df = df.copy()

    # 1. keep only known event types, drop rows missing key fields
    df = df[df["event"].isin(VALID_EVENTS)]
    df = df.dropna(subset=["timestamp", "visitorid", "itemid"])

    # 2. clearer column names
    df = df.rename(columns={"visitorid": "user_id", "itemid": "item_id"})

    # 3. real datetime (timestamp is in milliseconds)
    df["time"] = pd.to_datetime(df["timestamp"], unit="ms")

    # 4. remove exact duplicate events
    df = df.drop_duplicates(subset=["timestamp", "user_id", "event", "item_id"])

    # 5. attach the weight for each event type
    df["weight"] = df["event"].map(EVENT_WEIGHTS)

    # 6. oldest first
    return df.sort_values("time").reset_index(drop=True)


def chronological_split(
    df: pd.DataFrame, val_days: int = 14, test_days: int = 14
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by time: train (oldest) | validation | test (newest)."""
    end = df["time"].max()
    test_start = end - pd.Timedelta(days=test_days)
    val_start = test_start - pd.Timedelta(days=val_days)

    train = df[df["time"] < val_start]
    val = df[(df["time"] >= val_start) & (df["time"] < test_start)]
    test = df[df["time"] >= test_start]
    return train, val, test