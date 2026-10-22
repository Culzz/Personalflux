"""Import the offline test evaluation into the database so the ML console can show it.
Run from the backend folder:

    python ..\\scripts\\import_evaluation.py
Safe to run more than once.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.services.evaluation_import import import_evaluation_csv  # noqa: E402

CSV_PATH = ROOT / "ml" / "reports" / "test_eval.csv"
if not CSV_PATH.exists():
    sys.exit(f"{CSV_PATH} not found. Run ml/src/run_test_eval.py first.")

with SessionLocal() as db:
    print(import_evaluation_csv(
        db, CSV_PATH, name="final_test_eval_v0.1",
        configuration={"source": "ml/reports/test_eval.csv",
                       "protocol": "pre-registered, run once on the test window",
                       "note": "Offline evaluation. Not live customer evidence."}))
