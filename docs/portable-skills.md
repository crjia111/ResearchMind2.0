# Portable ResearchMind skills

This release implements a framework-independent Python package and CLI. AgentScope 2.0.12 is the first optional adapter. Reading a Skill does not install dependencies or register tools.

## Install the application

Use Python 3.11 or 3.12 and Node.js 18+:

```sh
uv sync --locked
uv run python -m services.launcher --check
uv run python -m services.launcher
```

The default launcher starts only HTTP, WebSocket and the UI. It does not start the three legacy MCP servers. Configure the model/API settings in .env; login and platform billing remain removed. See .env.skills.example for optional model and embedding settings.

Knowledge indexing is optional: use uv sync --extra vector to install ChromaDB, then configure an Embedding provider. Standalone database use requires researchmind-skills[database].

GPU dependencies are optional: prepare a compatible simulation environment separately with researchmind-skills[simulation]. The default app does not install CUDA/PyTorch. Model weights are never downloaded automatically.

## Install portable skills without AgentScope

From a checkout:

```sh
python -m pip install "./packages/researchmind-skills[paper]"
researchmind-skills install --bundle literature --target /your/agent/skills
researchmind-skills install --bundle materials-db --target /your/agent/skills
researchmind-skills install --bundle simulation --target /your/agent/skills
researchmind-skills install --skill paper-analysis --target /your/agent/skills
researchmind-skills doctor --skill paper-analysis --target /your/agent/skills
```

Once a wheel has been built, installing that wheel does not require the checkout. Build it with:
```sh
python -m build --wheel packages/researchmind-skills
```

Each Skill includes SKILL.md, its own references, a fixed-skill script and a versioned manifest. The target Agent must support loading instructions and executing Python/CLI, or provide its own native tool adapter. No universal Agent install directory or universal framework support is assumed.

Bundles contain 4 literature, 1 database and 4 simulation skills. Resources, enabled host bindings and executable capabilities are separate states. Installing a bundle does not install dependencies, credentials, models or services.

## Execute

```sh
researchmind-skills capabilities describe papers.search --output-format json
researchmind-skills run papers.search --skill literature-search --input-file request.json --workspace ./research-work --wait
python /your/agent/skills/literature-search/scripts/run.py run papers.export_csv --input-file records.json --workspace ./research-work
researchmind-skills artifacts import ./research-work/input.cif --workspace ./research-work
researchmind-skills worker run --workspace ./research-work
researchmind-skills jobs status JOB_ID --workspace ./research-work --session default
researchmind-skills jobs result JOB_ID --workspace ./research-work --session default
```

JSON payloads contain only business parameters. Identity, workspace and session are supplied by the local configuration or host. Import roots are checked; operations refer to registered artifact IDs. Each session has independent paper selection, analysis and knowledge data.

With JSON output, stdout contains one result; logs use stderr. Exit codes are 0 completed/accepted, 2 invalid arguments, 3 partial, 4 capability/dependency failure, 5 internal error and 130 cancellation. Always inspect status: accepted only means a persistent worker has accepted the job.

Long operations with --wait run in an isolated subprocess. A workspace compute slot serializes scientific execution, and the OS releases it if the process exits. Stale task supervisors are reported as failed rather than automatically re-running computations. Without --wait they require a running worker. Cancel through the job API; closing a waiting client does not promise background completion. Reuse request IDs only for retries of the same operation and exact payload.

## Adapter

Install researchmind-skills[agentscope] only for AgentScope integration. The adapter uses the public registry's JSON Schema, maps failed results to ToolResultState.ERROR and shares the exact same runtime. Professional role bindings remain 4/1/4; coordination and experiment planning use bounded specialist delegation.

Third-party frameworks should load the same Skill resources and invoke the CLI, or map registry schemas to their own tool definitions and call Runtime.execute. Framework classes do not belong in the business implementation.

## Scientific scope and environment limits

- All 42 original tool registrations have a mapping in schemas/legacy-tools.json. Consolidated capability IDs are intentionally fewer than old aliases.
- CIF validation uses actual ASE parsing; it does not consider nonempty but unparsable input valid.
- Text offsets are Unicode character offsets; CSV fields and embedded newlines round-trip correctly.
- Scientific implementations under vendor/ were extracted from the original repository, with package imports and explicit model paths. Legacy source remains in mcp_servers/ for comparison, not as a dependency of the wheel.
- MatterSim requires MATTERSIM_MODEL_PATH. Optional convex-hull references require GNOME_DATA_DIR; absent references cannot be presented as validated stability.
- CrystaLLM requires CRYSTALLM_MODEL_DIR and its optional dependencies.
- Kappa requires KAPPA_MODEL_DIR and KAPPA_ATOM_INIT. The original formulas are fixed at 300 K. This release rejects other temperatures rather than silently labeling a 300 K result as another temperature.
- No mock thermal conductivity fallback is accepted. Missing dependencies or models return explicit errors.
- Initial vector ingestion accepts saved arXiv papers only. Configure either Google embedding credentials or an explicit OpenAI embedding model. Model and chunk versions isolate indexes.
- Real provider credentials and scientific weights are not included. Local protocol tests prove integration and error handling, not provider availability, numerical accuracy or natural-language routing quality for every model.

## Validation

```sh
python -m pytest -q
cd ui
npm ci
npm run build
```

Tests exercise the actual AgentScope package with a local OpenAI-compatible fixture, shared API/CLI behavior, real CIF parsing, wheel installation into a clean environment without any Agent framework, local uploads/downloads and existing no-auth routes. Optional real model/GPU tests must be run in a prepared environment before claiming numerical acceptance. Never replace them with mock values.

Do not remove the migration worktree until the tested commit is on main and pushed successfully. Historical ADK files are read as fallback; new state is versioned in the workspace. Roll back by selecting the previous Git release and keeping the new workspace data intact.

Standalone Skill ZIP resources can be built with python scripts/build_portable_skills.py --out dist/skills. See [validation and remaining environment checks](migration-validation.md).
