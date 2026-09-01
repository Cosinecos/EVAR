# Reproducibility Notes

This document separates requirements fixed by the final EVAR paper from engineering choices that the paper leaves unspecified. The distinction is intentional: defaults are visible and configurable rather than silently presented as published hyperparameters.

## Final-paper requirements implemented directly

| Paper requirement | Implementation |
|---|---|
| Atomic source-grounded claims with provenance | `ATOM` returns exact narrative substrings and character offsets; contracts require `narrative[start:end] == quote`. |
| Observable metadata only | Each unit stores `entities`, `time`, and `polarity`; inferred motives and causal bridges are prohibited during ATOM. |
| Local consistency tags | Batched `TAG` returns `OK`, `Uncertain`, or `Conflict` and severity `0..3` for every unit. |
| Immutable evidence store \(\mathcal B\) | Frozen data classes, a locked serialization flag, and a SHA-256 fingerprint checked during refinement. |
| Complexity and budget | Equations 8 and 9 are implemented in `EVARPipeline._complexity_score` and `_assign_budget`. |
| Corrected Algorithm 1 | `Z0` is computed once before routing, reused at `t=0`, and recomputed only for `t>0`. |
| Direct hypotheses per gap | `HYP` consumes a gap and state directly. The obsolete Query operator is not used. |
| Hypothesis-conditioned challenges | `CHAL` always returns direct-support, counterevidence, and prerequisite checks. |
| Strict admission | Only `VER=Support` enters \(\mathcal H^+\); `Unknown` is quarantined and `Contradict` is discarded. |
| State boundary | ANS receives only \(\mathcal B\), admitted hypotheses, the goal, and fixed candidates. |
| Stop conditions | No blocking gap, sufficiency score at or above `tau_suf`, or budget exhaustion. |
| NarraCrime output | Complete non-negative candidate-ID probability map with unit mass within `1e-6`. |
| Paper decoding | Greedy decoding, temperature `0`, top-p `1.0`, maximum output length `512`; stochastic baselines opt into nonzero temperature. |
| Paper metrics | RVS, IR, ASR, EC, UCR, and CR; `CR <= UCR` is enforced by construction. |
| Semantic recall | `all-mpnet-base-v2`, cosine threshold `0.8`, descending greedy one-to-one matching, micro-averaging. |
| LLM judging | Separate fixed prompts for proposition extraction, atomic decomposition, and evidence-status labeling. |

## Explicit implementation choices

The final paper gives formulas but does not publish all scalar values or provider behavior. The default release chooses:

| Setting | Default | Reason |
|---|---:|---|
| `alpha_gap` | `1.0` | Keeps one unresolved gap as the base complexity unit. |
| `alpha_issue` | `0.5` | Makes local uncertainty contribute without dominating gaps. |
| `alpha_sev` | `0.25` | Converts the `0..3` severity scale into a smaller additive term. |
| `tau_fast` | `1.0` | Allows very low-complexity cases to take the fast route. |
| `tau_step` | `1.0` | Adds roughly one refinement iteration per complexity unit above the fast threshold. |
| `tau_suf` | `0.82` | Conservative state-sufficiency threshold. |
| `B_max` | `4` | Matches the largest cap in the paper's budget sweep. |
| gaps per iteration | `4` | Bounds operator fan-out for malformed or over-generating backbones. |
| hypotheses per gap | `3` | Keeps candidate validation auditable and bounded. |
| JSON repair attempts | `2` | Handles formatting errors while failing closed after repeated invalid output. |
| TAG invocation | one batch per case | The paper defines a tag per unit but not API batching; batching keeps call accounting and context consistent. |

All values live in `configs/*.yaml`. Changing them changes the operating point and should be logged with results.

## Gold-data isolation

Inference receives:

- narrative text;
- a generic task goal that does not name the answer;
- the fixed suspect names, roles, and generated candidate IDs.

It does not receive `culprit`, `verdict`, `intent`, `action_schema`, `evidence_cues`, `Answer.txt`, or accomplice labels. Gold annotations are loaded only by the evaluator after inference. The offline mock follows the same restriction.

## Evaluation modes

`configs/deepseek_v3_2.yaml` is the paper-style path:

- DeepSeek-V3.2-compatible inference endpoint;
- MPNet semantic matching with `delta=0.8`;
- a separate GPT-5.5-compatible judge endpoint;
- strict structured outputs and raw traces.

`configs/mock.yaml` is an offline integrity path:

- rule-based model backend;
- lexical matching;
- deterministic textual-answer judge.

Mock scores are not estimates of model quality and must not be compared with paper results.

## Dataset construction summary

The released cases are consumed directly and never regenerated during inference. Construction used a two-step assisted workflow: human authors specified the schema, difficulty targets, evidence-chain constraints, and prompts; an AI model generated a structured fictional blueprint and realized it as a narrative. Automated scripts then checked structure, reference mappings, difficulty ranges, and single-culprit consistency. The supplement includes independent review sheets and agreement tooling for human audits.

Descriptive statistics are recomputed from `metadata/case_index.csv` and the case files; they are not hard-coded into evaluation logic.

## Reproducing reported runs

The paper averages three independent runs, with stochastic seeds `42`, `44`, and `46`. Keep one output directory per seed, and retain:

- resolved YAML configuration;
- provider model identifier or immutable snapshot when available;
- raw operator traces and predictions;
- per-instance metric counts;
- micro-aggregated summaries;
- run manifest and timestamp.

Hosted model endpoints can change. Matching a model family name alone is not sufficient to guarantee bitwise or numerical reproduction of historical results.
