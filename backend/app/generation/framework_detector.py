from __future__ import annotations

import json
from pathlib import Path


def detect_frameworks(repo_path: str) -> dict:
    """
    Scan well-known config files and return a dict of detected frameworks/stack info.
    Used as context for the architecture summary LLM prompt.
    """
    root = Path(repo_path)
    info: dict[str, object] = {}

    # Python
    reqs = root / "requirements.txt"
    if reqs.exists():
        text = reqs.read_text(errors="ignore").lower()
        pkgs = [line.split("==")[0].split(">=")[0].strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
        info["python_packages"] = pkgs[:40]

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        info["pyproject_toml"] = pyproject.read_text(errors="ignore")[:1000]

    # Node / JS
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text(errors="ignore"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            info["npm_packages"] = list(deps.keys())[:40]
            if "scripts" in pkg:
                info["npm_scripts"] = pkg["scripts"]
        except Exception:
            pass

    # Go
    go_mod = root / "go.mod"
    if go_mod.exists():
        info["go_mod"] = go_mod.read_text(errors="ignore")[:800]

    # Java / Maven / Gradle
    pom = root / "pom.xml"
    if pom.exists():
        info["pom_xml_snippet"] = pom.read_text(errors="ignore")[:800]

    build_gradle = root / "build.gradle"
    if build_gradle.exists():
        info["build_gradle_snippet"] = build_gradle.read_text(errors="ignore")[:800]

    # Dockerfile
    dockerfile = root / "Dockerfile"
    if dockerfile.exists():
        info["dockerfile"] = dockerfile.read_text(errors="ignore")[:600]

    # README snippet
    for name in ("README.md", "README.rst", "README.txt", "README"):
        readme = root / name
        if readme.exists():
            info["readme_snippet"] = readme.read_text(errors="ignore")[:1200]
            break

    return info
