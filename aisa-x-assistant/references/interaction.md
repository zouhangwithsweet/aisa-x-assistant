# Interaction and defaults

Use the user's language. Keep questions short, relevant, and optional where a safe default exists. Prefer the host's choice/question UI when available; ordinary text works everywhere. Do not ask users to repeat values already present in the conversation.

## Preference defaults

| Setting | Default | Meaning of Skip |
| --- | --- | --- |
| Target | The user's confirmed connected X account | Reuse a confirmed identity; if none exists, continue discovery without a target and ask once when a real read requires it. |
| Collection | Following home timeline for a general personal reading brief | Keep this intended collection; if unsupported, offer alternatives instead of silently using profile posts. |
| “My timeline” | Ask once: home feed or posts published by me | Following home feed; state this choice. |
| Window | Last 7 days in the user's timezone | Apply only to timestamps supported by the source. For private actions without action timestamps, explain the limitation first. |
| Size | Up to 50 qualifying posts, within access and spending limits | Fewer are acceptable when the source or budget stops the read; report the count. |
| Order | Newest first | “Most liked” changes to received like count descending. |
| Topics | Infer a small set from retrieved content | No forced predefined taxonomy. |
| Format | Markdown | Use HTML or both when requested. |
| Preferences | Current conversation only | Do not create a persistent account profile. |
| Spending | Existing explicit allowance, if any | Free checks and preview only when paid authorization is required but absent. |

These are analysis preferences, not authorizations to access private information or spend money. A source-specific request such as “my liked posts” overrides the general home-feed default.

## Starting prompt when the task is vague

> I can prepare a brief from your X content. Start with your connected account and defaults, choose another account, or customize? You can say “skip” to use defaults.

If the user customizes, ask only the next two useful questions, for example:

> Which collection: Following feed, your posts, liked posts, reposts/quotes, or viewing history? Which output: Markdown, HTML, or both? Skip uses the Following feed and Markdown.

Do not present this menu when the user already asked for a specific target and collection.

## Important cases

**Already connected to AIsa**

Reuse a successful protected check from this session. Skip signup, key entry, skill installation, and reconnect instructions. Resolve X identity only if the requested collection needs it.

**No key and no connection**

> You can connect AIsa through browser sign-in without sharing an API key. Choose “Connect with AIsa”, use securely configured credentials you already have, or skip connection and preview the report.

Follow the host's documented connector flow. The user performs any required consent. Do not turn an OAuth flow into a request to paste a secret.

**“Use my account”, but X identity is unknown**

> Which X account should I use? Enter an @handle, profile URL, or numeric ID, or connect X through the supported authorization flow. Skip keeps this in preview mode until an account is identified.

One account already analyzed is not automatically the user's own account. If a supplied identifier could be either a numeric handle or a numeric user ID, ask or use an unambiguous `id:` prefix; do not guess.

**Another user's data**

Accept an @handle, profile URL, or explicit numeric ID, and state the interpreted identity. Public-post analysis needs no claim of ownership. Private likes/history still need a supported interface and authorization for that account; changing the target never expands access.

**Private endpoint unavailable**

> AIsa currently exposes profile posts here, but I have not found a matching read interface for your liked-post list. Continue with your public posts, analyze an export you provide, generate a report for the sources that worked, or preview the layout?

Do not describe an unavailable collection as empty. If the user skips this choice, preserve a partial report for successful collections and list the missing collection.

**Cost approval required**

Present the concrete call scope, quote type, expected charge, and any provable maximum together. Offer an appropriate task allowance and a preview alternative. Existing scope and cost approval remain valid; do not ask on every page. If the user requires a cap and there is no defensible bound, explain that before execution. A skipped cost choice leaves paid work pending.

## Example behaviors to check

- “Summarize @example's latest 5 posts.” Reuse AIsa, identify the public-post endpoint, quote the bounded request; skip optional questions.
- “Organize my likes; skip preferences.” Use the confirmed self identity, liked-post collection, inferred topics, and Markdown. Do not convert likes into public posts when the collection is unavailable.
- “Show another user's viewing history.” Explain the access boundary and offer public-post analysis; do not attempt private-account access.
- “No key.” Offer OAuth and a fictional preview, not a forced API-key form.
- “HTML, most liked, last week.” Resolve the collection if missing and state whether “last week” applies to post time or an action timestamp.
