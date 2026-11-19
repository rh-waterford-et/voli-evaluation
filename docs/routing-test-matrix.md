# VOLI — Token-Load Routing Test Matrix


## 1. What we are testing

The November 16 integration sync identified `token-load-scorer` as the immediate load-aware routing focus. This matrix tests whether requests work through the intended paths, whether EPP actually uses token-load information to choose a replica, and how that profile compares with a round-robin control. It can be extended with other scorers later.

**Keep three findings separate:**

1. **Functional:** did the request reach a real model and return the required output?
2. **Routing:** did the intended EPP receive useful token information and select a replica according to the profile?
3. **Performance:** under the same workload and conditions, what happened to client latency, successful throughput and errors with token load versus round robin?

A successful request does not prove that token-load scoring worked. A latency difference does not by itself prove that the scorer caused it. A tie does not by itself prove that the scorer is broken.

This is a **proposed test plan**, not a claim that all eight workloads are required for 3.7. Start with one available workload and one path, then add ready cells.

## 2. What token-load scoring needs

For each candidate replica, token-load scoring uses an estimate of token work, including existing in-flight load and, in the checked router implementation, the estimated uncached part of the incoming request. It favors a lower calculated load. This is **not a direct measurement of GPU use or the entire cost of audio and image generation**. Estimates, cache discounts, producer configuration and the deployed router version all matter. The [scorer source](https://github.com/llm-d/llm-d-router/blob/main/pkg/epp/framework/plugins/scheduling/scorer/tokenload/token_load.go) includes both components; the [scorer README](https://github.com/llm-d/llm-d-router/blob/main/pkg/epp/framework/plugins/scheduling/scorer/tokenload/README.md) describes the normalization.

- Check the parser, `token-producer` backend, `inflight-load-producer`, scorer instance, weight, picker and filters actually used. An EPP that starts and picks a pod is not enough.
- Record `queueThresholdTokens`. The checked implementation defaults to **4,194,304**; small token differences may produce scores very close to one another, while values at or above the threshold are clipped. Inspect full-precision logs/results before calling scores equal; do not change the threshold during a comparison.
- Check `addEstimatedOutputTokens` and the request lifecycle in the deployed build. In the local router source checked, when that option is false, token counts for a streaming request are released at the first response chunk, even if the request continues. When enabled, an estimated output portion can remain until completion. A long audio stream is therefore not necessarily counted as token load for its whole duration. See the [in-flight producer documentation](https://github.com/llm-d/llm-d-router/blob/main/pkg/epp/framework/plugins/requesthandling/dataproducer/inflightload/README.md).
- Use one EPP replica for the clearest first experiment, or verify how its in-flight state is shared across replicas. If different EPPs maintain separate or eventually consistent views, a request routed by one may not be visible to another at the decision time. Record which EPP handled each request.

### Endpoint-specific starting points

These are source-review findings, **not proof of the deployed setup**. The detailed `Scorer Caveats`were reviewed against router v1.0.0 and `main` at `647ca7ca` on November 12. Recheck the deployed image digest, parser and producer; a mutable `main` tag is not a commit.

| Workload                          | What to check before interpreting token-load results                                                                                                                                                                                                                                                               |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Chat, text input                  | Chat parsing and a compatible token producer are available in the reviewed code; verify the actual producer and output. The current evaluation tool does not send image or audio input in chat.                                                                                                                    |
| TTS                               | Router v0.11.0 and v1.0.0 lacked TTS input estimation. [#3712](https://github.com/llm-d/llm-d-router/pull/3712) added estimation for TTS text to the estimate backend on `main`; confirm the deployed build includes it and uses the right backend. Text input estimates do not measure all audio-generation work. |
| Embeddings                        | The reviewed estimate backend handles text; the reviewed render backend does not handle this body. Confirm which is configured and that useful estimates appear.                                                                                                                                                   |
| Image generation                  | [#3721](https://github.com/llm-d/llm-d-router/pull/3721) added prompt estimation on `main` after v1.0.0. Prompt length alone does not describe output-image cost.                                                                                                                                                  |
| Image edits                       | #3721 added text estimation; [#4054](https://github.com/llm-d/llm-d-router/pull/4054) added an estimate for uploaded image input on `main` after v1.0.0. Confirm both changes in the build. Estimates remain approximate and omit output-generation cost.                                                          |
| Transcription, batch or streaming | The reviewed v1.0.0 and `main` default passthrough path did not supply an audio-input estimate. [#3964](https://github.com/llm-d/llm-d-router/pull/3964) was open at the November 12 review. Recheck its current status and the deployed parser; do not assume duration is available to EPP.                       |

**Evidence freshness:** the local router checkout used for this draft was `8f730719` dated November 6, and the scorer-caveats review above is newer. The upstream scorer source and producer behavior were also checked for this draft. The individual PR pages and latest release could not be independently refreshed, so their present status is not asserted here. Verify them when selecting the router image.

## 3. Paths, profiles and readiness

### Paths

| ID  | Actual request path                       | Purpose                                                                                    |
| --- | ----------------------------------------- | ------------------------------------------------------------------------------------------ |
| `I` | Client → Istio Gateway → EPP → model pool | Test the Istio path.                                                                       |
| `P` | Client → Praxis → EPP → model pool        | Test the Praxis path. Prove Praxis actually calls EPP and forwards to its chosen endpoint. |

For a meaningful `I` versus `P` comparison, use the **same** pool, EPP build and profile, model, replicas, client location and workload where possible; record TLS, authentication and any remaining differences. If the paths cannot be matched, report the difference as confounded. A ready Praxis pod or admitted Route alone does not prove the request followed `P`.

An optional direct request to **one pinned backend** can establish that the backend works without the gateway and EPP. It is not a round-robin scorer control and its difference from `I` or `P` is a **whole-path difference**, not gateway overhead alone.

### Profiles

| ID   | Meaning                                                          | Verify before use                                                                                                                                                           |
| ---- | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RR` | Explicit EPP round-robin control, with no ranking scorer.        | Same eligibility filters and picker as `TL`; eligible replicas have equal scores and the deployed picker rotates among ties. Confirm configuration and observed selections. |
| `TL` | EPP profile with `token-load-scorer` as the only ranking scorer. | Record actual profile/instance name, weight, threshold, producers and picker. Verify the header reaches the right EPP.                                                      |

The live profile name `tokenLoadProfile` is an example in the tool's profile map, not proof that the cluster has it. The default profile is **not automatically round robin**: the November 16 wetlab snapshot used active-request scoring by default. For a fair comparison, keep eligibility and picker the same in `RR` and `TL`; document any unavoidable differences. Do not silently substitute the default profile for either one.

### Readiness checklist — fill once per workload and path

| Check | Record / result |
|---|---|
| Date, operator, cluster, namespace, GPU type, capacity and shared-cluster activity | — |
| Workload ID, served model name, model revision, backend image digest and configuration | — |
| At least two eligible, healthy, compatible backend replicas; record pod names, node/GPU, pool and management type | — |
| Actual client URL → gateway → route → pool → EPP → backend; client location, TLS/auth and request ID propagation | — |
| EPP workload/pod count, image digest and version/commit; profile handler, header and live ConfigMap/key/hash | — |
| `RR` and `TL` actual profile names; filters, picker, weight and threshold; verify profile changes take effect | — |
| Parser, token backend, in-flight producer, prefix/cache settings, output-token setting and EPP state-sharing configuration | — |
| Tool commit/version, fixtures and hashes, output settings, logging/attribution method, time window and result location | — |
| Owner, unavailable prerequisite and next check, if blocked | — |

Use the same backend pool for both profiles.

## 4. Workload catalogue

Select and record one compatible model and one fixed fixture set for each row. Models are **to be chosen**, not assumed installed. Keep settings and inputs identical between `RR` and `TL` within a comparison. For text-input rows, use a prompt file with a balanced mix of short and long, distinct prompts, within model limits. Record the file and hash. Each nonempty line is one prompt; the script cycles through them. Different lengths are an **input-estimate experiment**, not proof that the longer input costs more GPU time.

| ID | Endpoint and exact mode | Input / settings to fix | Client observations |
|---|---|---|---|
| `TTS` | `/v1/audio/speech`, streaming SSE | Text prompts, model, voice and audio format | First audio event, audio-event gaps, E2E, audio presence and failures. |
| `ASR-B` | `/v1/audio/transcriptions`, batch response | One audio file per run, model, language and optional hint | E2E, nonempty/empty transcripts and failures. |
| `ASR-S` | Same transcription endpoint, `stream=true` | Same model/file/settings as applicable; choose a clip expected to produce multiple events | First transcript text, event gaps, E2E, completion and incremental delivery. |
| `EMB` | `/v1/embeddings`, non-streaming | Text prompts and model | E2E, finite nonempty vector, dimension and failures. |
| `IMG-G` | `/v1/images/generations`, non-streaming | Prompts, model, requested size and output settings | E2E, header-verified PNG, unverified output and failures. |
| `IMG-E` | `/v1/images/edits`, multipart input | One input image per run, prompts, model and requested size | E2E including upload, header-verified PNG, unverified output and failures. |
| `CHAT-T` | `/v1/chat/completions`, streaming text output | Text prompts, model and tokenizer | TTFT, first visible text, text-event gaps, estimated TPOT, E2E and failures. |
| `CHAT-TA` | Same chat endpoint, streaming text **and** audio output | Text prompts, model, tokenizer, voice and audio format | TTFT, first audio event, text/audio gaps, E2E, required output presence and failures. |

`ASR-S` uploads a **complete file** and streams the response. It is not live microphone input, WebSocket `/v1/realtime`, or a separate `/v1/audio/transcriptions/stream` route. The tool uses the base transcription path. `CHAT-TA` has text input and text/audio output; it is not image- or audio-input chat. Test those other paths with a suitable client if they become required.

For ASR, run different audio clips as **separate** experiments; the current tool sends the same uploaded file on every request in one run. The same applies to different image-edit input files. Hash each file and compare identical fixtures across profiles and gateways. Do not add an ASR recognition hint unless intentionally testing one. Reusing inputs can warm caches; keep warm-up and input-reuse policy consistent and record it.

## 5. Status and evidence rules

In the tables below, `—` means **not run**. Replace it with one of:

- **Pass:** the stated check was performed and the evidence supports it for the recorded configuration.
- **Fail:** the check was performed and observed behavior contradicted its expectation; link evidence.
- **Blocked:** a required model, path, profile, signal or access is unavailable; state which one and the next check.
- **Inconclusive:** the check ran but the evidence cannot establish the result, for example equal scores with no observed token imbalance or missing request correlation.
- **N/A:** explicitly agreed outside this test scope, with the reason.

Each status needs a short finding and a link or path to the run manifest, raw JSON and relevant EPP/gateway evidence. A failure or block on one endpoint or gateway does not stop other ready cells.

## 6. Phase A — functional smoke

For each ready workload and path, send **5 requests at concurrency 1** with `TL` (`3×1` for images). Confirm the request follows the intended path, EPP selects an eligible replica, the backend returns the expected output and the response is complete. For streaming, inspect event order and confirm multiple events arrive before completion on a fixture expected to stream. Send the same number with `RR` to verify profile selection and tie rotation among eligible replicas; do not demand an exact split from a tiny run.

| Workload | Istio `I`: status + evidence | Praxis `P`: status + evidence |
|---|---|---|
| `TTS` | — | — |
| `ASR-B` | — | — |
| `ASR-S` | — | — |
| `EMB` | — | — |
| `IMG-G` | — | — |
| `IMG-E` | — | — |
| `CHAT-T` | — | — |
| `CHAT-TA` | — | — |

Record failures and missing or empty output. If the backend or path is unavailable, mark **Blocked**; do not call the scorer a failure. An `I` smoke can proceed while `P` is blocked, and vice versa.

## 7. Phase B — does token-load routing actually use a signal?

Run on each path/workload that passed its own Phase A. Keep `TL` as the only ranking scorer. Record the actual candidate set, EPP instance, request IDs and times. EPP log collection requires suitable JSON decision logs and verbosity; confirm this before starting. The tool's `--epp-scores` collects scores, weighted totals and picker choices **when logs can be correlated**. It does not prove which input estimate was produced or independently measure GPU load.

1. **Input check:** at low load, send short and long distinct inputs separately. For ASR, use two separately run clips of known different durations when supported. Inspect evidence of the actual input estimate or the incoming uncached-token contribution; record its source and values. If the only visible `tokenLoad` is a combined value, account for in-flight load, cache discounts and any output estimate before attributing a difference to input length. Missing or identical estimates need investigation; do not infer them from prompt length alone.
2. **Decision check:** run overlapping requests through the **same EPP and pool**, for example `20×4` with the fixed short/long prompt set (`12×2` for images), adjusting only before comparison if the cluster cannot sustain it. Record per-candidate raw scores, totals and selected endpoint; use EPP in-flight token gauges/state or suitable timestamped logs if available. Capture several decisions where token load actually differs. Check that the highest combined score was selected among eligible candidates and that the score direction is consistent with the deployed token-load calculation.
3. **Correlate the signal:** where telemetry allows, relate the score to in-flight counts and the incoming uncached contribution at decision time. If existing in-flight load was not observed, a score difference might be caused by the incoming request or cache discount instead. If streams are still open but the producer already released input tokens, explain the tie rather than calling it a defect. Additional controlled overlapping requests may be needed; the benchmark does not guarantee that an exact imbalance is present at a particular scheduling instant.

For a strong demonstration that token *amount* matters beyond request count, compare candidates with equal numbers of active requests but different observed token loads, and capture the subsequent decision while those loads are present. This requires suitable telemetry and a controlled client or additional setup; the current benchmark does **not** guarantee this arrangement. Treat it as a targeted follow-up, not as something the `20×4` run automatically proves.

| Workload | `I` input check | `I` decision check | `P` input check | `P` decision check |
|---|---|---|---|---|
| `TTS` | — | — | — | — |
| `ASR-B` | — | — | — | — |
| `ASR-S` | — | — | — | — |
| `EMB` | — | — | — | — |
| `IMG-G` | — | — | — | — |
| `IMG-E` | — | — | — | — |
| `CHAT-T` | — | — | — | — |
| `CHAT-TA` | — | — | — | — |

**Pass for input:** evidence shows useful request-derived estimates for the chosen input and build. **Pass for decision:** correlated candidate scores and selection agree with the configured picker, and evidence shows a meaningful token-load distinction. For a claim specifically about *existing in-flight* load, independently observe that component at decision time. If values, timings or correlation are unavailable, use **Inconclusive** or **Blocked** as appropriate; report any functional observations separately.

## 8. Phase C — round robin versus token load

Proceed for a workload/path when Phase A passes, the `RR` control is verified, and Phase B provides a meaningful `TL` signal. Otherwise record the performance comparison as **Blocked** or **Inconclusive** and do not rank profiles. A functional measurement may still be recorded separately.

`N×C` means **N total requests with up to C concurrent requests**, not a fixed arrival rate. These are proposed starting settings, not proof of saturation:

| Workloads | Low `L1` | Overlap `L2` |
|---|---|---|
| `TTS`, `ASR-B`, `ASR-S`, `EMB`, `CHAT-T`, `CHAT-TA` | `30×1` | `60×4` |
| `IMG-G`, `IMG-E` | `8×1` | `12×2` |

For each ready workload and path run **`RR` and `TL` at both `L1` and `L2`, in three repeated blocks**: 12 benchmark invocations per workload/path. Alternate `RR`/`TL` order between blocks; alternate gateway order when comparing both paths. Within a block run one benchmark invocation at a time on the shared pool. As a starting warm-up, send `3×1` (`2×1` for images) with the same fixture policy before each measured run; exclude those requests from results and record any change. If the environment changes, record it and repeat the affected controls. The small image runs and 30/60-request runs are not adequate for confident p99 claims.

| Workload | Path | `L1` comparison: status + evidence | `L2` comparison: status + evidence |
|---|---|---|---|
| `TTS` | `I` | — | — |
| `TTS` | `P` | — | — |
| `ASR-B` | `I` | — | — |
| `ASR-B` | `P` | — | — |
| `ASR-S` | `I` | — | — |
| `ASR-S` | `P` | — | — |
| `EMB` | `I` | — | — |
| `EMB` | `P` | — | — |
| `IMG-G` | `I` | — | — |
| `IMG-G` | `P` | — | — |
| `IMG-E` | `I` | — | — |
| `IMG-E` | `P` | — | — |
| `CHAT-T` | `I` | — | — |
| `CHAT-T` | `P` | — | — |
| `CHAT-TA` | `I` | — | — |
| `CHAT-TA` | `P` | — | — |

For every row, keep the individual block values and report attempted, eligible, failed, missing, empty and unverified responses as applicable, plus valid sample count, primary latency, E2E, eligible throughput and routing evidence. Calculate **eligible throughput = eligible responses / measured run duration**; the script's displayed requests/s is based on attempted requests. In this table, **Pass** means the matched comparison was completed with usable evidence, not that `TL` was faster; use **Inconclusive** if drift or missing evidence prevents an interpretation. Report results even when there is no clear winner. Do not declare benefit from a single run, an uneven pod split or a small difference within run-to-run variation.

If every workload and both gateways become ready, this phase is **192 invocations** (`8 × 2 paths × 2 profiles × 2 loads × 3 blocks`), plus smoke and signal checks. Start with one workload/path, measure the actual duration and GPU cost, then decide what to expand. This count is not a commitment to run the entire matrix.

### Copy this run ledger for each workload and path

Use the actual profile names in the evidence. Record one row per invocation; `B1–B3` are repeated blocks. Order below is an example; record the order actually run. Keep the same fixture and settings within each comparison.

| Block | Order | Load | Profile | Run ID / raw JSON | Eligible / attempted | Failures, empty, unverified | Primary latency + E2E | Eligible/s | Score / selection evidence |
|---|---:|---|---|---|---|---|---|---|---|
| B1 | 1 | L1 | RR | — | — | — | — | — | — |
| B1 | 2 | L1 | TL | — | — | — | — | — | — |
| B1 | 3 | L2 | RR | — | — | — | — | — | — |
| B1 | 4 | L2 | TL | — | — | — | — | — | — |
| B2 | 1 | L1 | TL | — | — | — | — | — | — |
| B2 | 2 | L1 | RR | — | — | — | — | — | — |
| B2 | 3 | L2 | TL | — | — | — | — | — | — |
| B2 | 4 | L2 | RR | — | — | — | — | — | — |
| B3 | 1 | L1 | RR | — | — | — | — | — | — |
| B3 | 2 | L1 | TL | — | — | — | — | — | — |
| B3 | 3 | L2 | RR | — | — | — | — | — | — |
| B3 | 4 | L2 | TL | — | — | — | — | — | — |

**Ledger header:** workload / path / fixture hash: —; model and image: —; pool and EPP image/config hash: —; `RR` profile: —; `TL` profile/weight/threshold: —; client, TLS/auth and gateway: —; start/end times and warm-up: —; differences or interruptions: —; conclusion and evidence: —.

## 9. Using the scorer evaluation tool

The checked local `voli-scorer-evaluation` checkout was `9c44185` (November 17); verify and record the version actually used. The dashboard can discover profiles and run the same endpoint/profile/load combinations. Its Compare warnings are useful but do not verify the deployed router version or prove that a scorer received a meaningful signal.

EPP selection is not independent proof that the selected pod served the response: verify gateway log lookup or a trustworthy response header where available, and record serving-pod attribution as **unknown** if unavailable. A no-scorer `RR` profile may not produce scorer records; inspect picker decisions separately. 

## 10. How to interpret the results

- The tool observes client timings, not per-stage server timings. Chunk gaps are event-gap proxies, not token-level latency; first transcript and E2E include file upload, but exclude local multipart construction.
- Audio-event presence does not prove the audio is decodable or correct. PNG validation checks signature/header, not full image decoding or quality. Empty transcripts and unverified images are tracked separately and excluded from the tool's latency rankings; report those counts alongside timings.
- A request's profile, score, chosen endpoint and actual serving pod are different facts. Record which ones were observed and which remain unknown. Ties can be legitimate, especially at low load or after token counts are released.
- Repeatable scores and selections demonstrate behavior for this build and workload; they do not establish that token estimates represent all multimodal compute or that one profile is universally best. Compare repeated blocks and state material differences in errors and configuration.
