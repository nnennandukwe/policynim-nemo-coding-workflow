# Consume PolicyNIM source quotations as references

PolicyNIM PR #158 keeps its public JSON fields but places whole selected policy bodies in `plan_steps`. Those bodies include conditions, examples and exceptions. This demo currently labels every step `must` and prepends it to a generated implementation plan, changing the meaning of those sections.

Recognize the exact source-extractive service summary/rationale contract and retain its bodies as source references. Add typed source references with body, owner ID/title and citation IDs in backward-default `source_references` fields to the demo's compiled constraints and artifact; preserve old fields and the historical synthesized-response path. The prompt must label these bodies as unverified source material whose applicability and conditions need review. The fixed demo generator mustn't claim it implemented them. Its evaluator must retain an explicit failed source-applicability review check when references exist.

Use the ordinary public compile, generator and evaluator paths for a full-condition/custom-heading fixture. Check malformed extractive envelopes, legacy synthesized responses and historical model loading. A marker identifies response semantics; it doesn't authenticate a server, prove quotation fidelity or establish applicability. No external calls are needed for these regressions.

Relevant standards retrieved through Qodo require coordinated producer/consumer validation (1060877, error), preservation of existing response fields (1060851/1060863, error), valid Literal defaults (2119709, error), English identifiers and text (8184/7205/576985, warning), descriptive names (613754/699152, warning) and docstrings for changed functions (784431, warning). Portal/Swift/config-specific rules don't apply to this Python consumer slice. No endpoint, dependency or settings change is planned.

Gate: locked dependency sync, Ruff, full offline suite, language verification, final local Qodo, ready PR and exact-head remote review/CI. Preserve the dirty primary checkout. A successful offline fixture isn't hosted or model-quality evidence.
