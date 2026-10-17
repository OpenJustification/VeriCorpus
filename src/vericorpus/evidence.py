# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from .models import BBox, Candidate, Disagreement, LedgerEntry, AIJudgment
from .util import contains_high_risk, content_type, normalize_text, stable_id, union_bbox, similarity


def _tokens_with_boxes(candidate: Candidate):
    tokens=[]; boxes=[]
    if candidate.spans:
        for sp in candidate.spans:
            parts=re.findall(r"\S+", sp.text)
            for part in parts:
                tokens.append(part); boxes.append(sp.bbox)
    else:
        for part in re.findall(r"\S+", candidate.text):
            tokens.append(part); boxes.append(None)
    return tokens, boxes


def _norm_token(t: str) -> str:
    return re.sub(r"\W+", "", t, flags=re.UNICODE).lower()


def choose_anchor(candidates: list[Candidate]) -> Candidate:
    nonempty=[c for c in candidates if c.text.strip()]
    if not nonempty:
        return Candidate(engine="none",text="",confidence=0.0)
    # No permanent model reputation bonus: anchor selection is based on observed
    # extraction quality and information retained on this page. Future calibrated
    # profiles may supply benchmark-derived content-specific weights.
    return max(nonempty, key=lambda c: (c.confidence, len(c.text)))


def page_agreement(candidates: list[Candidate]) -> float:
    """Agreement across independent evidence families only.

    Multiple wrappers from the same parser/model family are not independent
    witnesses and must not inflate page confidence.
    """
    c=[x for x in candidates if x.text.strip()]
    if len(c)<2:
        return 0.0
    vals=[]
    for i in range(len(c)):
        for j in range(i+1,len(c)):
            if evidence_family(c[i].engine,candidates)==evidence_family(c[j].engine,candidates):
                continue
            vals.append(similarity(c[i].text,c[j].text))
    return sum(vals)/len(vals) if vals else 0.0


def detect_disagreements(candidates: list[Candidate], page_number: int, context_chars: int = 220) -> tuple[Candidate,list[Disagreement]]:
    anchor=choose_anchor(candidates)
    atoks, aboxes=_tokens_with_boxes(anchor)
    anorm=[_norm_token(x) for x in atoks]
    raw=[]
    equal_support={}  # engine -> {anchor_token_index: token}

    for other in candidates:
        if other.engine==anchor.engine or not other.text.strip():
            continue
        btoks,bboxes=_tokens_with_boxes(other)
        bnorm=[_norm_token(x) for x in btoks]
        sm=SequenceMatcher(None,anorm,bnorm,autojunk=False)
        equal_support[other.engine]={}
        for tag,i1,i2,j1,j2 in sm.get_opcodes():
            if tag=='equal':
                if (i2-i1)==(j2-j1):
                    for ai,bj in zip(range(i1,i2),range(j1,j2)):
                        equal_support[other.engine][ai]=btoks[bj]
                continue
            atext=' '.join(atoks[i1:i2]).strip()
            btext=' '.join(btoks[j1:j2]).strip()
            # Ignore whitespace/punctuation-only drift.
            if normalize_text(atext)==normalize_text(btext): continue
            bbox=union_bbox(aboxes[i1:i2] or bboxes[j1:j2])
            before=' '.join(atoks[max(0,i1-25):i1])[-context_chars:]
            after=' '.join(atoks[i2:i2+25])[:context_chars]
            alt={anchor.engine:atext,other.engine:btext}
            joined=' '.join([atext,btext])
            typ=content_type(joined)
            high=contains_high_risk(joined) or typ in {'equation','identifier','code'}
            sev=1.0-similarity(atext,btext)
            raw.append(Disagreement(
                disagreement_id=stable_id(str(page_number),anchor.engine,str(i1),str(i2),other.engine,atext,btext),
                page_number=page_number,
                anchor_engine=anchor.engine,
                anchor_start=i1,
                anchor_end=i2,
                bbox=bbox,
                left_context=before,
                right_context=after,
                alternatives=alt,
                content_type=typ,
                high_risk=high,
                severity=max(0,min(sev,1)),
            ))

    # Merge comparisons that refer to the same anchor token interval.
    grouped={}
    for d in raw:
        key=(d.anchor_start,d.anchor_end)
        if key not in grouped:
            grouped[key]=d
        else:
            g=grouped[key]
            g.alternatives.update(d.alternatives)
            g.bbox=union_bbox([g.bbox,d.bbox])
            alltxt=' '.join(g.alternatives.values())
            g.content_type=content_type(alltxt)
            g.high_risk=contains_high_risk(alltxt) or g.content_type in {'equation','identifier','code'}
            g.severity=max(g.severity,d.severity)
    # Add engines that matched the anchor across each disputed interval.
    for (i1,i2),g in grouped.items():
        for eng,mapping in equal_support.items():
            if eng in g.alternatives or i2<=i1:
                continue
            if all(i in mapping for i in range(i1,i2)):
                g.alternatives[eng]=' '.join(mapping[i] for i in range(i1,i2))
    return anchor, sorted(grouped.values(),key=lambda x:(x.anchor_start,x.anchor_end))


def evidence_family(engine: str, candidates: list[Candidate]) -> str:
    c = next((x for x in candidates if x.engine == engine), None)
    if c and c.metadata.get("evidence_family"):
        return str(c.metadata["evidence_family"])
    e = engine.lower()
    if e.startswith("pymupdf"): return "native_pdf"
    if e.startswith("tesseract"): return "classical_ocr"
    if e.startswith("paddle"): return "paddle_vlm"
    if e.startswith("glm"): return "glm_ocr"
    if e.startswith("olmocr"): return "olmocr"
    if e.startswith("docling"): return "docling"
    if e.startswith("plugin:"): return e
    return e


def extraction_consensus(d: Disagreement, candidates: list[Candidate]):
    """Return consensus only when agreeing alternatives span >=2 evidence families.

    This avoids treating two wrappers around the same model lineage as two independent witnesses.
    """
    groups=defaultdict(list)
    for engine,text in d.alternatives.items():
        key=normalize_text(text).lower()
        if key:
            groups[key].append((engine,text))
    if not groups:
        return None
    key,vals=max(groups.items(),key=lambda kv:len(kv[1]))
    families={evidence_family(eng,candidates) for eng,_ in vals}
    if len(vals)>=2 and len(families)>=2:
        text=Counter(v for _,v in vals).most_common(1)[0][0]
        confs=[]
        for eng,_ in vals:
            c=next((x for x in candidates if x.engine==eng),None)
            if c: confs.append(c.confidence)
        return text,[e for e,_ in vals],sum(confs)/len(confs) if confs else 0.8
    return None


def resolve_disagreement(document_id: str, source_file: str, d: Disagreement, candidates: list[Candidate], ai: list[AIJudgment], ai_threshold: float=0.97) -> LedgerEntry:
    consensus=extraction_consensus(d,candidates)
    if consensus:
        text,engines,conf=consensus
        return LedgerEntry(
            ledger_id=stable_id(document_id,d.disagreement_id,"extractor_consensus"), document_id=document_id,source_file=source_file,page_number=d.page_number,bbox=d.bbox,content_type=d.content_type,
            original_alternatives=d.alternatives,selected_text=text,evidence_engines=engines,ai_judgments=ai,decision="accepted",reason="cross_family_extractors_agree",confidence=conf,high_risk=d.high_risk,
        )

    supported=[j for j in ai if j.status=='supported' and j.confidence>=ai_threshold and j.text.strip()]
    # AI is an adjudicator, not an author: accepted AI text must match an extracted alternative.
    def matching_alternative(txt):
        matches=[]
        for eng,alt in d.alternatives.items():
            if similarity(txt,alt)>=0.97:
                matches.append((eng,alt))
        return matches

    if d.high_risk:
        # Require two independent AI judges agreeing + at least one extraction alternative.
        if len(supported)>=2 and similarity(supported[0].text,supported[1].text)>=0.98:
            matches=matching_alternative(supported[0].text)
            if matches:
                return LedgerEntry(
                    ledger_id=stable_id(document_id,d.disagreement_id,"two_ai_plus_extractor"),document_id=document_id,source_file=source_file,page_number=d.page_number,bbox=d.bbox,content_type=d.content_type,
                    original_alternatives=d.alternatives,selected_text=matches[0][1],evidence_engines=[matches[0][0]],ai_judgments=ai,decision="accepted",reason="two_visual_ai_judges_confirm_extracted_high_risk_span",confidence=min(supported[0].confidence,supported[1].confidence),high_risk=True,
                )
    else:
        # Low-risk prose can be settled by one high-confidence visual judge only if it selects an existing extraction.
        if supported:
            matches=matching_alternative(supported[0].text)
            if matches:
                return LedgerEntry(
                    ledger_id=stable_id(document_id,d.disagreement_id,"one_ai_plus_extractor"),document_id=document_id,source_file=source_file,page_number=d.page_number,bbox=d.bbox,content_type=d.content_type,
                    original_alternatives=d.alternatives,selected_text=matches[0][1],evidence_engines=[matches[0][0]],ai_judgments=ai,decision="accepted",reason="visual_ai_selects_existing_low_risk_extraction",confidence=supported[0].confidence,high_risk=False,
                )

    return LedgerEntry(
        ledger_id=stable_id(document_id,d.disagreement_id,"unresolved"),document_id=document_id,source_file=source_file,page_number=d.page_number,bbox=d.bbox,content_type=d.content_type,
        original_alternatives=d.alternatives,selected_text="",evidence_engines=[],ai_judgments=ai,decision="unresolved",reason="insufficient_independent_evidence",confidence=0.0,high_risk=d.high_risk,
    )


def reconstruct_anchor(anchor: Candidate, disagreements: list[Disagreement], ledger: list[LedgerEntry]) -> tuple[str,int,int]:
    toks,_=_tokens_with_boxes(anchor)
    by_id={x.ledger_id:x for x in ledger}
    # map disagreement_id through ledger ai judgments? Use parallel positional ordering.
    entry_by_dis={}
    for d,e in zip(disagreements,ledger): entry_by_dis[d.disagreement_id]=e
    pieces=[]; pos=0; unresolved=0; high_risk_unresolved=0
    for d in disagreements:
        if d.anchor_start < pos:
            continue
        pieces.extend(toks[pos:d.anchor_start])
        e=entry_by_dis[d.disagreement_id]
        if e.decision=='accepted':
            pieces.extend(re.findall(r"\S+",e.selected_text))
        else:
            pieces.append('[UNRESOLVED]')
            unresolved+=1
            if d.high_risk: high_risk_unresolved+=1
        pos=d.anchor_end
    pieces.extend(toks[pos:])
    return normalize_text(' '.join(pieces)), unresolved, high_risk_unresolved


def drop_unresolved_sentences(text: str) -> str:
    if '[UNRESOLVED]' not in text:
        return text
    units=re.split(r'(?<=[.!?])\s+|\n+',text)
    kept=[u.strip() for u in units if u.strip() and '[UNRESOLVED]' not in u]
    return normalize_text(' '.join(kept))
