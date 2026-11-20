"""Install portable resources; never installs dependencies or frameworks implicitly."""

import importlib.resources
import json
from pathlib import Path
import shutil
from .runtime.registry import BUNDLES, SKILLS
from .runtime.contracts import CapabilityError


def assets():
    return importlib.resources.files("researchmind_skills").joinpath("skill_assets")


def selected(bundle=None, skill=None):
    if bool(bundle) == bool(skill):
        raise CapabilityError("INVALID_ARGUMENT", "Specify exactly one bundle or skill")
    if bundle and bundle not in BUNDLES:
        raise CapabilityError("INVALID_ARGUMENT", "Unknown bundle")
    if skill and skill not in SKILLS:
        raise CapabilityError("INVALID_ARGUMENT", "Unknown skill")
    return BUNDLES[bundle] if bundle else [skill]


def install(target, bundle=None, skill=None):
    names = selected(bundle, skill)
    root = Path(target).resolve()
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / ".researchmind-install.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    # Validate the entire selected set before copying its first member.
    for name in names:
        src = assets().joinpath(name)
        manifest = json.loads(src.joinpath("skill.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != "1.0":
            raise CapabilityError("SCHEMA_VERSION_UNSUPPORTED", name)
        if manifest.get("runtime_version") != "0.1.0":
            raise CapabilityError("RUNTIME_VERSION_MISMATCH", name)
        for relative in (
            "SKILL.md",
            "scripts/run.py",
            "references/parameters.md",
            "references/outputs.md",
        ):
            if not src.joinpath(relative).is_file():
                raise CapabilityError(
                    "ARTIFACT_NOT_FOUND",
                    "Incomplete skill resource: " + name + "/" + relative,
                )
        dest = root / name
        if dest.is_symlink() or dest.resolve().parent != root:
            raise CapabilityError(
                "ACCESS_DENIED", "Skill destination is outside the target root"
            )
        if dest.exists():
            existing = dest / "skill.json"
            if (
                not existing.is_file()
                or json.loads(existing.read_text(encoding="utf-8")).get("name") != name
            ):
                raise CapabilityError(
                    "INVALID_ARGUMENT", "Conflicting skill destination: " + name
                )
            if any(path.is_symlink() for path in dest.rglob("*")):
                raise CapabilityError(
                    "ACCESS_DENIED", "Skill destination contains symlinks"
                )
    for name in names:
        src = assets().joinpath(name)
        manifest = json.loads(src.joinpath("skill.json").read_text(encoding="utf-8"))
        if manifest["schema_version"] != "1.0":
            raise CapabilityError("SCHEMA_VERSION_UNSUPPORTED", name)
        dest = root / name
        if dest.exists():
            existing = dest / "skill.json"
            if (
                not existing.exists()
                or json.loads(existing.read_text(encoding="utf-8")).get("name") != name
            ):
                raise CapabilityError(
                    "INVALID_ARGUMENT",
                    "Refusing to overwrite unrelated skill directory",
                )
        with importlib.resources.as_file(src) as path:
            shutil.copytree(path, dest, dirs_exist_ok=True)
        entry = state.setdefault(
            name, {"bundles": [], "explicit": False, "version": "0.1.0"}
        )
        if bundle and bundle not in entry["bundles"]:
            entry["bundles"].append(bundle)
        if skill:
            entry["explicit"] = True
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"installed": names, "target": str(root)}


def uninstall(target, bundle=None, skill=None):
    names = selected(bundle, skill)
    root = Path(target).resolve()
    path = root / ".researchmind-install.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    removed = []
    for name in names:
        if name not in state:
            continue
        if bundle:
            state[name]["bundles"] = [x for x in state[name]["bundles"] if x != bundle]
        else:
            state[name]["explicit"] = False
        if not state[name]["bundles"] and not state[name]["explicit"]:
            dest = (root / name).resolve()
            if dest.parent != root:
                raise CapabilityError("ACCESS_DENIED", "Invalid install path")
            if dest.exists():
                shutil.rmtree(dest)
            state.pop(name)
            removed.append(name)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return {"removed": removed, "retained": list(state)}
