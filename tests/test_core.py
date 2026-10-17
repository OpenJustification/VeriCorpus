# SPDX-License-Identifier: AGPL-3.0-or-later
from vericorpus.util import normalize_text, similarity, contains_high_risk, repair_fraction
from vericorpus.models import Candidate
from vericorpus.evidence import detect_disagreements, extraction_consensus


def test_normalize():
    assert normalize_text("hello   world") == "hello world"


def test_similarity():
    assert similarity("The dose was 10 mg.", "The dose was 10 mg.") > 0.99


def test_high_risk():
    assert contains_high_risk("10")
    assert contains_high_risk("The concentration was 0.05 mg/mL.")
    assert contains_high_risk("p < 0.05")
    assert not contains_high_risk("The cells were washed twice.")


def test_repair_fraction():
    assert repair_fraction("abc", "abc") == 0.0


def test_two_extractors_outvote_one():
    cs=[
        Candidate(engine='pymupdf_native',text='The dose was 10 mg',confidence=.99),
        Candidate(engine='tesseract',text='The dose was 10 mg',confidence=.95),
        Candidate(engine='docling',text='The dose was 70 mg',confidence=.96),
    ]
    _,ds=detect_disagreements(cs,1)
    assert len(ds)==1
    assert ds[0].high_risk
    consensus=extraction_consensus(ds[0],cs)
    assert consensus is not None
    assert consensus[0]=='10'
    assert set(consensus[1])=={'pymupdf_native','tesseract'}
