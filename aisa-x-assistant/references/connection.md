# AIsa connection and discovery

## Connection selection

1. Honor an explicit connection choice and reuse a working authorized AIsa MCP or AIsa plugin.
2. Otherwise prefer the host's native Streamable HTTP MCP at `https://mcp.aisa.one/mcp`.
3. If the user has no key or declines to supply one, use AIsa browser OAuth. A personal API key is optional.
4. If the user explicitly chooses a key, let the host's secure credential configuration provide it as a Bearer token. Do not copy it into skill files, exports, command-line arguments, or chat output.

Keep configuration and authentication distinct. Where currently documented, the free protected MCP check is `use` with `operation_id: account`. Check its live schema first, and extract only necessary status; its result may include credential metadata. Reuse a successful check during the session. Do not run a paid endpoint as a login test.

A browser session signed into AIsa does not prove that a particular MCP client's credential works. Conversely, a failed tool credential does not prove the user failed to log in. Preserve the exact error and request ID, identify the failing layer, and avoid unsupported root-cause claims.

The host may require a new session to expose a newly added MCP. Follow the host's supported reload mechanism. Do not silently install a different transport, reconfigure unrelated models, or switch to a separately authenticated cloud plugin to bypass an unresolved connection.

## Discovery contract

Use live metadata rather than assuming a prefix or version. Typical router tool names are:

| Tool | Role |
| --- | --- |
| `search` | Discover capabilities and exact operation IDs. |
| `get_details` / `batch_get_schema` | Obtain missing input/output schemas, read-only flags, side effects, and documentation. |
| `batch_quote` | Quote exact call arguments without executing them. |
| `batch_use` | Execute already quoted, authorized calls, at most 20 independent calls per batch. |

Search the whole user goal first, then use simpler atomic searches for missing collections. Do not let an unhelpful category filter or empty relevance result prove absence. After one simpler retry, describe what was and was not found. Save and reuse Search's `session_id`; pass `search_id` when supported by the current schema.

Construct arguments only from successful schemas. Treat plans as potentially partial. A `GET` description or familiar name alone is not enough when side effects or permissions are unclear. A login endpoint, a like action, a retweeter list, and a user's liked-post collection are different operations.

Public-post discovery can consider capabilities such as latest profile posts, keyword/date search, and post lookup. Never assume a home-feed, liked-post, or history endpoint is available because it appears in a third-party platform's own API documentation. Confirm that the current AIsa connection exposes it.

## Fees and failure handling

- Quote the exact tool IDs and arguments before executing. Re-quote a changed call; a next-page cursor creates changed arguments.
- Follow the active tool's approval contract. Reuse adequate user approval; avoid additional per-call confirmation rules invented by this skill. An `auto_execute_eligible` value is not explicit user approval where explicit approval is required.
- Show estimates as estimates. Missing or failed quotes do not mean free. A minimum price is not a maximum. A task cap needs a guaranteed quote, a documented enforceable cap, or a provable bound.
- Do not execute past the authorized scope or remaining allowance. No silent paid retries. Dependent pages run sequentially; independent supported reads can be batched.
- For `401` or `invalid_credentials`, identify which connection failed and preserve the request ID. Offer a focused reauthentication once; do not loop after repeated identical failures.
- For insufficient balance or a required subscription, explain the actual message. Do not call it a missing key or retry to test availability.
- For rate limits or transient failures, preserve partial results. Retry only when authorized and after the appropriate backoff; otherwise report the gap.
- Verify both the MCP envelope and provider business status. An HTTP success with a provider error is not a successful read. Report actual charges when returned and mark unreported charges as unknown.

## Evidence and onboarding links

- [AIsa MCP connection and router overview](https://www.aisa.one/mcp#connect)
- [Current agent quickstart](https://aisa.one/docs/agent-quickstart.md)
- [Authentication](https://aisa.one/docs/guides/authentication.md)

These describe the provider's supported connection mechanisms. Current schemas, permissions, account access, and quotes still need runtime verification. This skill does not assert that AIsa always uses X's official API upstream or that any integration is exempt from platform controls.
