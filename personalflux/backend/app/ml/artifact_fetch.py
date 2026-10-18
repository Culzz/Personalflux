"""Fetch the model artefact tarball at boot when MODEL_ARTIFACT_URL is configured.

Hosts build from git, and trained artefacts are build outputs rather than source,
so a deployment needs a way to obtain them. Setting MODEL_ARTIFACT_URL to a
tarball (a release asset, a pre-signed object-store URL) makes startup
self-sufficient. Extraction is restricted to regular files and directories that
stay inside the artefact root, and the existing checksum verification in
`app.ml.inference` still runs afterwards, so a corrupted download cannot serve.
"""
import logging
import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from app.core.config import settings
from app.ml.registry import registry

logger = logging.getLogger("personaflux")


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    dest = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if target != dest and not str(target).startswith(str(dest) + os.sep):
            raise ValueError(f"archive entry escapes the artefact directory: {member.name}")
        if not (member.isfile() or member.isdir()):
            raise ValueError(f"unsupported archive entry: {member.name}")
    tar.extractall(dest)   # noqa: S202 - every member was validated just above


def ensure_artifacts() -> bool:
    """Download and unpack the artefact tarball if it is configured and missing.

    Never raises: a failed download leaves the API in documented fallback mode.
    """
    url = settings.model_artifact_url
    if not url:
        return False
    root = registry.artifact_root
    if registry.list_on_disk():
        return True                     # already provisioned (e.g. a mounted disk)
    tmp_path: str | None = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = tmp.name
            with urllib.request.urlopen(url, timeout=120) as response:   # noqa: S310
                shutil.copyfileobj(response, tmp)
        with tarfile.open(tmp_path, "r:gz") as tar:
            _safe_extract(tar, root)
        logger.info("model artefacts fetched from the configured URL")
        return True
    except Exception as e:
        logger.error("could not fetch model artefacts: %s", str(e)[:200])
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
