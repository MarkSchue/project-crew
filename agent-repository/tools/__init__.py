"""Package marker for the tool library (masterplan section 7.1 `tools/`).

Tools here are small, typed, independently testable units with a contract
in the tool registry (masterplan section 14.1). They do not live inside
`src/agent_platform` because they are versioned alongside the registry and
are consumed by agents through the tool registry, not imported as
application code.
"""
