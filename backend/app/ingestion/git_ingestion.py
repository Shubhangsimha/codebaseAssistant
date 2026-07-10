import logging
from pathlib import Path

import git

logger = logging.getLogger(__name__)

_GITHUB_PREFIXES = ("https://github.com/",)


def clone_repository(repo_url: str, dest_dir: Path) -> Path:
    """Shallow-clone a public GitHub repository into dest_dir.

    Returns the path to the cloned directory.
    Raises ValueError for invalid URLs or clone failures.
    """
    if not any(repo_url.startswith(p) for p in _GITHUB_PREFIXES):
        raise ValueError(
            "Only public GitHub HTTPS URLs are supported "
            "(must start with https://github.com/)."
        )

    # Normalise: strip trailing .git if present
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    logger.info("Cloning %s → %s (depth=1)", url, dest_dir)
    try:
        git.Repo.clone_from(
            url,
            str(dest_dir),
            depth=1,
            single_branch=True,
            no_checkout=False,
        )
    except git.exc.GitCommandError as exc:
        raise ValueError(
            f"Could not clone repository — check the URL is a public GitHub repo. "
            f"Detail: {exc}"
        ) from exc

    logger.info("Clone complete: %s", dest_dir)
    return dest_dir
