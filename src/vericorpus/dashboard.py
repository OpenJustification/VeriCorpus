# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline, self-contained review dashboard; never auto-promotes human edits.

The reviewer can export a local feedback bundle with traceable original text IDs.
No remote scripts, fonts, network requests or background uploads are involved.
"""
from __future__ import annotations

import json
from pathlib import Path


_PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; form-action 'none'">
<title>VeriCorpus • Offline review</title>
<style>
:root{color-scheme:light;--bg:#f3f5f9;--paper:#fff;--ink:#192338;--muted:#52627d;--line:#dae1ed;--a:#2359ba;--good:#137655;--bad:#a83e39;--warn:#a16d16}
*{box-sizing:border-box}body{font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;color:var(--ink);background:var(--bg)}
header{background:#101f3a;color:white;padding:21px 30px}header h1{margin:0;font-size:24px;letter-spacing:.2px}header p{margin:2px 0 0;color:#c9d5e8;font-size:13px}
nav{padding:16px 24px;background:white;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;flex-wrap:wrap;position:sticky;top:0;z-index:1}
input,select,textarea,button{font:inherit}input,select,textarea{padding:8px 10px;background:white;border:1px solid #bfc9da;border-radius:7px;color:var(--ink)}input[type=search]{min-width:230px;flex:1}button{cursor:pointer;padding:9px 14px;border-radius:7px;border:0;background:var(--a);color:white;font-weight:600}button.secondary{background:#e7edf8;color:#1e457f}
#metrics{margin:20px 24px;display:flex;gap:12px;flex-wrap:wrap}.metric{background:white;padding:13px 18px;border-radius:12px;border:1px solid var(--line);min-width:140px}.metric b{font-size:23px;display:block}
main{display:grid;grid-template-columns:minmax(270px,380px) minmax(0,1fr);gap:18px;margin:0 24px 36px}aside,.detail{background:white;border:1px solid var(--line);border-radius:12px;min-height:350px;overflow:hidden}aside{max-height:76vh;overflow:auto}.unit{width:100%;display:block;background:white;border:0;border-bottom:1px solid var(--line);border-radius:0;text-align:left;color:var(--ink);padding:13px 16px}.unit:hover,.unit.active{background:#eff5fe}.unit small{display:block;color:var(--muted);font-weight:400;margin-top:3px}.detail{padding:24px;overflow:auto}h2{margin:0 0 6px}h3{margin:18px 0 7px}.pill{border:1px solid var(--line);border-radius:999px;padding:3px 9px;font-size:12px;background:#f6f8fb;white-space:nowrap}.accepted{color:var(--good)}.partial{color:var(--warn)}.rejected,.reprocess{color:var(--bad)}.row{display:flex;gap:8px;flex-wrap:wrap;margin:11px 0}.muted{color:var(--muted)}.document{white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f8fc;border:1px solid var(--line);border-radius:8px;padding:15px;max-height:480px;overflow:auto;line-height:1.6}.feedback{padding:16px;background:#edf3fb;border-radius:10px;margin-top:22px}.feedback textarea{width:100%;height:155px;resize:vertical}.feedback label{display:block;margin:10px 0 5px;font-weight:600}.feedback input,.feedback select{max-width:100%;width:100%}details{margin-top:12px}details summary{cursor:pointer;font-weight:600}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:6px 8px;text-align:left;border-bottom:1px solid var(--line)}td{vertical-align:top}footer{padding:0 25px 25px;color:var(--muted);font-size:12px}@media(max-width:830px){main{grid-template-columns:1fr}aside{max-height:250px}header{padding:16px}#metrics{margin:14px}}
</style></head><body>
<header><h1>VeriCorpus <span style="font-weight:300">| Offline review</span></h1><p>Evidence-first extraction • Inspect every page • Export human feedback without changing training outputs</p></header>
<nav><input id="search" type="search" placeholder="Search filenames, pages and extracted text" aria-label="Search extracted records"><select id="filter" aria-label="Filter readiness"><option value="all">All statuses</option><option value="accepted">Accepted</option><option value="partial">Review queue</option><option value="rejected">Rejected</option><option value="reprocess">Reprocess</option></select><input id="reviewer" placeholder="Reviewer ID (optional)" aria-label="Reviewer ID"><button id="export">Export feedback.json</button></nav>
<div id="metrics" aria-label="Dataset statistics"></div><main><aside id="items" aria-label="Pages"></aside><section class="detail" id="detail"><p class="muted">Choose a source page to inspect.</p></section></main>
<footer>Local HTML report. No network access. Model-assisted outputs are never substituted for source evidence. Reviewer feedback is separate from the admitted training corpus.</footer>
<script type="application/json" id="dataset">__VERICORPUS_DATA__</script>
<script>
'use strict';
const D=JSON.parse(document.getElementById('dataset').textContent);
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const edits=new Map();let current=null;
function id(a){return a.document_id+':'+a.page_number}
function status(a){return (a.readiness||{}).status || a.decision || 'rejected'}
function metric(label,value){return `<div class="metric"><b>${esc(value)}</b>${esc(label)}</div>`}
function renderMetrics(){let st={};D.audits.forEach(x=>st[status(x)]=(st[status(x)]||0)+1); $('metrics').innerHTML=metric('Total units',D.audits.length)+metric('Accepted',st.accepted||0)+metric('Review queue',st.partial||0)+metric('Reprocess / reject',(st.reprocess||0)+(st.rejected||0))+metric('Structured objects',D.objects.length)}
function visible(){const q=$('search').value.toLowerCase().trim(),f=$('filter').value;return D.audits.filter(a=>(f==='all'||status(a)===f)&&(!q||(a.source_file+' '+a.page_number+' '+(a.selected_text||'')).toLowerCase().includes(q)))}
function renderItems(){const rows=visible();$('items').innerHTML=rows.length?rows.map(a=>`<button class="unit ${id(a)===current?'active':''}" data-id="${esc(id(a))}"><b>${esc(a.source_file)}</b><small>Unit ${esc(a.page_number)} • <span class="${esc(status(a))}">${esc(status(a))}</span> • score ${Number((a.quality||{}).overall||0).toFixed(3)}</small></button>`).join(''):'<p class="muted" style="padding:20px">No matching records.</p>';
 document.querySelectorAll('.unit').forEach(b=>b.addEventListener('click',()=>select(b.dataset.id)))}
function select(key){const a=D.audits.find(x=>id(x)===key);if(!a)return;current=key;renderItems();const q=a.quality||{},r=a.readiness||{},s=a.structure||{};const objects=(s.objects||[]).filter(o=>!(o.metadata||{}).suppressed);const f=edits.get(key)||{};
 $('detail').innerHTML=`<h2>${esc(a.source_file)}</h2><p class="muted">Page/section ${esc(a.page_number)} • source SHA-256 ${esc(a.document_id)}</p><div class="row"><span class="pill ${esc(status(a))}">${esc(status(a))}</span><span class="pill">Quality ${Number(q.overall||0).toFixed(3)} (heuristic)</span><span class="pill">${esc(s.layout_type||'unknown')} • ${esc(s.column_count||'?')} column(s)</span><span class="pill">${esc(r.verification_grade||'not scored')}</span></div>
 <p><b>Blocking issues:</b> ${esc((r.blocking_issues||[]).join(', ')||'None detected')}<br><b>Warnings:</b> ${esc((r.warnings||[]).join('; ')||'None')}<br><b>Routing:</b> ${esc(((a.routing||{}).requested_engines||[]).join(', '))}</p>
 <h3>Source-derived text</h3><div class="document" role="region" aria-label="Extracted page text">${esc(a.selected_text)}</div>
 <details><summary>Detected objects (${objects.length})</summary><div style="overflow:auto"><table><thead><tr><th>Order</th><th>Type</th><th>Confidence</th><th>Text preview</th></tr></thead><tbody>${objects.map(o=>`<tr><td>${esc(o.reading_order||'-')}</td><td>${esc(o.object_type)}</td><td>${Number(o.confidence||0).toFixed(2)}</td><td>${esc((o.text||'').slice(0,170))}</td></tr>`).join('')}</tbody></table></div></details>
 <details><summary>Evidence and disagreements (${(a.disagreements||[]).length})</summary><pre class="document">${esc(JSON.stringify({candidates:(a.candidates||[]).map(c=>({engine:c.engine,confidence:c.confidence})),disagreements:a.disagreements},null,2))}</pre></details>
 <div class="feedback"><h3>Suggest a correction or label</h3><p class="muted">Suggestions are exported to a separate local JSON file. They do not overwrite accepted text or bypass validation.</p><label for="kind">Feedback category</label><select id="kind"><option value="text_correction">Text correction</option><option value="reading_order">Reading order</option><option value="table">Table reconstruction</option><option value="equation">Equation</option><option value="figure">Figure / caption</option><option value="classification">Object classification</option><option value="reject">Reject this record</option><option value="looks_correct">Looks correct</option></select><label for="correction">Proposed corrected text or detailed annotation</label><textarea id="correction" placeholder="Suggest source-grounded changes; preserve exact numbers and symbols.">${esc(f.proposed_text||'')}</textarea><label for="reason">Evidence note</label><input id="reason" placeholder="Describe what the original source shows" value="${esc(f.evidence_note||'')}"><div class="row"><button id="save">Save suggestion</button><span class="muted" id="saved-status">${edits.has(key)?'Saved locally in this session':''}</span></div></div>`;
 $('kind').value=f.category||'text_correction';$('save').addEventListener('click',save);
}
function save(){if(!current)return;const a=D.audits.find(x=>id(x)===current);edits.set(current,{source_sha256:a.document_id,source_file:a.source_file,page_number:a.page_number,source_text_sha256:D.hashes[current]||null,category:$('kind').value,proposed_text:$('correction').value,evidence_note:$('reason').value});$('saved-status').textContent='Saved locally. Export feedback.json to retain.'}
function exportFeedback(){const data={schema:'vericorpus_feedback_v1',generator_version:D.version,reviewer_id:$('reviewer').value,feedback:Array.from(edits.values()),created_at:new Date().toISOString()};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='vericorpus_feedback.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000)}
$('search').addEventListener('input',renderItems);$('filter').addEventListener('change',renderItems);$('export').addEventListener('click',exportFeedback);renderMetrics();renderItems();if(D.audits.length)select(id(D.audits[0]));
</script></body></html>'''


def write_review_dashboard(path: Path, audits: list[dict], structured: list[dict], version: str) -> None:
    from .util import sha256_text
    payload = {
        "version": version,
        "audits": audits,
        "objects": structured,
        "hashes": {str(a["document_id"]) + ":" + str(a["page_number"]): sha256_text(a.get("selected_text", ""))
                   for a in audits},
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    path.write_text(_PAGE.replace("__VERICORPUS_DATA__", data), encoding="utf-8")
