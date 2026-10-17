# Legal and model policy

The goal of this policy is to reduce avoidable licensing ambiguity in the official VeriCorpus distribution. It is not legal advice.

## Official reference rule

A model/tool can enter the official reference registry only when:

- its code/model license is clearly identified by the upstream project;
- the license is compatible with distribution/use in an AGPL project architecture;
- VeriCorpus does not need to redistribute weights under ambiguous terms;
- local inference is possible;
- the exact version/revision can be pinned;
- any remote-code requirement is documented and can be avoided or explicitly controlled.

The current registry accepts Apache-2.0, MIT, and AGPL-compatible components. Custom/research-only/noncommercial licenses are excluded from the official reference extras.

## No bundled model weights

VeriCorpus ships adapters/metadata, not third-party model weights. Users acquire models from their upstream source and remain bound by the upstream model license.

## No proprietary API in the reference profile

The official profile does not require proprietary hosted APIs. Third parties may publish plugins for them under their own terms.

## Input-content rights

Open-source software does not make arbitrary source documents lawful training data. Users must independently address copyright, privacy, consent, confidentiality, contractual restrictions, and applicable regulation.
