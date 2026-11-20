"""Four material providers, with provenance and session-local structure artifacts."""

import hashlib
import json
from urllib.parse import urlencode, quote
from . import network
from .contracts import CapabilityError
from .store import Store


def query(source, formula, limit):
    if source == "mp":
        import os

        key = os.environ.get("MP_API_KEY")
        if not key:
            raise CapabilityError("MISSING_CREDENTIAL", "Configure MP_API_KEY")
        url = "https://api.materialsproject.org/materials/summary/?" + urlencode(
            {
                "formula": formula,
                "_limit": limit,
                "_fields": "material_id,formula_pretty,band_gap,density,structure,energy_above_hull",
            }
        )
        return network.request(url, headers={"X-API-KEY": key}).get("data", [])
    if source == "oqmd":
        return network.request(
            "https://oqmd.org/oqmdapi/formationenergy?"
            + urlencode({"composition": formula, "limit": limit})
        ).get("data", [])
    if source == "cod":
        from pymatgen.core import Composition

        composition = Composition(formula).get_el_amt_dict()
        formatted = " ".join(
            element + (str(int(amount)) if int(amount) != 1 else "")
            for element, amount in sorted(composition.items())
        )
        return network.request(
            "https://www.crystallography.net/cod/result?"
            + urlencode({"formula": formatted, "format": "json", "maxv": limit})
        )
    terms = (
        "compound("
        + formula
        + "),geometry,positions_fractional,species,composition,auid,paging(1,"
        + str(limit)
        + ")"
    )
    return network.request("https://aflow.org/API/aflux/?" + quote(terms, safe="(),"))


def structure_cif(source, record):
    from pymatgen.core import Structure, Lattice
    from pymatgen.io.cif import CifWriter

    if record.get("structure"):
        return str(CifWriter(Structure.from_dict(record["structure"])))
    if source == "oqmd" and record.get("unit_cell") and record.get("sites"):
        species = []
        coordinates = []
        for site in record["sites"]:
            element, values = site.split("@", 1)
            species.append(element.strip())
            coordinates.append([float(x) for x in values.split()])
        return str(
            CifWriter(Structure(Lattice(record["unit_cell"]), species, coordinates))
        )
    if (
        source == "aflow"
        and record.get("geometry")
        and record.get("positions_fractional")
    ):
        geometry = record["geometry"]
        positions = record["positions_fractional"]
        species = record.get("species", [])
        counts = record.get("composition", [])
        if isinstance(species, str):
            species = species.split(",")
        expanded = [
            element
            for element, count in zip(species, counts)
            for _ in range(int(count))
        ]
        if len(expanded) != len(positions):
            raise CapabilityError(
                "SOURCE_UNAVAILABLE", "AFLOW species/site count mismatch"
            )
        return str(
            CifWriter(
                Structure(Lattice.from_parameters(*geometry[:6]), expanded, positions)
            )
        )
    if source == "cod" and record.get("file"):
        return network.request(
            "https://www.crystallography.net/cod/" + str(record["file"]) + ".cif",
            raw=True,
        ).decode("utf-8")
    return None


def dispatch(operation, payload, context):
    store = Store(context)
    formula = payload["formula"]
    limit = payload.get("num_return", 10)
    sources = (
        [operation.removeprefix("materials.query_")]
        if ".query_" in operation
        else payload.get("sources", ["mp", "oqmd", "cod", "aflow"])
    )
    rows = []
    failures = []
    warnings = []
    artifacts = []
    successful_sources = 0
    for source in sources:
        cache_key = (
            "database:"
            + hashlib.sha256(json.dumps([source, formula, limit]).encode()).hexdigest()
        )
        try:
            import time

            cached = store.get(cache_key)
            raw = (
                cached["records"]
                if cached and cached["expires"] > time.time()
                else query(source, formula, limit)
            )
            if not cached or cached["expires"] <= time.time():
                store.set(cache_key, {"expires": time.time() + 86400, "records": raw})
            if isinstance(raw, dict):
                raw = list(raw.values())
            successful_sources += 1
            for record in raw[:limit]:
                item = dict(record, source=source)
                try:
                    if any(
                        record.get(k)
                        for k in ("structure", "unit_cell", "geometry", "file")
                    ):
                        text = structure_cif(source, record)
                        if text:
                            artifact = store.artifact("structure.cif", text, "cif")
                            artifacts.append(artifact)
                            item["cif_artifact_id"] = artifact["artifact_id"]
                except (CapabilityError, ImportError, ValueError, KeyError) as exc:
                    warnings.append(
                        {
                            "source": source,
                            "message": "Structure unavailable: " + str(exc),
                        }
                    )
                rows.append(item)
        except CapabilityError as exc:
            failures.append({"source": source, "code": exc.code, "message": str(exc)})
        except ImportError as exc:
            failures.append(
                {
                    "source": source,
                    "code": "DEPENDENCY_UNAVAILABLE",
                    "message": str(exc),
                }
            )
    if not successful_sources:
        raise CapabilityError("SOURCE_UNAVAILABLE", json.dumps(failures))
    return {
        "data": {"formula": formula, "records": rows, "failures": failures},
        "artifacts": artifacts,
        "warnings": failures + warnings,
        "status": "partial" if failures or warnings else "completed",
    }
