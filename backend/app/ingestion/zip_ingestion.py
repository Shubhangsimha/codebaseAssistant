import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract a ZIP archive to dest_dir with zip-slip protection.

    If the archive contains a single top-level directory, that directory is
    returned as the effective root (common for GitHub-downloaded ZIPs).
    Otherwise dest_dir is returned.

    Raises ValueError on zip-slip attempts or corrupt archives.
    """
    dest_dir = dest_dir.resolve()

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.namelist()

            # Zip-slip check: resolve every target path before extraction
            for member in members:
                target = (dest_dir / member).resolve()
                if not str(target).startswith(str(dest_dir)):
                    raise ValueError(
                        f"Zip-slip attack detected in archive member: {member!r}"
                    )

            zf.extractall(dest_dir)
            logger.info("Extracted %d entries to %s", len(members), dest_dir)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid or corrupt ZIP file: {exc}") from exc

    # If there is exactly one top-level directory, descend into it.
    entries = [e for e in dest_dir.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        logger.info("Single top-level directory detected; using %s as root", entries[0])
        return entries[0]

    return dest_dir
