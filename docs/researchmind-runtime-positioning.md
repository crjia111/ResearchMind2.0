# ResearchMind runtime positioning

ResearchMind is a local-first research workbench. Its scientific layer owns
projects, provenance, notebooks, skills, connectors, artifacts, and reproducible
runs. The runtime layer is an implementation detail behind the SDK boundary.

The default runtime is a supervised local sidecar. It communicates with the
desktop through the SDK and stays replaceable at that boundary, while the
scientific workflow remains stable. This keeps model providers, skills, MCP
servers, and local files configurable without coupling the research layer to a
particular UI or hosting service.

The desktop application can also expose its runtime through ACP for compatible
editor integrations. ACP is an interoperability surface; it does not replace
the local scientific data model or move workspace data to a hosted service.
