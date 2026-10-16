# AIsa X Assistant — review package

Start with [the skill entry point](aisa-x-assistant/SKILL.md), then open [the HTML example](preview/report.html) or [the Markdown example](preview/report.md). Every post, account name, metric, and source destination in the examples is fictional. The example reports were generated offline.

## What this version implements

- AIsa-first access through an existing working MCP or plugin connection.
- OAuth onboarding for users who do not want to provide an API key; key-based access remains optional.
- A confirmed self account as the default target, with @handle, profile URL, or explicit numeric-ID alternatives.
- Short, progressive questions with a clear Skip / use defaults path.
- Separate handling of Following, For You, profile posts, liked posts, reposts/quotes, and platform viewing history.
- Collection-specific permission and capability checks before claiming access.
- Classification, evidence-linked summaries, and rankings that distinguish unknown metrics from zero and sample results from complete history.
- Markdown exports and self-contained HTML reports with local search, topic/collection filters, sorting, expandable evidence, and printing.

## Important design decisions

**AIsa sign-in and X account authorization are separate.** Signing into AIsa through GitHub does not establish the user's X identity. An authenticated X account or a handle explicitly identified as the user's own is needed to resolve “my account.”

**The collection is part of the request.** A profile timeline is not a home feed. A post's like count is not the user's liked-post list. A source that returns who reposted one post is not a complete share history. Missing access is not an empty collection.

**Skip has useful boundaries.** Optional analysis preferences fall back to documented defaults. Skipping required account information, access, or spending approval leads to free discovery, supplied-content analysis, or a clearly labeled preview.

**Reuse authorization without confirmation loops.** A working connection skips onboarding. Adequate scope and spending approval cover subsequent calls; the skill adds no per-page approval requirement. The active tool's actual approval rules still apply.

## Files to review

| File | Purpose |
| --- | --- |
| [SKILL.md](aisa-x-assistant/SKILL.md) | Agent workflow and capability boundaries. |
| [interaction.md](aisa-x-assistant/references/interaction.md) | Defaults, skippable questions, and example exchanges. |
| [connection.md](aisa-x-assistant/references/connection.md) | OAuth/key onboarding, discovery, quotes, and failures. |
| [reporting.md](aisa-x-assistant/references/reporting.md) | Normalized data contract and report requirements. |
| [render_report.py](aisa-x-assistant/scripts/render_report.py) | Standard-library-only offline Markdown/HTML renderer. |
| [sample-input.json](preview/sample-input.json) | Fictional data used to demonstrate the presentation. |

The installable skill is the `aisa-x-assistant` subfolder. This review record describes the portable skill and fictional example, with validation performed on 16 October 2026.

## Suggested prompts

```text
Use $aisa-x-assistant to organize my liked posts. Skip optional preferences.

Use $aisa-x-assistant to summarize @example's latest 5 public posts.

Use $aisa-x-assistant to group my reading by topic and show the most-liked
posts in each group. Give me Markdown and HTML.

I do not want to share an API key. Help me connect through AIsa sign-in.

Skip account connection and show me a fictional report preview.
```

## Validation

The review build passed the skill structure validator and local-reference checks. Renderer checks covered ranking, tie handling, missing versus zero metrics, latest ordering, large string IDs, duplicate rejection, timestamp validation, invalid evidence references, empty inputs, multiple action observations, HTML/Markdown escaping, unsafe URL rejection, and the inline-script integrity hash.

The HTML example was opened in a browser. Search, empty results, topic filters, collection filters, combined filters, resetting filters, sorting, keyboard focus order, and keyboard disclosure toggling were exercised. It reflowed at 320 CSS pixels without horizontal overflow. No browser console errors were observed.

The interaction cases were reviewed against the written workflow, not executed by an independent agent. Live private X reads, X OAuth consent, paid data calls, a screen-reader session, and the system print dialog were not exercised for this review build. Capabilities such as private home feeds, liked-post lists, and platform viewing history remain conditional on the current AIsa interfaces and the relevant account authorization.

## Regenerate the example

From this review folder, run:

```sh
python3 aisa-x-assistant/scripts/render_report.py \
  --input preview/sample-input.json \
  --output preview \
  --format both
```

No account login, API key, network access, or third-party Python package is needed to render the example. All skill instructions and source comments are in English; reports follow the user's requested language.
