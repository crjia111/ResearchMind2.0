# Migration validation and release scope

Implementation target: portable Skill package/runtime with an optional AgentScope 2.0.12 adapter, based on ResearchMind2.0 ce3e2ff8309a7c9fdc79e42800b8846c8d0bfe35.

## Implemented and checked locally

- Nine Skill resources in three 4/1/4 bundles, with fixed-skill scripts, parameters, output contracts and version checks.
- 42 legacy tool registrations mapped to stable capabilities; shared functions are not separate Skills.
- Framework-independent Python API, JSON CLI, SQLite session/artifact/job persistence, cancellation, timeout, stale-task failure and workspace compute serialization.
- Real ASE CIF validation, Unicode segment/search offsets, CSV export, source-specific paper searches, document ingestion, analysis/report model port, explicit evidence limits, vector integration and four database providers.
- Extracted scientific implementations with explicit model paths and no accepted mock fallback.
- AgentScope structured tools, schema reuse, true error states, professional role bindings, bounded delegation, durable state and neutral/legacy history handling.
- Default local startup runs backend and UI without MCP processes; no platform login or billing.
- Local-domain HTTP upload, selection, artifact/download and task endpoints.
- Portable wheel and standalone Skill ZIP build script; Windows/Linux Python CI matrix.

Local environment: Windows, CPython 3.12.14, AgentScope 2.0.12. Final commands and results are recorded below; no external model credentials or scientific weights are bundled.

## Verification

- `python -m pytest -q`: 40 tests passed, including real AgentScope execution against a local OpenAI-compatible protocol fixture.
- Fresh wheel installed and executed outside the checkout in a new environment with no AgentScope, ADK, MCP or FastMCP installed.
- All nine Skills passed the Skill structure validator.
- `npm run build`: TypeScript and Vite production build passed.
- `python scripts/check_local_startup.py`: actual UI, HTTP/WebSocket proxies, local statistics and shutdown/port cleanup passed.
- Public arXiv API smoke call: successful search, two paper records and a registered CSV artifact.
- Static undefined/unused-name checks and Git whitespace checks pass for new integration code.

A remaining websockets legacy-handler deprecation warning belongs to the existing WebSocket API version and does not fail tests. The front-end build retains existing bundle-size and mixed-import warnings.

## Explicit limits

- Real remote model analysis, MP/Tavily credentials, Embedding/Chroma service interoperability and numerical GPU calculations are not claimed as empirically validated here. Deterministic fixtures validate contracts and error handling; actual providers/models require separate prepared-environment acceptance.
- This machine has not run the Linux CI jobs. The workflow records Windows/Linux Python 3.11/3.12 coverage when it executes on GitHub.
- Kappa-P and Kappa-MTP retain the original 300 K formulas; requests at other temperatures are rejected.
- Energy/forces are model predictions. Legacy convex-hull defaults are not presented as validated formation/decomposition energy or stability evidence.
- Initial vector ingestion supports saved arXiv papers only. PDF extraction does not imply OCR support for image-only documents.
- The shipped local model client targets OpenAI-compatible chat endpoints; other provider protocols need their own model-port implementation.
- The bundled scientific code retains its upstream origin. Model and upstream license/redistribution conditions still apply.
- Other Agent frameworks are not labeled formally supported merely because the portable CLI is available.

The design document remains a target specification. This release provides the executable migration and local integration; the prepared-environment numerical/provider checks above remain necessary before claiming every scientific acceptance criterion complete.
