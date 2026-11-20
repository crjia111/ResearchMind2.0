"""Build standalone, framework-neutral Skill resource archives from the installed package."""

import argparse
from importlib.resources import as_file
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from researchmind_skills.installer import assets
from researchmind_skills.runtime.registry import SKILLS, BUNDLES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist/skills")
    args = parser.parse_args()
    target = Path(args.out).resolve()
    target.mkdir(parents=True, exist_ok=True)
    archives = []
    for name in SKILLS:
        archive = target / (name + "-0.1.0.zip")
        with as_file(assets().joinpath(name)) as root:
            with ZipFile(archive, "w", ZIP_DEFLATED) as stream:
                for path in sorted(root.rglob("*")):
                    if (
                        path.is_file()
                        and "__pycache__" not in path.parts
                        and path.suffix != ".pyc"
                    ):
                        stream.write(path, str(Path(name) / path.relative_to(root)))
        archives.append(archive.name)
    (target / "bundles.json").write_text(
        json.dumps(BUNDLES, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"archives": archives, "bundles": BUNDLES, "target": str(target)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
