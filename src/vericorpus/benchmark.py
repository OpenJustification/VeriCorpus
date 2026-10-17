# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path
from .util import normalize_text


def character_error_rate(reference: str, hypothesis: str) -> float:
    a=normalize_text(reference); b=normalize_text(hypothesis)
    # Levenshtein distance, memory-efficient.
    if len(a)<len(b): a,b=b,a
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):
            cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]/max(len(reference),1)


def evaluate_jsonl(predicted: Path, gold: Path) -> dict:
    def load(p):
        rows={}
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            r=json.loads(line); key=(r.get('document_id'),int(r.get('page_number',0)))
            rows[key]=r
        return rows
    pred=load(predicted); ref=load(gold)
    matched=0; cer=[]; missing=0
    for k,g in ref.items():
        if k not in pred: missing+=1; continue
        matched+=1; cer.append(character_error_rate(g.get('text',''),pred[k].get('text','')))
    return {
        'gold_records':len(ref),'predicted_records':len(pred),'matched':matched,'missing':missing,
        'mean_character_error_rate':sum(cer)/len(cer) if cer else None,
        'coverage':matched/max(len(ref),1),
    }
