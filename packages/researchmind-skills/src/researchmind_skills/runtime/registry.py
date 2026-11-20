"""Single source of capability schemas, skill bindings and legacy aliases."""

from copy import deepcopy
from .contracts import CapabilityError

S = lambda **kw: dict(type="string", **kw)
I = lambda **kw: dict(type="integer", **kw)
N = lambda **kw: dict(type="number", **kw)
B = lambda **kw: dict(type="boolean", **kw)
A = lambda items=None, **kw: dict(type="array", items=items or {}, **kw)
O = lambda **kw: dict(type="object", **kw)


def schema(properties, required=()):
    return dict(
        type="object",
        properties=properties,
        required=list(required),
        additionalProperties=False,
    )


BUNDLES = {
    "literature": [
        "literature-search",
        "paper-analysis",
        "research-report",
        "literature-knowledge",
    ],
    "materials-db": ["materials-search"],
    "simulation": [
        "crystal-generation",
        "structure-optimization",
        "phonon-analysis",
        "thermal-conductivity",
    ],
}
SKILLS = {name: bundle for bundle, names in BUNDLES.items() for name in names}
CAPABILITIES = {}


def add(name, skills, properties=None, required=(), long=False, dependency=None):
    CAPABILITIES[name] = dict(
        operation=name,
        skills=skills,
        input_schema=schema(properties or {}, required),
        output_schema={
            "type": "object",
            "required": [
                "schema_version",
                "operation",
                "request_id",
                "status",
                "data",
                "artifacts",
                "error",
                "usage",
            ],
        },
        schema_version="1.0",
        long_running=long,
        dependency=dependency,
    )


readers = ["paper-analysis", "research-report", "literature-knowledge"]
all_papers = BUNDLES["literature"]
add("papers.list", all_papers, {"fields": A(S()), "topic": S()})
add("papers.topics", ["literature-search"])
add("papers.filter", ["literature-search"], {"topic": S()}, ["topic"])
add(
    "papers.selection.update",
    ["literature-search"],
    {"paper_ids": A(S())},
    ["paper_ids"],
)
add("papers.selection.get", all_papers)
add("papers.selection.clear", ["literature-search"])
add("papers.plan", ["literature-search"], {"query": S(minLength=1)}, ["query"])
search = {
    "query": S(minLength=1),
    "max_results": I(minimum=1, maximum=100),
    "sources": A(S(enum=["arxiv", "tavily", "semantic_scholar"]), minItems=1),
    "year_from": I(minimum=1900, maximum=2200),
}
add("papers.search", ["literature-search"], search, ["query"])
add(
    "papers.search_by_author",
    ["literature-search"],
    {"author": S(minLength=1), "max_results": I(minimum=1, maximum=100)},
    ["author"],
)
add(
    "papers.import_uploads",
    ["literature-search"],
    {"artifact_ids": A(S(), minItems=1)},
    ["artifact_ids"],
)
add("papers.info", all_papers, {"paper_id": S(minLength=1)}, ["paper_id"])
for op in ["papers.web_search", "papers.news_search"]:
    add(
        op,
        ["literature-search"],
        {"query": S(minLength=1), "max_results": I(minimum=1, maximum=100)},
        ["query"],
    )
add("papers.download", readers, {"url": S(minLength=1), "name": S()}, ["url"])
add("papers.content.get", readers, {"paper_id": S(), "url": S()}, ())
add(
    "papers.content.batch_get",
    readers,
    {"paper_ids": A(S(), minItems=1)},
    ["paper_ids"],
)
add("papers.content.read", readers, {"artifact_id": S(minLength=1)}, ["artifact_id"])
add(
    "papers.content.read_segment",
    readers,
    {
        "artifact_id": S(minLength=1),
        "start": I(minimum=0),
        "length": I(minimum=1, maximum=100000),
    },
    ["artifact_id"],
)
add(
    "papers.content.find",
    readers,
    {
        "artifact_id": S(minLength=1),
        "search_term": S(minLength=1),
        "context_length": I(minimum=0, maximum=10000),
    },
    ["artifact_id", "search_term"],
)
add(
    "papers.analyze",
    ["paper-analysis"],
    {"paper_ids": A(S(), minItems=1), "instruction": S()},
    ["paper_ids"],
    True,
)
add("papers.export_csv", all_papers, {"records": A(O()), "fields": A(S()), "name": S()})
add(
    "papers.report",
    ["research-report"],
    {"topic": S(minLength=1), "paper_ids": A(S())},
    ["topic"],
    True,
)
add(
    "papers.index",
    ["literature-knowledge"],
    {
        "paper_ids": A(S(), minItems=1),
        "collection_name": S(),
        "source_type": S(enum=["arxiv"]),
    },
    ["paper_ids"],
    True,
    "chromadb",
)
add(
    "papers.semantic_search",
    ["literature-knowledge"],
    {
        "query": S(minLength=1),
        "collection_name": S(),
        "top_k": I(minimum=1, maximum=100),
    },
    ["query"],
    False,
    "chromadb",
)
add(
    "papers.clean_csv",
    [],
    {"artifact_id": S(minLength=1), "dry_run": B(), "backup": B()},
    ["artifact_id"],
)
for source in ["mp", "oqmd", "cod", "aflow"]:
    add(
        "materials.query_" + source,
        ["materials-search"],
        {"formula": S(minLength=1), "num_return": I(minimum=1, maximum=100)},
        ["formula"],
    )
for op in ["materials.search", "materials.recommend"]:
    add(
        op,
        ["materials-search"],
        {
            "formula": S(minLength=1),
            "num_return": I(minimum=1, maximum=100),
            "sources": A(S(enum=["mp", "oqmd", "cod", "aflow"]), minItems=1),
        },
        ["formula"],
    )
for group in ["materials", "simulation"]:
    add("diagnostics." + group, [])
add(
    "simulation.validate_cif",
    BUNDLES["simulation"],
    {"artifact_id": S(), "cif_content": S()},
    dependency="ase",
)
structure = {"artifact_id": S(), "cif_content": S(), "device": S(enum=["cpu", "cuda"])}
for op, skill in [
    ("energy", "structure-optimization"),
    ("relax", "structure-optimization"),
    ("phonon", "phonon-analysis"),
    ("kappa", "thermal-conductivity"),
]:
    props = deepcopy(structure)
    if op == "relax":
        props.update(max_steps=I(minimum=1, maximum=10000), fmax=N(minimum=0.000001))
    if op == "phonon":
        props.update(
            supercell_matrix=A(I(minimum=1, maximum=10), minItems=3, maxItems=3),
            amplitude=N(minimum=0.000001),
            relax_first=B(),
        )
    if op == "kappa":
        props.update(
            method=S(enum=["kappa_p", "kappa_mtp"]),
            temperature=N(minimum=1, maximum=5000),
        )
    add(
        "simulation." + op,
        [skill],
        props,
        long=True,
        dependency="mattersim" if op != "kappa" else "torch",
    )
CAPABILITIES["simulation.relax"]["skills"].append("phonon-analysis")
add(
    "simulation.generate",
    ["crystal-generation"],
    {
        "composition": S(minLength=1),
        "device": S(enum=["cpu", "cuda"]),
        "num_samples": I(minimum=1, maximum=100),
        "top_k": I(minimum=1, maximum=1000),
        "max_new_tokens": I(minimum=1, maximum=20000),
        "spacegroup": S(),
    },
    ["composition"],
    True,
    "torch",
)
add("simulation.cache.clear", [], {"dry_run": B()})

for operation, spec in CAPABILITIES.items():
    if operation.startswith("simulation.") and operation not in (
        "simulation.generate",
        "simulation.cache.clear",
    ):
        spec["input_schema"]["properties"]["artifact_ids"] = A(
            S(minLength=1), minItems=1, maxItems=100
        )

LEGACY_ALIASES = {
    "list_papers_from_csv": "papers.list",
    "get_paper_topics": "papers.topics",
    "filter_papers_by_topic": "papers.filter",
    "select_papers": "papers.selection.update",
    "get_selected_papers": "papers.selection.get",
    "clear_paper_selection": "papers.selection.clear",
    "generate_research_plan": "papers.plan",
    "search_papers": "papers.search",
    "ingest_uploaded_papers": "papers.import_uploads",
    "search_arxiv_papers": "papers.search",
    "search_papers_by_author": "papers.search_by_author",
    "get_paper_info": "papers.info",
    "tavily_search": "papers.web_search",
    "tavily_academic_search": "papers.search",
    "tavily_news_search": "papers.news_search",
    "download_paper": "papers.download",
    "get_paper_content": "papers.content.get",
    "fetch_papers_content": "papers.content.batch_get",
    "load_saved_paper_content": "papers.content.read",
    "load_paper_content_segment": "papers.content.read_segment",
    "search_in_saved_content": "papers.content.find",
    "batch_paper_analysis": "papers.analyze",
    "save_papers_to_csv": "papers.export_csv",
    "generate_research_report": "papers.report",
    "ingest_papers_to_vector_store": "papers.index",
    "semantic_search_papers": "papers.semantic_search",
    "clean_csv_data": "papers.clean_csv",
    "materials_project_query_tool": "materials.query_mp",
    "get_oqmd_phases": "materials.query_oqmd",
    "search_cod_by_formula": "materials.query_cod",
    "get_aflow_data": "materials.query_aflow",
    "batch_database_search": "materials.search",
    "get_structure_recommendations": "materials.recommend",
    "materials.health_check": "diagnostics.materials",
    "calculate_phonon": "simulation.phonon",
    "calculate_energy": "simulation.energy",
    "relax_structure": "simulation.relax",
    "simulation.health_check": "diagnostics.simulation",
    "extract_and_validate_cif": "simulation.validate_cif",
    "calculate_kappa": "simulation.kappa",
    "generate_crystal_structure": "simulation.generate",
    "clear_structure_cache": "simulation.cache.clear",
}


def describe(operation):
    if operation not in CAPABILITIES:
        raise CapabilityError(
            "CAPABILITY_UNAVAILABLE", f"Unknown capability: {operation}"
        )
    return deepcopy(CAPABILITIES[operation])


def list_capabilities(skill_name=None):
    if skill_name is not None and skill_name not in SKILLS:
        raise CapabilityError("INVALID_ARGUMENT", "Unknown skill")
    return [
        describe(n)
        for n, s in CAPABILITIES.items()
        if skill_name is None or skill_name in s["skills"]
    ]
