---
id: CKG-C-0001
title: "Sample Claim"
type: claim
taxonomy: claim.example
status: active
review_state: reviewed
visibility: public
summary: "A short claim that depends on one sample method."
why_it_matters: "It demonstrates a human-readable CKG card."
sources:
  - SRC-0001
edges:
  - target: CKG-C-0002
    type: REQUIRES
    rationale: "The claim needs the sample method."
---

# Sample Claim

Longer human-readable notes can live here.
