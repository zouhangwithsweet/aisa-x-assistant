# Data and report contract

## Evidence rules

Resolve the requested collection before analysis. Record the target's identity evidence without storing a token. Separate `created_at`, `action_at`, and `generated_at`; convert dates with the user's timezone and preserve offsets. A like list without like timestamps cannot support an action-date filter. A pinned post is not necessarily one of the latest posts.

Normalize a successful response using its actual schema. Keep IDs as strings; consolidate repeated posts while retaining source memberships and action observations. Use the most recent observed metric snapshot only when its retrieval time is known. Do not multiply a post's received likes merely because it appears in two collections.

Topic counts may overlap because a post can have several topics. Distinguish received-post metrics from counts of the user's observed actions. The renderer sorts received-post metrics only; compute an author/topic action-frequency table separately and explain its denominator.

Record inaccessible collections, failed pages, missing metrics, timestamp gaps, exclusions, the pagination stop reason, and whether results are partial. A current snapshot cannot prove an all-time maximum. Do not label private content empty merely because access failed.

## Renderer input

The standard-library-only helper accepts a JSON object with these fields. Optional fields can be omitted; unavailable metrics must be `null`, never zero.

```json
{
  "meta": {
    "title": "My X reading brief",
    "target": "@confirmed_account",
    "generated_at": "2026-10-16T18:00:00+08:00",
    "timezone": "Asia/Shanghai",
    "language": "en",
    "collections": ["Liked posts"],
    "requested_window": "Last 7 days",
    "time_basis": "Post creation time; like timestamps unavailable",
    "coverage": "Partial: one authorized page, 5 qualifying posts",
    "stop_reason": "Requested item count reached",
    "pages_fetched": 1,
    "sort": "likes",
    "sample": false,
    "cost": {"actual_usd": null, "estimated_usd": null}
  },
  "overview": "A concise evidence-based overview.",
  "findings": [
    {"title": "A recurring topic", "summary": "Explain the observed pattern.", "post_ids": ["post-id"]}
  ],
  "limitations": ["This ranking describes only the retrieved collection."],
  "posts": [
    {
      "id": "post-id",
      "author": "@author",
      "url": "https://x.com/author/status/1234567890123456789",
      "created_at": "2026-10-15T09:00:00+08:00",
      "action_at": null,
      "actions": [{"kind": "Liked post", "at": null}],
      "headline": "A short descriptive headline",
      "summary": "A faithful paraphrase with enough context to be useful.",
      "excerpt": "An optional short excerpt.",
      "topics": ["Research"],
      "collections": ["Liked posts"],
      "metrics": {"likes": 120, "reposts": 8, "replies": 3, "views": null},
      "notes": ["Like timestamp unavailable."]
    }
  ]
}
```

Use a valid timestamp with an offset or `Z`; a post's `created_at` may be `null` when unknown. `meta.sort` is `latest`, `likes`, `reposts`, `replies`, or `views`. `posts` may be empty; include an explanation in limitations. `meta.sample=true` adds a prominent fictional-preview notice to both formats. Optional `labels` can map the renderer's English UI strings to the report language.

Use `actions` to preserve multiple observed actions on one deduplicated post. Only include an action when the source actually proves it, and keep an unavailable action timestamp `null`. An optional single `action_at` is a convenience field, not a replacement for multiple distinct actions.

The renderer validates IDs, timestamps, metrics, and evidence references. Duplicate IDs are rejected so the agent must normalize them without losing source membership. It does not classify raw posts, invent missing fields, collect data, or promise source completeness.

## Output behavior

Markdown contains scope, overview, findings, topic groups with post references, a ranked evidence table, item-level summaries/excerpts, limitations, and reported cost. HTML contains the same evidence with local search, topic/collection filters, sorting, expandable excerpts/provenance, and print styling. Filters update the visible count; they do not imply a broader source search.

The HTML is self-contained. It uses no remote fonts, media embeds, analytics, or network calls. Post content is escaped, unsafe URL schemes are discarded, and the interactive code never inserts post text with `innerHTML`. All content remains readable without JavaScript; controls appear only when JavaScript runs.

Before delivery, run the renderer on the real normalized data, inspect both formats, and test search, empty results, filtering, sorting, and keyboard focus. Check a narrow viewport and printing when the host supports it. Do not claim screen-reader validation if none was performed. Summaries and topic labels use the report's language; translate UI labels through `labels` when needed.

Store only the user's requested report outputs. Raw provider responses and normalized personal data are intermediate artifacts, not a permanent archive unless requested. No credentials, login traces, or account secrets belong in the report or the skill package.
