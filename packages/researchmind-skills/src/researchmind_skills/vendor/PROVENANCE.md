# Scientific source provenance

The implementations in src/researchmind_skills/vendor were extracted from crjia111/ResearchMind2.0, commit ce3e2ff8309a7c9fdc79e42800b8846c8d0bfe35:

- simulation/modules/mattersim_energy.py
- simulation/crystallm/generate_crystal.py, crystallm/ and the three pipeline scripts
- simulation/kappa_lib/

Original code comments, attribution and algorithm bodies are retained. Adaptations replace repository-path imports, require explicit model/data locations, isolate work directories and propagate subprocess failures. The thermal-conductivity formulas are the original 300 K formulas. No model weights are included. Do not infer numerical validation from transport/contract tests.

Original embedded attribution includes nanoGPT in crystallm/_model.py. The source repository does not supply a root license grant; external redistribution must honor applicable upstream licenses and permissions. This file records origin, not a new license.
