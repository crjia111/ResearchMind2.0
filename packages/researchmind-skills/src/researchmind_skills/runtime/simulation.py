"""Real scientific execution. Missing models never produce mock success."""

import io
import math
import os
from pathlib import Path
import tempfile
from .contracts import CapabilityError
from .store import Store


def cif_text(payload, store):
    if bool(payload.get("artifact_id")) == bool(payload.get("cif_content")):
        raise CapabilityError(
            "INVALID_ARGUMENT", "Supply exactly one CIF artifact_id or cif_content"
        )
    return (
        store.resolve(payload["artifact_id"]).read_text(encoding="utf-8")
        if payload.get("artifact_id")
        else payload["cif_content"]
    )


def validate_cif(text):
    from ase.io import read

    try:
        atoms = read(io.StringIO(text), format="cif")
        if (
            len(atoms) == 0
            or not math.isfinite(atoms.get_volume())
            or atoms.get_volume() <= 0
        ):
            raise ValueError("Empty structure or invalid unit cell")
        if not all(
            math.isfinite(float(v)) for row in atoms.get_positions() for v in row
        ):
            raise ValueError("Invalid coordinates")
        return {
            "is_valid": True,
            "formula": atoms.get_chemical_formula(),
            "num_atoms": len(atoms),
            "cell_volume": atoms.get_volume(),
        }
    except Exception as exc:
        raise CapabilityError(
            "INVALID_ARGUMENT", "CIF could not be parsed as a valid periodic structure"
        ) from exc


def require_path(variable, directory=False):
    value = os.environ.get(variable)
    path = Path(value).expanduser().resolve() if value else None
    if not path or not (path.is_dir() if directory else path.is_file()):
        raise CapabilityError(
            "MODEL_NOT_FOUND",
            "Configure "
            + variable
            + " to an existing "
            + ("directory" if directory else "file"),
        )
    return path


def dispatch(operation, payload, context):
    store = Store(context)
    if payload.get("artifact_ids"):
        if payload.get("artifact_id") or payload.get("cif_content"):
            raise CapabilityError(
                "INVALID_ARGUMENT",
                "Batch input cannot mix artifact_ids with a single structure",
            )
        rows = []
        artifacts = []
        failed = 0
        for ident in payload["artifact_ids"]:
            item = {k: v for k, v in payload.items() if k != "artifact_ids"}
            item["artifact_id"] = ident
            try:
                output = dispatch(operation, item, context)
                rows.append(
                    {
                        "artifact_id": ident,
                        "status": output.get("status", "completed"),
                        "data": output["data"],
                    }
                )
                artifacts.extend(output.get("artifacts", []))
            except (CapabilityError, ImportError) as exc:
                failed += 1
                rows.append(
                    {
                        "artifact_id": ident,
                        "status": "failed",
                        "error": {
                            "code": getattr(exc, "code", "DEPENDENCY_UNAVAILABLE"),
                            "message": str(exc),
                        },
                    }
                )
        successful = len(rows) - failed
        if not successful:
            return {
                "status": "failed",
                "data": {"results": rows, "completed": 0, "failed": failed},
                "error": {
                    "code": "COMPUTE_FAILED",
                    "message": "All structures failed",
                    "retryable": False,
                },
                "usage": {"successful_units": 0, "real_compute_units": 0},
            }
        return {
            "status": "partial" if failed else "completed",
            "data": {"results": rows, "completed": successful, "failed": failed},
            "artifacts": artifacts,
            "usage": {
                "successful_units": successful,
                "real_compute_units": 0
                if operation == "simulation.validate_cif"
                else successful,
            },
        }

    if operation == "simulation.cache.clear":
        # Only ephemeral workspace files; user models and artifacts are never deleted.
        root = store.root / "compute-cache" / context.session_id
        files = list(root.glob("*")) if root.exists() else []
        if not payload.get("dry_run", True):
            import shutil

            for file in files:
                resolved = file.resolve()
                if not resolved.is_relative_to(root.resolve()):
                    raise CapabilityError(
                        "ACCESS_DENIED", "Cache path escapes current session"
                    )
                if file.is_symlink():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file)
                elif file.is_file():
                    file.unlink()
        return {
            "data": {
                "dry_run": payload.get("dry_run", True),
                "files": [f.name for f in files],
            }
        }
    if operation == "simulation.generate":
        return generate(payload, context, store)
    text = cif_text(payload, store)
    info = validate_cif(text)
    if operation == "simulation.validate_cif":
        return {"data": info}
    if operation == "simulation.kappa":
        return kappa(payload, text, store)
    require_path("MATTERSIM_MODEL_PATH")
    from ..vendor import mattersim_energy as engine

    kwargs = dict(
        cif_content=text, cif_filename="input.cif", device=payload.get("device", "cpu")
    )
    if operation == "simulation.energy":
        data = engine.calculate_energy_from_cif_impl(**kwargs)
    elif operation == "simulation.relax":
        data = engine.relax_structure_impl(
            **kwargs,
            max_steps=payload.get("max_steps", 500),
            fmax=payload.get("fmax", 0.01),
        )
    else:
        if payload.get("relax_first", False):
            relaxed = engine.relax_structure_impl(**kwargs)
            ensure_success(relaxed)
            text = relaxed.get("relaxed_cif_content") or relaxed.get("cif_content")
            if not text:
                raise CapabilityError(
                    "INTERNAL_ERROR", "Relaxation returned no structure"
                )
            kwargs["cif_content"] = text
        output = (
            store.root
            / "compute-cache"
            / context.session_id
            / __import__("uuid").uuid4().hex
        )
        output.mkdir(parents=True, exist_ok=True)
        data = engine.calculate_phonon_impl(
            **kwargs,
            supercell_matrix=payload.get("supercell_matrix", [2, 2, 2]),
            amplitude=payload.get("amplitude", 0.01),
            output_dir=str(output),
        )
    ensure_success(data)
    artifacts = []

    # Preserve nested plot/data paths without exposing server paths.
    def collect(value, key=""):
        if isinstance(value, dict):
            return {
                k: collect(v, k)
                for k, v in value.items()
                if k not in ("relaxed_cif_base64", "_remove_cif_content_before_return")
            }
        if isinstance(value, list):
            return [collect(v, key) for v in value]
        if (
            isinstance(value, str)
            and "cif" in key
            and ("data_" in value or "_cell_" in value)
        ):
            artifact = store.artifact("relaxed.cif", value, "cif")
            artifacts.append(artifact)
            return artifact["artifact_id"]
        if isinstance(value, str) and len(value) < 4096:
            try:
                path = Path(value)
                if (
                    path.is_absolute()
                    and path.is_file()
                    and path.resolve().is_relative_to(store.root.resolve())
                ):
                    artifact = store.artifact(
                        path.name, path.read_bytes(), path.suffix.lstrip(".")
                    )
                    artifacts.append(artifact)
                    return artifact["artifact_id"]
            except OSError:
                pass
        return value

    data = collect(data)
    if operation == "simulation.energy":
        for key in (
            "formation_energy_per_atom",
            "decomposition_energy",
            "stability",
            "stability_assessment",
            "is_stable",
        ):
            if key in data:
                data[key] = None
        data["stability_status"] = "not_validated"
        data["stability_note"] = (
            "Energy and forces are model predictions; convex-hull/stability outputs are not accepted without a validated reference calculation."
        )
    data["calculation_mode"] = "real"
    return {"data": data, "artifacts": artifacts}


def ensure_success(data):
    if data.get("success") is False or data.get("error"):
        raise CapabilityError(
            "COMPUTE_FAILED", str(data.get("error", "Scientific calculation failed"))
        )
    if str(data.get("calculation_mode", "real")).startswith("mock"):
        raise CapabilityError("COMPUTE_FAILED", "Mock results are not accepted")


def generate(payload, context, store):
    model = require_path("CRYSTALLM_MODEL_DIR", True)
    from ..vendor.crystal_pipeline import CrystalStructureGenerator
    from importlib.resources import files
    import re

    if not re.fullmatch(r"[A-Za-z0-9().+-]+", payload["composition"]):
        raise CapabilityError("INVALID_ARGUMENT", "Invalid chemical composition")
    root = (
        store.root
        / "compute-cache"
        / context.session_id
        / __import__("uuid").uuid4().hex
    )
    dirs = {name: root / name for name in ("prompts", "generated", "processed")}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    params = dict(
        bin_dir=str(files("researchmind_skills.vendor").joinpath("crystal_bin")),
        prompt_dir=str(dirs["prompts"]),
        generate_dir=str(dirs["generated"]),
        postprocess_input_dir=str(dirs["generated"]),
        postprocess_output_dir=str(dirs["processed"]),
        out_dir=str(model),
        num_samples=payload.get("num_samples", 1),
        top_k=payload.get("top_k", 10),
        max_new_tokens=payload.get("max_new_tokens", 2000),
        device=payload.get("device", "cpu"),
    )
    data = CrystalStructureGenerator(
        payload["composition"], params=params, spacegroup=payload.get("spacegroup")
    ).run_pipeline(export_json=False)
    if not data.get("success"):
        raise CapabilityError(
            "COMPUTE_FAILED", str(data.get("message", "Crystal generation failed"))
        )
    artifacts = []
    warnings = []
    for path in dirs["processed"].rglob("*.cif"):
        try:
            validate_cif(path.read_text(encoding="utf-8"))
        except CapabilityError:
            warnings.append("Rejected invalid generated CIF " + path.name)
            continue
        artifacts.append(store.artifact(path.name, path.read_bytes(), "cif"))
    if not artifacts:
        raise CapabilityError("COMPUTE_FAILED", "No valid generated crystal")
    return {
        "data": {
            "composition": payload["composition"],
            "structures": artifacts,
            "calculation_mode": "real",
        },
        "artifacts": artifacts,
        "warnings": warnings,
    }


def kappa(payload, text, store):
    models = require_path("KAPPA_MODEL_DIR", True)
    atom_init = require_path("KAPPA_ATOM_INIT")
    temperature = payload.get("temperature", 300)
    # The original models and formulas were calibrated at 300K.
    if temperature != 300:
        raise CapabilityError(
            "INVALID_ARGUMENT",
            "The supplied Kappa models support 300 K only; no unvalidated temperature extrapolation is performed",
        )
    from ..vendor.kappa.calculator import (
        ThermalConductivityCalculator,
        is_kappa_available,
    )

    if not is_kappa_available():
        raise CapabilityError(
            "DEPENDENCY_UNAVAILABLE",
            "Kappa scientific libraries are not fully installed",
        )
    import shutil

    with tempfile.TemporaryDirectory(prefix="rm-kappa-") as directory:
        root = Path(directory)
        inputs = root / "input"
        inputs.mkdir()
        (inputs / "material.cif").write_text(text, encoding="utf-8")
        work = root / "work"
        work.mkdir()
        shutil.copy2(atom_init, work / "atom_init.json")
        # This function is only invoked in the isolated scientific task process.
        old = Path.cwd()
        try:
            os.chdir(work)
            calculator = ThermalConductivityCalculator(str(inputs), str(models))
            calculator.lib_path = str(work)
            calculator.model_path = str(models)
            method = payload.get("method", "kappa_p")
            frame = (
                calculator.calculate_kappa_p()
                if method == "kappa_p"
                else calculator.calculate_kappa_mtp()
            )
        finally:
            os.chdir(old)
        if frame.empty:
            raise CapabilityError("COMPUTE_FAILED", "Kappa returned no rows")
        column = (
            "Kappa_Slack (W m-1 K-1)"
            if method == "kappa_p"
            else "Kappa_cal (W m-1 K-1)"
        )
        values = [float(x) for x in frame[column]]
        if not all(math.isfinite(x) and x >= 0 for x in values):
            raise CapabilityError(
                "COMPUTE_FAILED", "Non-finite or negative thermal conductivity"
            )
        artifact = store.artifact(
            "thermal_conductivity.csv", frame.to_csv(index=True), "csv"
        )
        return {
            "data": {
                "method": method,
                "temperature": 300,
                "thermal_conductivity": {"values": values, "unit": "W/(m·K)"},
                "calculation_mode": "real",
            },
            "artifacts": [artifact],
        }
