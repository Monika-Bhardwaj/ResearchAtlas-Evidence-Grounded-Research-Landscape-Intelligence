# 49. RESEARCH CONTRACT — v0.1 (MAINTAINED, VERSIONED, FROZEN AT MILESTONE 1 APPROVAL)

Before implementing anything beyond schemas, create and maintain:

```
docs/research_contract.md
```

This file is the single source of truth linking every design choice to a testable claim.
If a component cannot be traced to a row in the contract, it is scope creep:
remove it, or amend the contract through an ADR.

The contract follows this chain, and each stage must reference the next:

```
Question
   ↓
Hypothesis
   ↓
Representation
   ↓
Reasoning tasks
   ↓
Primary metric
   ↓
Baselines
   ↓
Ablations
   ↓
Failure taxonomy
```

---

## 49.1 Question

> Given a fixed, frozen corpus and a previously unseen research proposal, does a
> manually designed typed, provenance-backed graph support better research-positioning
> decisions than flat retrieval or citation-only structure?

---

## 49.2 Hypotheses

**H1 (primary, accuracy; the ONLY confirmatory hypothesis):**
A typed, provenance-backed research-decision graph yields more accurate facet-level
positioning (T2) of unseen research proposals than flat retrieval or citation-only
baselines within a fixed corpus.

**H1b (secondary, reported separately, NOT part of the H1 verdict):**
The graph system's end-to-end outputs are more actionable (Section 35 rubric, 1–5),
scored on full CLI output from the raw proposal.

**H2 (structure matters; mechanism analysis):** a causal decomposition on facet
macro-F1, with identical gold facets for all systems:

* H2-graph: L1 > E (does even an untyped graph add value beyond flat concept tagging?)
* H2-typing: L2 > L1 (do typed relations / multi-hop add value beyond an untyped graph?)
* H2-total: L2 > E

H2 is CONSISTENT only if H2-typing AND H2-total have CIs favouring L2. H2-graph is
reported as attribution of where the gain arises.
Caveat: E → L1 bundles concept nodes, citation structure and traversal. Claim
"untyped graph structure", not any single factor within it.

**H3 (calibration; mechanism analysis):**
(i) facet accuracy is monotone non-decreasing as the evidence level rises from LOW to
MEDIUM to HIGH (INSUFFICIENT facets are abstained and excluded from this ordering);
(ii) AURC of the full system is LOWER than AURC of the best baseline's score-margin
confidence; (iii) AURC of L3 is LOWER than or equal to AURC of L2.
AURC is the area under the risk–coverage curve (49.5c), so LOWER IS BETTER. Selective
risk at a coverage level is the 0/1 error rate (label differs from gold) among the
retained facets. Facets are ranked by a continuous confidence score; ties are broken by
facet_id.

**H0:** No difference from, or worse than, the strongest baseline.

**Term definitions (H1):**

* "accurate" = agreement with frozen human gold positioning labels (T2)
* "unseen" = passes the leakage audit (Section 38)
* "flat retrieval" = Baselines A, B, D; "citation-only" = Baseline C
* "actionable" appears only in H1b

### Decision rule (pre-registered)

H1 is SUPPORTED iff BOTH hold:

1. Paired bootstrap over PROPOSALS (not facets): the 95% CI lower bound for
   Δ macro-F1 (full system − strongest baseline on test) is > 0.
2. nDCG@5 on T1 is non-inferior to the strongest baseline within a pre-declared
   tolerance δ.

Otherwise report DIRECTIONAL or NOT SUPPORTED. Comparing against the strongest baseline
on test is conservative toward H0. With 20–30 proposals, CIs will be wide: always
report per-proposal win/tie/loss counts and never overstate.

### Confirmatory vs mechanism analyses

* H1 is the only confirmatory hypothesis. Its verdict requires BOTH conditions above.
  Because it is an intersection of conditions, no multiplicity adjustment is applied.
* H1b, H2 and H3 are pre-registered mechanism/secondary analyses. Their CIs are reported
  as mechanism evidence. They are NOT additional confirmatory tests and carry no
  family-wise error control. The three H2 comparisons must not be read as three
  independent claims. H2 and H3 are always reported, regardless of the H1 outcome.
* Verdict vocabulary: H1 uses SUPPORTED / DIRECTIONAL / NOT SUPPORTED.
  H1b, H2, H3 use CONSISTENT / NOT CONSISTENT / INCONCLUSIVE.
* Actionability (H1b) is reported next to the H1 verdict, never folded into it.

### Attribution boundary

> H1 evaluates the full system as a provenance-backed system. The ablation ladder does
> NOT attribute positioning-accuracy gains specifically to provenance. L3 tests
> provenance/confidence primarily through H3 (evidence sufficiency, calibration,
> abstention) and through auditability, not through macro-F1.

---

## 49.3 Representation

State exactly which structures the reasoning consumes:

* typed entities and typed relations (ontology vX)
* per-edge provenance and confidence
* Limitation → ResearchDirection chains
* Claim SUPPORTS / CHALLENGES structure
* PREREQUISITE_FOR edges

**Necessity table (mandatory):** for every reasoning output (score feature, reading-path
step, tension, positioning label), name the graph structure it consumes.
If an output could be computed from a flat document store, tag it `FLAT_COMPUTABLE`
and do not count it as evidence for H1/H2.

---

## 49.4 Reasoning tasks

* **T0: facet grounding/decomposition (auxiliary, secondary result).**
  Input: raw proposal. Output: facets with grounded concepts. NEVER combined with T2.
* **T1: prior-work ranking.** Input: the full proposal text (end-to-end, includes
  grounding). Serves as the non-inferiority guard.
* **T2: facet-level positioning (PRIMARY).** Input: a frozen gold facet tuple
  `(proposal_id, facet_id, facet_text)`. Output: one of WELL_EXPLORED /
  PARTIALLY_EXPLORED / UNDERREPRESENTED / UNKNOWN, plus evidence.
* **T3: prerequisite-aware reading path.** Input: gold facet tuple.
* **T4: tension surfacing.** Input: gold facet tuple. Tension status (CONFLICTING / INSUFFICIENT_EVIDENCE) is an output and evaluation label derived at query time from SUPPORTS and CHALLENGES edges on a Claim. It is not an ontology relation and is never stored in the knowledge state.
* **T5: abstention.** Input: gold facet tuple. Output: ABSTAIN decision + confidence.

T2 evaluates positioning CONDITIONAL on a correctly specified facet. It isolates
knowledge representation and reasoning from proposal decomposition.

### Two evaluation tracks over the same proposals (independent, not a pipeline)

| Track | Tasks | Input | Purpose |
|---|---|---|---|
| End-to-end | T0, T1, H1b actionability | raw proposal | realism: grounding, retrieval, researcher-facing output |
| Controlled | T2, T3, T4, T5 | frozen gold facets | isolate representation/reasoning (ablation-ready) |

Gold facets are human-authored and never derived from T0 or T1 outputs.

### No hidden evaluation pipeline

T3–T5 do not consume outputs from T0 or T2. They are parallel controlled-track
evaluations conditioned directly on the same frozen gold facet tuples and their
permitted evidence inputs (the frozen knowledge state K, or a baseline's own corpus
index). T0/T1/T2 outputs must not become hidden intermediate state for these
evaluations. Shared code modules (grounding, traversal) are permitted; shared per-run
outputs are not.

T5 is scored by the harness by joining its ABSTAIN decision/confidence with the
correctness of the T2 label for the same facet. This is scoring, not input: the abstain
decision is computed in the same per-facet pass from the gold facet tuple and K, never
from a previously produced T2 output.

The actionability rubric (H1b, the 8 questions of Section 35) is scored on the full
end-to-end CLI output from the raw proposal, which is where realism is tested.

---

## 49.4b Evaluation map

| Question | Task / metric |
|---|---|
| Can the system identify the important research facets? | T0: facet P/R, concept grounding, ambiguity handling |
| Given the same facet, can it position the research correctly? | T2: facet macro-F1 (PRIMARY) |
| Can it retrieve relevant prior work? | T1: nDCG@5 (guard), P@5, R@5, MRR |
| Can it construct a useful reading path? | T3: rubric (Section 34) |
| Can it surface tensions? | T4 (metric fixed at Milestone 1, see 49.12) |
| Can it safely abstain? | T5: risk–coverage, abstention recall |

**T1 and T2 answer different questions and must not be conflated.** T1 measures
end-to-end prior-work retrieval from an unseen proposal; T2 measures facet-level
positioning conditional on a frozen gold facet. A system may therefore improve T2
without improving T1, or vice versa. The T1 non-inferiority guard prevents the proposed
representation from sacrificing basic retrieval quality while the primary H1 test
remains T2.

### T0 definition (pre-registered)

* Each gold facet carries a gold concept set. A predicted facet MATCHES a gold facet if
  the Jaccard similarity of their grounded concept sets is >= tau_T0 (fixed on dev),
  assigned one-to-one, greedily by descending Jaccard.
* Facet precision = matched / predicted. Facet recall = matched / gold.
* Unsupported-facet rate = unmatched predicted / predicted.
  Missing-facet rate = 1 − recall.
* Concept grounding: precision/recall of matched concepts against gold concept sets.
* Ambiguity handling: fraction of gold-ambiguous terms returned as AMBIGUOUS
  (not force-resolved). Unknown handling: fraction of gold-unknown terms returned
  as unknown (not mapped into the ontology).
* T0 applies to the system's grounding module only. Baselines A–D have no decomposition
  stage. A trivial clause/sentence-splitting decomposer may be reported as a reference floor.

**T0 limitation (record in approach.md):** T0 measures agreement at the level of the
predefined concept vocabulary, not semantic equivalence of arbitrary free-text facets.
A legitimate alternative decomposition that grounds to different concepts will score as
unmatched; a predicted facet that grounds to an empty concept set can never match.

---

## 49.5 Primary metric

Exactly ONE primary metric:

> **Facet-level positioning macro-F1** over the four classes
> WELL_EXPLORED / PARTIALLY_EXPLORED / UNDERREPRESENTED / UNKNOWN.

Computation:

* Unit of analysis: the facet. Classes: the four labels.
* **Proposal-size weighting:** each facet is weighted 1 / n_p (n_p = gold facets in
  proposal p). Build a weighted confusion matrix, compute per-class F1 from weighted
  counts, then macro-average over classes.
* **Test-set construction rule:** 3–5 gold facets per proposal, and a minimum gold
  support per class fixed at M1 approval: ≥ 8. Classes with zero gold support are
  excluded from the average, and the exclusion is reported.
* **All facets are scored.** Abstained facets are never dropped (see 49.5c).
* **CI:** paired bootstrap, 10,000 resamples, fixed seed, resampling proposals
  (facets within a proposal are correlated).
* **Facet input:** every system receives the identical frozen gold facet tuples for T2.
  No system may modify, merge, split, add, remove, or reinterpret the gold facet set.

Guard: nDCG@5 on T1 (full-proposal input), non-inferiority with tolerance δ.

Secondary (reported, not optimized): P@5, R@5, MRR, reading-path rubric, actionability
checklist, abstention metrics, T0 metrics, knowledge-construction precision/recall/F1.

---

## 49.5b Ranking→positioning adapter and fairness rules

The adapter maps a baseline's ranked output to a facet label.

1. Identical functional form, tuning procedure and tuning budget for every baseline.
   Parameters are fitted per baseline on dev, because score scales differ across
   BM25, cosine similarity, and citation scores.
2. Tuned ONLY on the dev set.
3. Uses ONLY that baseline's own output (ranks, scores, margins, counts above a
   threshold). No gold labels. No ontology information for A–D. Baseline E may use
   its own tag-overlap counts, because tags are part of its output.
4. Deliberately tiny: ordinal thresholds with 2–3 parameters, grid-searched on dev
   (no learned classifier; dev has too few facets).
5. The adapter code hash and fitted parameters are frozen, documented, and committed
   (git tag) BEFORE the first test run.
6. The graph system's own label thresholds are tuned under the same dev budget.
7. **Sensitivity row:** also report test macro-F1 for each baseline under a
   test-oracle-tuned adapter, labelled "non-deployable upper bound". If the graph
   system still beats that, the result is robust to adapter choice.
8. **Shared facet identity.** Every system is evaluated against the identical
   `(proposal_id, facet_id, facet_text)` tuples. Systems may use the facet text to
   retrieve/score evidence, but may not create additional facets or remove existing
   ones for T2.
9. **Exact input.** The T2 input is exactly that tuple: no extra proposal context for
   any system. Gold facet text must therefore be self-contained, written in natural
   researcher language (not ontology-canonical terms), and label-neutral (no wording
   that hints at the gold positioning label). Facet text is authored BEFORE the rule
   registry is frozen and is covered by the leakage audit (Section 38).
10. **Harness enforcement.** The evaluation harness asserts that each system's T2 output
    facet_id set equals the gold facet_id set per proposal. Any mismatch invalidates the
    run (fail fast). It is never silently repaired.
11. **Label-logic parity within the H2 comparison.** For E, L0, L1, L2 the label rule has
    the same functional form (thresholded ordinal over evidence features). Rungs differ
    only in which evidence features their representation can supply. Otherwise
    representation is confounded with label logic.

---

## 49.5c Abstention treatment (pre-registered)

* `UNKNOWN` is a positioning CLASS: "the corpus has insufficient evidence about this
  facet." It can be gold-labelled and counts in macro-F1.
* `ABSTAIN` is an orthogonal SYSTEM DECISION: "I do not stand behind my label for
  this facet." Default rule: ABSTAIN iff evidence_sufficiency = INSUFFICIENT.
  Sweeping the threshold across levels produces the risk–coverage curve.
* Every system always emits a label from the four classes, even when it abstains
  (forced label), so abstention cannot improve macro-F1 by dropping hard facets.
* Reported separately: coverage, selective accuracy, risk–coverage curve / AURC,
  and accuracy by confidence level. Baselines obtain a confidence from their adapter
  (e.g. score margin) so H3 comparisons are possible.
* The test set includes a small block of deliberately out-of-scope proposals
  (expected UNKNOWN + ABSTAIN). Report abstention recall on them.

---

## 49.6 Baselines

* A: BM25
* B: embedding similarity
* C: citation-graph retrieval
* D: abstract RAG
* **E: flat store + the same controlled-vocabulary tags**, with no typed edges and no
  traversal. This isolates H2: whether typed structure adds value beyond concept tagging.

Fairness rules: same corpus, same frozen proposals/facets, same tokenization and
preprocessing, equal tuning effort on the dev set, and no baseline gets less
engineering care. See 49.5b.

---

## 49.7 Ablation ladder

```
A  BM25
B  Embedding
C  Citation graph
D  Abstract RAG
E  Flat store + controlled vocabulary
│
├── L0 Citation graph
├── L1 + concept nodes
├── L2 + typed relations / multi-hop
├── L3 + provenance/confidence
├── L4 + limitations/directions/tensions
└── L5 + prerequisite-aware reading path
```

| Variant | Adds | Expected effect on primary macro-F1 | Evaluated on | Falsified if |
|---|---|---|---|---|
| L0 | citation graph only | parity with Baseline C (sanity check) | T2 | diverges from C without explanation |
| L1 | + untyped concept nodes | increase (H2-graph) | T2 | no gain over E |
| L2 | + typed relations / multi-hop | increase (H2-typing) | T2 | no gain over L1 |
| L3 | + provenance-weighted confidence | NONE by design (confidence/abstention only; does not feed label logic) | T5, H3 | calibration unchanged |
| L4 | + limitation/direction chains + tension analysis | increase on PARTIALLY_EXPLORED / UNDERREPRESENTED facets | T2 (those classes), T4 | no change on those facets |
| L5 | + prerequisite-aware reading path | NONE by design (changes T3, not T2) | T3 rubric | no gain over L4 |

A rung expected to be a no-op for macro-F1 must be evaluated on its own metric, not
dropped. Report every rung, including rungs that do not help.

---

## 49.8 Failure taxonomy

Every miss on the evaluation set must be tagged with ONE primary code (optional
secondary) BEFORE any fix is considered:

* F1 grounding: missed concept / false concept / ambiguity resolved wrongly
* F2 knowledge construction: false edge / missing edge / wrong provenance
* F3 corpus coverage gap (relevant paper not in the corpus; not a system fault)
* F4 traversal or scoring error (right graph, wrong rank; weight sensitivity)
* F5 positioning miscalibration (overconfident or over-abstaining)
* F6 reading-path defect (prerequisite inversion, redundancy, missing foundation)
* F7 tension error (spurious conflict / missed conflict)
* F8 evidence-sufficiency miscalibration
* F9 gold-label OR gold-facet-text error (ambiguous, non-self-contained, or
  label-leaking facet text)
* F10 leakage / contamination
* F11 infrastructure failure (API, cache, schema)

Report the failure distribution in approach.md. Do NOT tune the system on frozen
proposals. Failures found there become documented limitations, or are fixed only
using NEW dev-set examples.

---

## 49.9 Data splits and anti-peeking

* **Dev set (8–10 proposals, with gold facets):** used for scoring weights, adapter
  thresholds, tau_T0, rule debugging.
* **Frozen test set (20–30 proposals):** touched only for released versions.
* Gold labels and gold facet text are written BEFORE the rule registry is frozen and
  WITHOUT viewing system output.
* Every run on the frozen set is logged (git SHA + config hash) so repeated peeking
  is visible.
* Raters see anonymized, order-randomized outputs where feasible. The single-rater
  limitation must be stated explicitly.

---

## 49.10 Freeze points and amendments

* Contract v0.1 is delivered with Milestone 1 and frozen when Milestone 1 is approved.
  Frozen items: hypotheses, primary metric, decision rule, baselines, task definitions,
  fairness rules.
* Parameters listed in 49.12 are fixed at Milestone 1 approval. Before the frozen test
  set is created (start of Milestone 5) they may be amended only by an ADR whose
  rationale is not informed by any test-set run. After the frozen test set is first run,
  nothing in the contract changes.
* Any later change requires an ADR and results are labelled POST_HOC.

---

## 49.11 Traceability matrix

Maintain a table: component → hypothesis served → task/metric → ablation rung → failure
codes. Any component without a row is flagged for removal. Initial rows (extend as
components are added):

| Component | Hypothesis | Task / metric | Rung | Failure codes |
|---|---|---|---|---|
| Proposal decomposition into facets | H1b | T0, T1 | end-to-end only | F1 |
| Facet-text grounding to ontology concepts (shared by E, L1+) | none individually (held constant across E, L1, L2) | T2 (on the path), T0 concept metrics | E, L1+ | F1 |
| Controlled-vocabulary tags (flat) | H2 | T2 | E | F1, F4 |
| Typed-relation traversal | H2-typing | T2 | L2 | F2, F4 |
| Provenance + confidence | H3 | T5 | L3 | F2, F8 |
| Limitation/direction chains, tensions | H1b (Section 35 items 4–6); L4 ladder analysis is exploratory, no named hypothesis | T4, T2 (UNDERREPRESENTED) | L4 | F7 |
| Prerequisite-aware reading path | H1b | T3 | L5 | F6 |
| Ranking→positioning adapter | fairness (H1) | T2 baselines | A–E | F4, F5 |
| Abstention logic | H3 | T5 | L3 | F5, F8 |

The hypothesis column names the hypothesis whose evidence a component's own evaluation
supplies. Every full-system component is also part of the H1 confirmatory comparison,
but H1 is attributed only to the system as a whole, never to an individual component or
mechanism rung.

---

## 49.12 Parameters

**Fixed at Milestone 1 approval:** tolerance δ for the nDCG@5 guard; gold facets per
proposal (3–5); minimum gold facets per class; bootstrap resamples and seed; coverage
levels for the risk–coverage analysis; ABSTAIN rule; T4 metric definition (proposed:
precision/recall of surfaced SUPPORTS/CHALLENGES tensions against gold-annotated
tensions per facet, plus correctness of INSUFFICIENT_EVIDENCE calls); T3 rubric
anchors (Section 34).

**Fixed on dev, frozen before first test run:** tau_T0, adapter parameters, label
thresholds.

No parameter in either list may change after the frozen test set is first run.


---

# Part 2. Milestone 1 instantiation

**Status: PROPOSED.** Nothing below is frozen until the human researcher approves Milestone 1. After approval the Section 49 text and the Part 2.1 parameters are frozen under 49.10: amendments require an ADR whose rationale uses no test-set run, and nothing changes after the frozen test set is first run.

## 2.1 Proposed 49.12 parameters

| Parameter | Proposed value | Rationale |
|---|---|---|
| nDCG@5 guard δ | **0.10 absolute** | Chosen for interpretability, not for what n can demonstrate (see 2.1a). |
| Guard bound | One-sided 95%: the 5th percentile of the paired bootstrap of Δ = system − strongest baseline must exceed −δ | Standard non-inferiority convention. H1's superiority condition keeps the two-sided 95% CI lower bound. |
| T1 population | In-scope test proposals only | Out-of-scope proposals have no relevant papers, so nDCG is undefined. |
| Set sizes | Test 24 (20 in-scope + 4 out-of-scope); dev 8 | Meets 20–30 and 8–10. |
| Gold facets per proposal | Target 4; 3–5 allowed; at least 1 combination facet for in-scope proposals | Combination facets are the natural source of UNDERREPRESENTED facets. Enforced by `validate_gold_set`, values in `config/default.yaml`. |
| Min gold facets per class (test) | Minimum **≥ 8 gold facets per class — fixed at M1 approval.** | UNKNOWN is covered by the out-of-scope block (about 16 facets). UNDERREPRESENTED depends on the corpus: inspect the Section 11 statistics at M2 before corpus submission and before annotation; treat any genuinely unforeseen problem through the ADR/amendment process rather than revising the corpus selection to accommodate annotation convenience. |
| Bootstrap | 10,000 resamples, seed 42, resampling proposals | Facets within a proposal are correlated. |
| Risk–coverage | Coverage grid 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, plus AURC. **Lower AURC is better.** | Selective risk = 0/1 label error among retained facets. Facets are ranked by a continuous confidence score; ties are broken by facet_id. |
| ABSTAIN rule | ABSTAIN iff `evidence_sufficiency == INSUFFICIENT` | Evidence-level thresholds are dev-tuned label parameters, not contract parameters. ABSTAIN is a system decision; UNKNOWN is a positioning class. |
| T1 relevance scale | Graded 0–3: 0 unrelated, 1 background, 2 closely related, 3 directly overlapping prior work. Gain = 2^rel − 1. Unlisted papers count as 0. | Gold lists are written before any system runs, so pooled annotation is not possible. Incompleteness bias is accepted and stated. |

### 2.1a Why δ = 0.10, and what the guard can and cannot show

δ is the loss a researcher would notice. With three grade-2 relevant papers, nDCG@5 falls by 0.033 when one relevant paper is demoted from rank 3 to 4, by 0.094 from rank 2 to 4, and by 0.235 when one drops out of the top five. So δ = 0.10 is about one relevant paper demoted two ranks.

Power is a separate question. Under true equivalence, the probability the guard passes (one-sided 95% bound) is:

| n (in-scope) | paired SD 0.15 | paired SD 0.20 | paired SD 0.30 |
|---|---|---|---|
| 20 | 0.91 | 0.72 | 0.44 |
| 28 | 0.97 | 0.84 | 0.55 |

(Normal approximation. Using the 2.5th percentile instead lowers these, for example 0.61 at SD 0.20, n = 20.) The paired SD is unknown. At M4, estimate it from dev baseline runs (n = 8 is noisy). If the pass probability under equivalence looks below about 0.7, add in-scope test proposals by ADR before the test set is locked rather than widening δ. Failing the guard caps H1 at DIRECTIONAL, as the decision rule already states.

## 2.2 T3 rubric anchors (1 / 3 / 5)

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| Prerequisite coherence | two or more order inversions | one inversion or one unexplained jump | every prerequisite precedes its dependent |
| Relevance | mostly tangential to the facet | about half directly relevant | all directly relevant or a declared prerequisite |
| Coverage | misses the core concept or method | covers the concept but not evaluation or recent work | foundational, core, evaluation and recent work all present |
| Usefulness | would not change my reading | would reorder or replace two or more papers | would adopt as is |
| Redundancy (5 = none) | three or more near-duplicates | one duplicate | every paper has a distinct role |

## 2.3 T4 definition

Tension status values CONFLICTING and INSUFFICIENT_EVIDENCE are **output and evaluation labels derived at query time. They are not ontology relations and are never stored.** For each Claim reachable from a facet within the bounded traversal:

- CONFLICTING iff the claim has at least one SUPPORTS and at least one CHALLENGES edge from distinct papers;
- INSUFFICIENT_EVIDENCE if only one side has edges, or fewer than two papers are involved;
- consistent support from two or more papers is not surfaced as a tension;
- a facet with no reachable claim gets a facet-level INSUFFICIENT_EVIDENCE marker.

Scoring is claim-level precision, recall and F1 on (facet_id, claim_id, status), with paper-set Jaccard as a secondary measure. `Tension` in `src/output/models.py` enforces the CONFLICTING invariant.

## 2.4 Representation necessity table (initial)

| Output | Graph structure consumed | `FLAT_COMPUTABLE`? |
|---|---|---|
| Concept overlap | concept tags (ADDRESSES, focal concepts only) | yes (Baseline E) |
| Method overlap | typed PROPOSES / USES | no |
| Graph proximity | multi-hop typed paths | no |
| Citation connectivity | CITES | yes (Baseline C) |
| Positioning label | typed coverage of facet concept combinations | partly |
| Reading path | PREREQUISITE_FOR chains | no |
| Tensions | SUPPORTS / CHALLENGES on Claims | no |
| Evidence sufficiency | edge provenance and confidence | no |

## 2.5 Reconciliation decisions recorded in this milestone

1. **20 relations.** Section 7 has 2 + 9 + 3 + 6 = 20 relation types. 18 are storable, CITED_BY is a derived inverse, MEASURES_WITH is deferred. A test asserts the key set equals Section 7 exactly.
2. **ADDRESSES** is defined precisely for both range types and never means "mentions" (ADR-0008).
3. **REPORTS_LIMITATION** is Method → Limitation, with mandatory source paper, evidence span and attribution, cross-checked against PROPOSES edges (ADR-0009).
4. **Inventory.** M1 provides an estimated inventory; a measured inventory comes at M3, with no quotas.
5. **δ** rationale revised (2.1a).
6. **AURC direction** fixed in H3: lower is better.
7. **Tension status** is an output label, not a relation (2.3).
8. **Section 21 signs** fixed in the master prompt (Patch 13) and covered by a config test (no negative weights, sum to 1).

## 2.6 M1 traceability: artifact to Section 49

| Artifact | What it does | Section 49 rows served |
|---|---|---|
| `src/ontology/ontology.yaml` | closed vocabulary, domain/range, source classes, estimates | 49.3 representation, 49.11 matrix |
| `src/ontology/loader.py` | fail-fast ontology validation, no silent repair | 49.10 freeze, 49.3 |
| `src/knowledge/models.py` | three-type provenance, evidence fields, per-edge confidence | 49.3, H3 auditability, F2 |
| `src/knowledge/validation.py` | domain/range, provenance-per-relation, REPORTS_LIMITATION semantics | 49.3, F2 |
| `src/knowledge/io.py` | canonical serialization, integrity hash, corrupt-state errors | 49.10, Sections 16 and 27 |
| `src/knowledge/curation.py` | human-authored vocabulary and curated-edge formats | Patch 11, 49.11 |
| `src/evaluation/gold.py` | gold schema, rule 8–10 checks, sealing | 49.5b rules 8–10, 49.9 |
| `src/output/models.py` | per-facet positioning, ABSTAIN vs UNKNOWN, tension label, no-novelty guard | 49.4, 49.5c, T0–T5 |
| `src/config.py` | scoring weights (Section 21) and gold parameters | 49.12, Patch 13 |
| `config/default.yaml` | all constants, PROPOSED values marked | 49.12 |
| `schemas/knowledge_state.schema.json` | independent inspectability | Section 16 |
| `docs/relation_source_inventory.md` | estimated inventory and curation workload | Patch 1 deliverable |
| `scripts/validate_knowledge_state.py` | validation command of the final demo | Section 54 |
| `scripts/seal_gold.py` | test-gold sealing | 49.9 |
| `data/evaluation/gold_test.template.yaml` | blank human-authored gold template | 49.9 |
