"""Load offline evaluation results (ml/reports/test_eval.csv) into experiments + evaluation_runs."""
import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EvaluationRun, Experiment

_INT = {"k", "sessions"}
_FLOAT = {"recall", "ndcg", "mrr", "coverage"}


def _convert(key: str, value: str):
    if key in _INT:
        return int(float(value))
    if key in _FLOAT:
        return float(value)
    return value


def import_evaluation_csv(db: Session, path: Path, name: str, model_version: str | None = None,
                          configuration: dict | None = None) -> dict:
    """Idempotent: an experiment with the same name is never imported twice."""
    if db.scalar(select(Experiment.id).where(Experiment.name == name)):
        return {"experiment": name, "runs_added": 0, "skipped": True}
    exp = Experiment(name=name, configuration=configuration or {"source": Path(path).name})
    db.add(exp)
    db.flush()
    added = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            metrics = {k: _convert(k, v) for k, v in row.items() if v not in (None, "")}
            db.add(EvaluationRun(experiment_id=exp.id, model_version=model_version, metrics=metrics))
            added += 1
    db.commit()
    return {"experiment": name, "runs_added": added, "skipped": False}
