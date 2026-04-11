# Tool Calling Contract

The policy workflow makes PolicyNIM visible as MCP tools instead of burying
standards in a prompt.

Expected policy trajectory:

1. `classify_coding_task`
2. `policy_preflight`
3. `compile_policy_constraints`
4. `emit_coding_artifact`
5. `revise_failed_artifact` only if evaluation fails

`policy_search` remains available for insufficient or ambiguous preflight
context, but the golden refresh-token scenario should be satisfied by
`policy_preflight`.

The deterministic evaluator treats a policy run without `policy_preflight` as a
failure because the workflow did not prove MCP tool use.
