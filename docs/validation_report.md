# Validation Report

Release: `1.0.0`  
Validation date: 2026-09-01 (UTC)  
Upstream repository commit used as the data/code starting point: `2202be69187ae000c000c088e9b67edd72eaed21`

## Completed checks

- Loaded and structurally validated all 300 released cases.
- Verified 100 cases in each Easy, Medium, and Complex split.
- Verified every gold culprit is present in its fixed candidate set.
- Ran all 11 dependency-light unit tests successfully.
- Ran the complete final-paper operator path on all 300 cases with the offline backend.
- Verified exact candidate coverage, non-negative probabilities, and unit probability mass for every output.
- Verified every operator trace ends in ANS.
- Verified the corrected `Z0` reuse behavior at iteration zero.
- Verified ANS inputs exclude challenge, quarantine, and discard histories.
- Verified the gold verdict string is absent from the inference trace in the control-flow test.
- Ran every listed NarraCrime baseline through inference and evaluation smoke tests.
- Ran the `42 / 44 / 46` repeated-run orchestration and aggregate writer.
- Parsed every JSON, YAML, and CFF file and compiled every Python source file.
- Checked README relative links, HTML tag balance, SVG XML validity, and Git whitespace errors.

## Offline call-path coverage

The mock backend varies observable difficulty so both routes are exercised:

| Split | Cases run | Route behavior | Mean LLM-operator calls |
|---|---:|---|---:|
| Easy | 100 | FAST | 4.0 |
| Medium | 100 | ITER | 11.0 |
| Complex | 100 | ITER | 14.0 |

These are integrity-test call counts, not paper performance results.

## External-model boundary

No private API credential is stored in the repository. The OpenAI-compatible DeepSeek-V3.2 inference path and separate GPT-5.5 evaluator path are configuration-complete but cannot be live-tested without the corresponding user endpoints and keys. Provider model aliases, response-format support, and snapshots should be recorded with every real run.
