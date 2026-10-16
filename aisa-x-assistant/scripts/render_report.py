#!/usr/bin/env python3
"""Render normalized X evidence to Markdown and offline HTML. No network access."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

METRICS = ("likes", "reposts", "replies", "views")
SORTS = ("latest",) + METRICS


def timestamp(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Timestamps must be strings with an explicit timezone.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include an offset or Z.")
    return parsed


def safe_url(value):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        return ""
    try:
        p = urlsplit(value)
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
            return ""
        return quote(value, safe=":/?#[]@!$&'*+,;=%-._~")
    except ValueError:
        return ""


def md(value):
    text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_{\[\]}|])", r"\\\1", text).replace("\r", "").replace("\n", " ")


def esc(value):
    return html.escape(str(value), quote=True)


def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("meta"), dict):
        raise ValueError("Input needs a meta object and a posts array.")
    meta = data["meta"]
    for key in ("title", "target", "generated_at", "coverage", "time_basis"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            raise ValueError(f"meta.{key} must be a nonempty string.")
    timestamp(meta["generated_at"])
    ZoneInfo(meta.get("timezone", "UTC"))
    if "sample" in meta and type(meta["sample"]) is not bool:
        raise ValueError("meta.sample must be a boolean.")
    if not isinstance(meta.get("cost", {}), dict):
        raise ValueError("meta.cost must be an object.")
    if not re.fullmatch(r"[A-Za-z0-9-]+", meta.get("language", "en")) or meta.get("direction", "auto") not in ("auto", "ltr", "rtl"):
        raise ValueError("Use a valid language tag and auto, ltr, or rtl direction.")
    if meta.get("sort", "latest") not in SORTS:
        raise ValueError("Unsupported sort metric.")
    posts = data.get("posts")
    if not isinstance(posts, list):
        raise ValueError("posts must be an array.")
    ids = set()
    for post in posts:
        if not isinstance(post, dict):
            raise ValueError("Each post must be an object.")
        for key in ("id", "author", "headline", "summary"):
            if not isinstance(post.get(key), str) or not post[key].strip():
                raise ValueError(f"Each post needs a nonempty string {key}.")
        if post["id"] in ids:
            raise ValueError("Duplicate post ID; normalize and merge collection memberships first.")
        ids.add(post["id"])
        timestamp(post.get("created_at"))
        timestamp(post.get("action_at"))
        actions = post.get("actions", [])
        if not isinstance(actions, list):
            raise ValueError("post.actions must be an array.")
        for action in actions:
            if not isinstance(action, dict) or not isinstance(action.get("kind"), str):
                raise ValueError("Each observed action needs a kind string.")
            timestamp(action.get("at"))
        for key in ("topics", "collections", "notes"):
            value = post.get(key, [])
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ValueError(f"post.{key} must be an array of strings.")
        post.setdefault("topics", [])
        post.setdefault("collections", [])
        metrics = post.setdefault("metrics", {})
        if not isinstance(metrics, dict):
            raise ValueError("post.metrics must be an object.")
        for metric in METRICS:
            value = metrics.setdefault(metric, None)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{metric} must be a nonnegative integer or null.")
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("findings must be an array.")
    for finding in findings:
        if not isinstance(finding, dict) or not all(isinstance(finding.get(k), str) for k in ("title", "summary")):
            raise ValueError("Each finding needs a title and summary.")
        refs = finding.get("post_ids", [])
        if not isinstance(refs, list) or not all(isinstance(i, str) and i in ids for i in refs):
            raise ValueError("Finding evidence must reference included post IDs.")
    limits = data.get("limitations", [])
    if not isinstance(limits, list) or not all(isinstance(x, str) for x in limits):
        raise ValueError("limitations must be an array of strings.")
    labels = data.get("labels", {})
    if not isinstance(labels, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in labels.items()):
        raise ValueError("labels must map English UI strings to translated strings.")
    for field in ("actual_usd", "estimated_usd"):
        value = meta.get("cost", {}).get(field)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
            raise ValueError("Reported costs must be nonnegative numbers or null.")
    return data


def ordered(posts, mode):
    def key(post):
        dt = timestamp(post.get("created_at"))
        created = dt.timestamp() if dt else None
        value = created if mode == "latest" else post["metrics"].get(mode)
        return (value is None, -(value or 0), -(created or 0), post["id"])
    return sorted(posts, key=key)


class Report:
    def __init__(self, data):
        self.data = validate(data)
        self.meta = data["meta"]
        self.tr = lambda s: data.get("labels", {}).get(s, s)
        self.mode = self.meta.get("sort", "latest")
        self.posts = ordered(data["posts"], self.mode)
        self.anchors = {p["id"]: f"post-{i + 1}" for i, p in enumerate(self.posts)}
        self.topics = sorted({t for p in self.posts for t in p["topics"]})
        self.collections = sorted({s for p in self.posts for s in p["collections"]})
        self.zone = ZoneInfo(self.meta.get("timezone", "UTC"))

    def time(self, value):
        dt = timestamp(value)
        return dt.astimezone(self.zone).strftime("%d %b %Y, %H:%M %Z") if dt else self.tr("Unknown")

    def number(self, value):
        return f"{value:,}" if value is not None else self.tr("Unknown")

    def cost(self, field):
        value = self.meta.get("cost", {}).get(field)
        return f"${value:.6f}".rstrip("0").rstrip(".") if value is not None else self.tr("Not reported")

    def scope(self):
        return [
            ("Account", self.meta["target"]),
            ("Collections", ", ".join(self.meta.get("collections", self.collections)) or self.tr("Not specified")),
            ("Requested window", self.meta.get("requested_window", self.tr("Not specified"))),
            ("Time basis", self.meta["time_basis"]),
            ("Retrieved", self.time(self.meta["generated_at"])),
            ("Timezone", self.meta.get("timezone", "UTC")),
            ("Coverage", self.meta["coverage"]),
            ("Pages read", self.meta.get("pages_fetched", self.tr("Unknown"))),
            ("Stop reason", self.meta.get("stop_reason", self.tr("Not reported"))),
        ]

    def markdown(self):
        tr = self.tr
        lines = [f"# {md(self.meta['title'])}", ""]
        if self.meta.get("sample"):
            lines += [f"> **{md(tr('Fictional preview'))}.** {md(tr('Illustrative data only. No X account has been read.'))}", ""]
        lines += [f"- **{md(tr(k))}:** {md(v)}" for k, v in self.scope()]
        lines += ["", f"## {md(tr('Overview'))}", "", md(self.data.get("overview", tr("No overview provided."))), ""]
        for f in self.data.get("findings", []):
            refs = ", ".join(f"[{md(i)}](#{self.anchors[i]})" for i in f.get("post_ids", []))
            lines += [f"### {md(f['title'])}", "", md(f["summary"]), "", f"{md(tr('Evidence'))}: {refs or md(tr('Not specified'))}", ""]
        lines += [f"## {md(tr('Topics'))}", "", md(tr("Topic groups can overlap.")), ""]
        for topic in self.topics:
            members = [p for p in self.posts if topic in p["topics"]]
            links = ", ".join(f"[{md(p['id'])}](#{self.anchors[p['id']]})" for p in members)
            lines += [f"- **{md(topic)} ({len(members)}):** {links}"]
        lines += ["", f"## {md(tr('Ranked evidence'))}", "", f"{md(tr('Order'))}: {md(tr(self.mode.title()))}. {md(tr('Ranks describe the included sample; missing metrics are not zero.'))}", ""]
        lines += ["| " + " | ".join(md(tr(x)) for x in ("Rank", "Post", "Likes", "Reposts", "Replies", "Views")) + " |", "| --- | --- | --- | --- | --- | --- |"]
        rank = 0
        for p in self.posts:
            known = p.get("created_at") is not None if self.mode == "latest" else p["metrics"][self.mode] is not None
            rank += int(known)
            url = safe_url(p.get("url"))
            link = f"[{md(p['headline'])}]({url})" if url else md(p["headline"])
            lines += ["| " + " | ".join([str(rank) if known else md(tr("Unknown")), link] + [md(self.number(p["metrics"][m])) for m in METRICS]) + " |"]
        if not self.posts:
            lines += ["", md(tr("No posts were included. Review the coverage and limitations."))]
        lines += ["", f"## {md(tr('Post notes'))}", ""]
        for p in self.posts:
            lines += [f'<a id="{self.anchors[p["id"]]}"></a>', f"### {md(p['headline'])}", "", f"**{md(p['author'])}** · {md(self.time(p.get('created_at')))}", "", md(p["summary"]), ""]
            if p.get("excerpt"):
                lines += ["> " + md(p["excerpt"]), ""]
            url = safe_url(p.get("url"))
            lines += [f"- {md(tr('Collections'))}: {md(', '.join(p['collections']) or tr('Unknown'))}", f"- {md(tr('Topics'))}: {md(', '.join(p['topics']) or tr('Unclassified'))}", f"- {md(tr('Action time'))}: {md(self.time(p.get('action_at')))}"]
            if url:
                lines += [f"- [{md(tr('Open source post'))}]({url})"]
            lines += [f"- {md(a['kind'])}: {md(self.time(a.get('at')))}" for a in p.get("actions", [])]
            lines += [f"- {md(note)}" for note in p.get("notes", [])] + [""]
        lines += [f"## {md(tr('Limitations and cost'))}", ""]
        lines += [f"- {md(x)}" for x in self.data.get("limitations", [])]
        lines += [f"- {md(tr('Estimated charge'))}: {md(self.cost('estimated_usd'))}", f"- {md(tr('Reported actual charge'))}: {md(self.cost('actual_usd'))}", ""]
        return "\n".join(lines)

    def html(self):
        tr = self.tr
        e = lambda s: esc(tr(s))
        sample = f'<aside class="preview"><strong>{e("Fictional preview")}</strong> · {e("Illustrative data only. No X account has been read.")}</aside>' if self.meta.get("sample") else ""
        scope = "".join(f"<div><dt>{e(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in self.scope())
        findings = []
        for f in self.data.get("findings", []):
            refs = " ".join(f'<a href="#{self.anchors[i]}">{esc(i)}</a>' for i in f.get("post_ids", []))
            findings.append(f'<article><h3>{esc(f["title"])}</h3><p>{esc(f["summary"])}</p><p class="refs">{e("Evidence")}: {refs}</p></article>')
        topic_counts = "".join(f'<span class="chip">{esc(t)} <b>{sum(t in p["topics"] for p in self.posts)}</b></span>' for t in self.topics)
        cards = []
        rank = 0
        for p in self.posts:
            known = p.get("created_at") is not None if self.mode == "latest" else p["metrics"][self.mode] is not None
            rank += int(known)
            metrics = "".join(f'<div><dt>{e(m.title())}</dt><dd>{esc(self.number(p["metrics"][m]))}</dd></div>' for m in METRICS)
            tags = "".join(f'<span class="chip">{esc(t)}</span>' for t in p["topics"])
            notes = "".join(f"<li>{esc(n)}</li>" for n in p.get("notes", []))
            notes += "".join(f"<li>{esc(a['kind'])}: {esc(self.time(a.get('at')))}</li>" for a in p.get("actions", []))
            url = safe_url(p.get("url"))
            link = f'<a class="source" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{e("Open source post")} <span class="sr">{esc(p["id"])}</span></a>' if url else f'<span>{e("Source link unavailable")}</span>'
            created = timestamp(p.get("created_at"))
            search = " ".join([p["author"], p["headline"], p["summary"], p.get("excerpt", "")] + p["topics"] + p["collections"])
            cards.append(f'''<article class="post" id="{self.anchors[p['id']]}" data-id="{esc(p['id'])}" data-created="{created.timestamp() * 1000 if created else ''}" data-metrics="{esc(json.dumps(p['metrics']))}" data-topics="{esc(json.dumps(p['topics']))}" data-collections="{esc(json.dumps(p['collections']))}" data-search="{esc(search)}">
              <div class="rank"><span class="sr">{e('Rank')} </span><span class="rank-value">{rank:02d}</span></div>
              <div class="post-body"><div class="post-meta"><bdi>{esc(p['author'])}</bdi><span>{esc(self.time(p.get('created_at')))}</span></div><h3>{esc(p['headline'])}</h3><p class="summary">{esc(p['summary'])}</p><div class="tags">{tags}</div><dl class="metrics">{metrics}</dl>
              <details><summary>{e('Read excerpt and provenance')}</summary><div class="details-body">{f'<blockquote>{esc(p["excerpt"])}</blockquote>' if p.get('excerpt') else ''}<p><b>{e('Collections')}:</b> {esc(', '.join(p['collections']) or tr('Unknown'))}</p><p><b>{e('Action time')}:</b> {esc(self.time(p.get('action_at')))}</p><ul>{notes}</ul></div></details>{link}</div></article>'''.replace(f'<span class="rank-value">{rank:02d}</span>', f'<span class="rank-value">{rank:02d}</span>' if known else '<span class="rank-value">—</span>'))
        options = lambda values, first: '<option value="">' + e(first) + '</option>' + ''.join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in values)
        sort_options = ''.join(f'<option value="{m}" {"selected" if m == self.mode else ""}>{e("Newest first" if m == "latest" else "Most " + m)}</option>' for m in SORTS)
        limits = ''.join(f"<li>{esc(n)}</li>" for n in self.data.get("limitations", []))
        count_template = esc(tr("{visible} of {total} posts"))
        fingerprint = base64.b64encode(hashlib.sha256(JS.encode()).digest()).decode()
        return f'''<!doctype html>
<html lang="{esc(self.meta.get('language', 'en'))}" dir="{esc(self.meta.get('direction', 'auto'))}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-{fingerprint}'; connect-src 'none'; img-src 'none'; base-uri 'none'; form-action 'none'"><title>{esc(self.meta['title'])}</title><style>{CSS}</style></head>
<body><a class="skip" href="#content">{e('Skip to report')}</a><main id="content" class="page"><header><div class="eyebrow">{e('X reading brief')} <span>{e('Read only')}</span></div><h1>{esc(self.meta['title'])}</h1><p class="lede">{esc(self.data.get('overview', ''))}</p>{sample}</header>
<dl class="scope">{scope}</dl><div class="stats"><div><strong>{len(self.posts)}</strong><span>{e('Included posts')}</span></div><div><strong>{len(self.topics)}</strong><span>{e('Topics')}</span></div><div><strong>{len(self.collections)}</strong><span>{e('Collections')}</span></div></div>
<section aria-labelledby="findings-title"><h2 id="findings-title">{e('What stands out')}</h2><div class="findings">{''.join(findings) or '<p>' + e('No findings were provided.') + '</p>'}</div><div class="topic-counts">{topic_counts}</div><p class="muted">{e('Topic groups can overlap.')}</p></section>
<section aria-labelledby="posts-title"><div class="section-head"><div><h2 id="posts-title">{e('Explore the posts')}</h2><p class="muted">{e('Ranks describe the included sample; missing metrics are not zero.')}</p></div><button type="button" id="print" hidden>{e('Print report')}</button></div>
<form id="filters" hidden><div class="field search"><label for="search">{e('Search posts')}</label><input id="search" type="search" name="q" autocomplete="off" placeholder="{e('Search text, authors, or topics')}"></div><div class="field"><label for="topic">{e('Topic')}</label><select id="topic">{options(self.topics, 'All topics')}</select></div><div class="field"><label for="collection">{e('Collection')}</label><select id="collection">{options(self.collections, 'All collections')}</select></div><div class="field"><label for="sort">{e('Order')}</label><select id="sort">{sort_options}</select></div><button type="button" id="clear">{e('Clear filters')}</button></form>
<noscript><p>{e('Filtering needs JavaScript. All included posts remain readable below.')}</p></noscript><p id="status" role="status" data-template="{count_template}"></p><p id="empty" class="empty" hidden>{e('No posts match these filters. Clear filters to show all posts.')}</p><div id="posts">{''.join(cards)}</div></section>
<footer><h2>{e('Coverage, limitations, and cost')}</h2><p>{esc(self.meta['coverage'])}</p><ul>{limits}</ul><dl class="cost"><div><dt>{e('Estimated charge')}</dt><dd>{esc(self.cost('estimated_usd'))}</dd></div><div><dt>{e('Reported actual charge')}</dt><dd>{esc(self.cost('actual_usd'))}</dd></div></dl><p class="muted">{e('This report is a snapshot of the included sources. Source content and engagement counts can change.')}</p></footer></main><script>{JS}</script></body></html>'''


CSS = """
:root{color-scheme:light;--paper:#f5f6f3;--ink:#17251e;--muted:#526158;--accent:#174e3c;--line:#dbe1da;--surface:#fff}
*{box-sizing:border-box}html{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:16px;-webkit-font-smoothing:antialiased;line-height:1.6}body{margin:0;background:var(--paper);color:var(--ink)}.page{max-width:1080px;margin:auto;padding:56px 32px 72px}.skip{position:fixed;inset-block-start:-100px;inset-inline-start:20px;background:#fff;padding:12px;z-index:5}.skip:focus{inset-block-start:12px}a{color:var(--accent);text-underline-offset:.18em;overflow-wrap:anywhere}h1,h2,h3,p{margin:0}h1{font-family:Georgia,serif;font-size:clamp(2.6rem,6vw,4.4rem);line-height:1.08;font-weight:400;letter-spacing:-.035em;max-width:15ch;margin-block:22px}h2{font-size:1.5rem;line-height:1.3;margin-block-end:20px;letter-spacing:-.02em}h3{font-size:1.12rem;line-height:1.4;margin-block-end:10px;text-wrap:balance}.lede{font-size:1.12rem;max-width:68ch;color:var(--muted);text-wrap:pretty}.eyebrow{display:flex;justify-content:space-between;gap:16px;font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;font-weight:650}.eyebrow span{letter-spacing:0;text-transform:none;border:1px solid #becfc2;border-radius:99px;padding:2px 12px;color:var(--accent);white-space:nowrap}.preview{margin-block-start:24px;padding:12px 16px;border-radius:8px;background:#fff0c8;color:#574113;font-size:.9rem}.scope{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 36px;padding-block:28px;margin-block:32px 0;border-block:1px solid var(--line)}dt{font-size:.8rem;color:var(--muted)}dd{margin:2px 0 0;overflow-wrap:anywhere}.scope div:last-child{grid-column:1/-1}.stats{display:flex;gap:56px;margin-block:28px 48px}.stats div{display:flex;flex-direction:column}.stats strong{font-size:2.3rem;line-height:1.2;font-variant-numeric:tabular-nums;font-weight:500}.stats span{font-size:.86rem;color:var(--muted);margin-block-start:4px}section{margin-block:48px}.findings{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:28px}.findings p{font-size:.95rem;max-width:65ch}.refs{margin-block-start:12px;color:var(--muted);font-size:.8rem!important}.refs a{display:inline-block;margin-inline-end:8px}.chip{display:inline-flex;gap:10px;align-items:center;background:#e8eee7;color:#304b3a;border-radius:5px;padding:3px 9px;font-size:.78rem;overflow-wrap:anywhere}.chip b{font-variant-numeric:tabular-nums}.topic-counts,.tags{display:flex;flex-wrap:wrap;gap:8px}.topic-counts{margin-block:24px 8px}.muted{color:var(--muted);font-size:.85rem}.section-head{display:flex;align-items:start;justify-content:space-between;gap:20px;margin-block-end:22px}.section-head h2{margin-block-end:8px}form{display:flex;flex-wrap:wrap;gap:12px;align-items:end;background:#eaf0e9;padding:18px;border-radius:10px;margin-block:24px 14px}.field{flex:1 1 140px;min-width:0}.field.search{flex:2 1 230px}label{display:block;font-size:.8rem;font-weight:600;margin-block-end:6px}input,select,button{font:inherit;font-size:1rem;min-height:44px;border-radius:6px;border:1px solid #aebdb1;background:#fff;color:var(--ink)}input,select{width:100%;padding:9px 11px}button{padding:9px 15px;cursor:pointer;white-space:nowrap}button:hover{background:#f0f5ef}:focus-visible{outline:3px solid #155cc7;outline-offset:3px}#status{font-size:.85rem;color:var(--muted);margin-block:12px 18px;font-variant-numeric:tabular-nums}.post{display:grid;grid-template-columns:44px minmax(0,1fr);gap:18px;padding:28px 0;border-block-start:1px solid var(--line);scroll-margin-block-start:24px}.rank{font-family:Georgia,serif;font-size:1.6rem;font-variant-numeric:tabular-nums;color:#66766b;padding-block-start:3px}.post-meta{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--muted);font-size:.8rem;margin-block-end:10px}.summary{max-width:70ch}.tags{margin-block-start:14px}.metrics{display:flex;flex-wrap:wrap;gap:20px 36px;margin-block:18px}.metrics dd{font-variant-numeric:tabular-nums;font-size:.95rem}.metrics dt{font-size:.75rem}summary{cursor:pointer;font-size:.85rem;color:var(--accent);padding-block:9px;min-height:40px}.details-body{padding:12px 0;color:var(--muted);font-size:.88rem;max-width:70ch}.details-body p{margin-block:8px}blockquote{white-space:pre-wrap;border-inline-start:3px solid #b9cabb;margin:4px 0 16px;padding-inline-start:18px}.source{display:inline-block;font-size:.85rem;padding-block:8px}.empty{background:#fff;padding:24px;border-radius:8px}footer{margin-block-start:48px;border-block-start:1px solid var(--line);padding-block-start:30px;font-size:.9rem}footer ul{padding-inline-start:22px;max-width:75ch}.cost{display:flex;flex-wrap:wrap;gap:30px;margin-block:24px}.cost dd{font-variant-numeric:tabular-nums}.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap;border:0}[hidden]{display:none!important}@media(max-width:38rem){.page{padding:30px 18px 50px}.scope{grid-template-columns:1fr;gap:16px}.stats{gap:30px;margin-block-end:36px}.section-head{flex-wrap:wrap}.post{grid-template-columns:28px minmax(0,1fr);gap:12px}.rank{font-size:1.25rem}.metrics{gap:14px 24px}h1{max-width:16ch}form{padding:14px}.field.search{flex-basis:100%}}
@media print{body{background:#fff}.page{max-width:none;padding:0;font-size:10pt}h1{font-size:30pt;max-width:none}.skip,form,#print,#empty,details>summary{display:none!important}.post{break-inside:avoid}.source{font-size:9pt}.findings{display:block}.findings article{margin-block-end:16px}section{margin-block:24px}.preview{border:1px solid #bbb;background:#fff}.scope{gap:8px 20px}}
@media(forced-colors:active){:focus-visible{outline:3px solid Highlight}.chip,.preview{border:1px solid CanvasText}}
"""

JS = """'use strict';
const form=document.getElementById('filters'), list=document.getElementById('posts');
const cards=Array.from(list.querySelectorAll('.post'));
const search=document.getElementById('search'), topic=document.getElementById('topic'), collection=document.getElementById('collection'), sort=document.getElementById('sort');
const status=document.getElementById('status'), empty=document.getElementById('empty');
const items=cards.map(el=>({el,id:el.dataset.id,created:el.dataset.created===''?null:Number(el.dataset.created),metrics:JSON.parse(el.dataset.metrics),topics:JSON.parse(el.dataset.topics),collections:JSON.parse(el.dataset.collections),text:el.dataset.search.toLocaleLowerCase()}));
function value(item){return sort.value==='latest'?item.created:item.metrics[sort.value];}
function update(){
  const q=search.value.trim().toLocaleLowerCase();
  const sorted=items.slice().sort((a,b)=>{const av=value(a),bv=value(b);if(av===null&&bv!==null)return 1;if(av!==null&&bv===null)return -1;if(av!==bv)return (bv||0)-(av||0);if(a.created!==b.created)return (b.created||0)-(a.created||0);return a.id<b.id?-1:a.id>b.id?1:0;});
  let visible=0,rank=0;
  sorted.forEach(item=>{const show=(!q||item.text.includes(q))&&(!topic.value||item.topics.includes(topic.value))&&(!collection.value||item.collections.includes(collection.value));item.el.hidden=!show;list.append(item.el);if(show){visible++;const known=value(item)!==null;if(known)rank++;item.el.querySelector('.rank-value').textContent=known?String(rank).padStart(2,'0'):'—';}});
  status.textContent=status.dataset.template.replace('{visible}',String(visible)).replace('{total}',String(items.length));empty.hidden=visible!==0;
}
form.addEventListener('submit',event=>event.preventDefault());
search.addEventListener('input',update);[topic,collection,sort].forEach(control=>control.addEventListener('change',update));
document.getElementById('clear').addEventListener('click',()=>{search.value='';topic.value='';collection.value='';update();});
const print=document.getElementById('print');print.hidden=false;print.addEventListener('click',()=>window.print());
let openedForPrint=[];
window.addEventListener('beforeprint',()=>{openedForPrint=Array.from(list.querySelectorAll('.post:not([hidden]) details:not([open])'));openedForPrint.forEach(el=>{el.open=true;});});
window.addEventListener('afterprint',()=>{openedForPrint.forEach(el=>{el.open=false;});openedForPrint=[];});
form.hidden=false;update();
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--format", choices=("markdown", "html", "both"), default="both")
    parser.add_argument("--basename", default="report")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.basename):
        parser.error("basename must use letters, numbers, underscores, or hyphens.")
    try:
        report = Report(json.loads(args.input.read_text(encoding="utf-8")))
        outputs = {}
        if args.format in ("markdown", "both"):
            outputs["md"] = report.markdown()
        if args.format in ("html", "both"):
            outputs["html"] = report.html()
        args.output.mkdir(parents=True, exist_ok=True)
        for extension, body in outputs.items():
            target = args.output / f"{args.basename}.{extension}"
            target.write_text(body, encoding="utf-8")
            print(target.resolve())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f"Unable to render report: {exc}\n")


if __name__ == "__main__":
    main()
