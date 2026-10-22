"""Holds the model currently used for serving, and finds versions on disk.

Each worker keeps its own copy in memory, but the *choice* of version lives in
the database. A background poller compares the two and hot-swaps when they
differ, so a promotion reaches every worker without a restart.
"""
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.ml.inference import LoadedModel, load_artifact, read_metadata, verify_checksums

BACKEND_ROOT = Path(__file__).resolve().parents[2]
_VERSION = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class ModelRegistry:
    def __init__(self):
        self.model: LoadedModel | None = None
        self.error: str | None = None
        self.root_override: Path | None = None   # used by tests
        self.loaded_version: str | None = None   # what this worker is serving
        self.desired_version: str | None = None  # what the database says should serve
        self.last_check_at: datetime | None = None
        self.poll_error: str | None = None
        self._lock = threading.Lock()

    @property
    def artifact_root(self) -> Path:
        if self.root_override is not None:
            return Path(self.root_override)
        return (BACKEND_ROOT / settings.model_artifact_dir).resolve()

    def folder_for(self, version: str) -> Path:
        """Only plain version names are accepted, never arbitrary paths."""
        if not _VERSION.match(version) or version in (".", ".."):
            raise ValueError("invalid version name")
        folder = (self.artifact_root / version).resolve()
        if folder.parent != self.artifact_root.resolve():
            raise ValueError("invalid version name")
        return folder

    def verify_version(self, version: str) -> dict:
        folder = self.folder_for(version)
        meta = read_metadata(folder)
        verify_checksums(folder, meta)
        return meta

    def load_version(self, version: str) -> LoadedModel:
        return load_artifact(self.folder_for(version), verify=True)

    def set_model(self, model: LoadedModel | None, error: str | None = None) -> None:
        with self._lock:
            self.model = model
            self.error = error
            self.loaded_version = model.version if model is not None else None

    def mark_checked(self, error: str | None = None) -> None:
        """Record the outcome of one poll, successful or not."""
        with self._lock:
            self.last_check_at = datetime.now(timezone.utc)
            self.poll_error = error[:300] if error else None

    @property
    def serving_version(self) -> str | None:
        return self.loaded_version

    def is_behind(self) -> bool:
        """True when the database points at a version this worker is not serving."""
        return self.desired_version is not None and self.desired_version != self.loaded_version

    def list_on_disk(self) -> list[str]:
        root = self.artifact_root
        if not root.exists():
            return []
        return sorted(p.name for p in root.iterdir()
                      if p.is_dir() and (p / "metadata.json").exists())


registry = ModelRegistry()
