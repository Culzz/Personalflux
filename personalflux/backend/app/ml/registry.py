"""Holds the model currently used for serving, and finds versions on disk."""
import re
import threading
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

    def list_on_disk(self) -> list[str]:
        root = self.artifact_root
        if not root.exists():
            return []
        return sorted(p.name for p in root.iterdir()
                      if p.is_dir() and (p / "metadata.json").exists())


registry = ModelRegistry()
