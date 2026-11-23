# VOLI Routing and Scorer Evaluation Plan

Use [test_matrix.md](test_matrix.md) for **what to run**: workloads, gateways, RR/SP labels, load levels, repeats and run names. This guide explains **how to prepare, validate and interpret those runs**. It consolidates the earlier routing matrix and cross-matrix plan.

The dashboard is the normal execution and review tool. CLI execution and additional diagnostics are optional. This is an evaluation method, not a record of completed tests or a statement that every combination is ready or required for a release.

## 1. Questions the tests answer

| Finding | Question | Evidence |
|---|---|---|
| Functional | Does the workload complete through the intended gateway and return the required output? | Client response, output checks and request-path evidence |
| Routing | Does EPP select eligible backends according to the selected profile? | Actual profile, candidate scores, picker decisions and, separately, serving-pod attribution |
| Performance | How does the profile or gateway affect client experience under matched conditions? | Repeated latency, response-outcome and throughput measurements |

Keep these findings separate. A working endpoint does not establish scorer usefulness. A faster run does not explain why routing changed. A profile can behave correctly without outperforming RR.

The matrix covers individual inference requests, streaming responses and replica scheduling. Model selection, asynchronous multi-file processing, autoscaling, metering and full media-quality evaluation require separate tests.

## 2. Paths and profiles

The two paths are **client → Istio → EPP-selected backend** and **client → Praxis → EPP-selected backend**. EPP makes the backend selection; the gateway forwards the inference request. Verify that each path actually consults EPP rather than relying on a ready gateway pod or an accepted route.

| Label | Meaning | How to use it |
|---|---|---|
| `RR` | Round-robin baseline: `noScorers`, using `max-score-picker` tie-breaking | Select the explicit profile. Inspect backend distribution; exact request-by-request alternation or an exact split in a small run is not an acceptance criterion. |
| `SP` | Scorer profile: one scorer or a combination of scorers | Record the actual profile name, scorer instances, weights, filters and picker. Evaluate its intended behavior. |

`SP` is a matrix label, not a literal cluster profile name. Token load is one candidate, not the only permitted scorer. Combined profiles are valid; their results describe the combination. To attribute a difference to one component, compare profiles that differ only in that component.

With the header-based profile handler, selecting `noScorers` should send `EPP-Profile: noScorers`. Confirm the same for each selected profile. The dashboard's `default` option sends no profile header and uses the cluster's configured default; it is not an alias for RR. Preserve profile-name capitalization in requests even though result names are lowercase.

For RR/SP comparisons, keep the backend pool, eligibility filters and picker the same wherever possible. Record deliberate differences. Selecting a no-scorer profile does not disable shared producers or background scraping, and does not guarantee identical processing overhead across profiles.

KServe is part of the recorded deployment, not an additional matrix axis by default. If managed and standalone pods share a pool, record their membership and verify eligibility and selection. Compare deployment methods separately only when investigating a specific deployment-related difference.

## 3. Prepare one workload and path

Start with an available workload and gateway. A missing Praxis path or model blocks its own combinations, not the rest of the matrix.

| Area | Check and record |
|---|---|
| Environment | Cluster, namespace, date/time, operator, client location, GPU/node types and competing activity |
| Backends | Served model and revision, image digests, replica count, pod names, nodes and pool membership; at least two healthy compatible candidates for routing comparisons |
| Request path | Gateway URL, gateway build, route, pool, EPP deployment/container, authentication/TLS and relevant gateway features |
| EPP | Image digest/version, replica count, loaded ConfigMap/key and relevant configuration; confirm profile changes have taken effect |
| Profiles | Actual RR/SP names, scorer types and weights, filters, picker, parameters and required producers or metrics |
| Inputs | Exact prompt set or uploaded file, hashes, model output settings and any session settings |
| Tool | Tool commit, dashboard parameters, scorer-caveat verification date and evidence-collection settings |

Keep this information in the result README or a linked configuration snapshot. The dashboard does not provide a complete historical cluster snapshot; capture missing details separately. Reuse the record while conditions remain unchanged, and update it when they change.

Use the same client, pool, model, inputs and output settings for matched comparisons. Record gateway differences such as TLS, authentication or BBR rather than assigning their effects to the gateway implementation alone. If the pool, configuration or competing load changes, start a new comparison block and repeat the affected controls.

## 4. Workload details

The endpoints and load values live in [test_matrix.md](test_matrix.md). These details explain how to keep each workload comparable.

| Workload | Keep fixed | Check beyond HTTP success |
|---|---|---|
| `TTS` | Text prompts, model, voice and audio format | Audio events, first-audio time, audio-event gaps and completion |
| `ASR-B` | Audio file, model, language and optional recognition hint | Nonempty transcript and E2E; record empty responses separately |
| `ASR-S` | Same audio/settings as the corresponding batch test where supported | First transcript text, multiple incremental events for a suitable clip, event gaps and completion |
| `EMB` | Text inputs and model | Nonempty finite vectors, consistent dimensions and E2E |
| `IMG-G` | Prompts, model, requested size and output settings | PNG-header validation, returned dimensions, E2E and unverified responses |
| `IMG-E` | Input image, prompts, model, requested size and output settings | Same image checks as generation; E2E includes upload |
| `CHAT-T` | Text prompts, model, tokenizer and generation settings | Text output, TTFT, text-event gaps, estimated TPOT and completion |
| `CHAT-TA` | Same chat settings plus voice and audio format | Both text and audio, TTFT, first audio, text/audio-event gaps and completion |

For text-input tests, a fixed mixture of short and long prompts can exercise different input sizes. The tool cycles through nonempty prompt lines. Input length is an experimental variable, not a measurement of GPU work.

ASR uploads a complete file; `ASR-S` streams the response on `/v1/audio/transcriptions` with `stream=true`. It does not test live microphone input, WebSocket realtime audio or a separate `/transcriptions/stream` endpoint. The tool reuses one uploaded audio file per run; different clips require separate runs. Image edits similarly use one uploaded image per run.

Both chat workloads send text input. Text-plus-audio output does not demonstrate support for image/audio input. Chat benchmarks require a tokenizer in the tool environment.

Keep input reuse and cache conditions consistent. If testing warm versus cold caches or different file sizes, name those as separate experiments rather than silently mixing them into a profile comparison.

## 5. Execution workflow

### A. Check functionality

Before measuring a new workload/path/profile, run a small dashboard smoke test: **5 requests at concurrency 1**, or **3×1 for images**. Check the intended path, profile selection, required output and response completion. Check RR and each candidate SP.

For streaming workloads, use an input expected to produce multiple events and confirm incremental delivery. A single final event does not demonstrate preserved streaming. If a model supports ASR batch only, continue batch testing and mark streaming blocked.

### B. Check profile behavior

Enable **Collect EPP scores** when evaluating scoring decisions. The collector needs request-correlated EPP JSON decision logs at the appropriate verbosity, currently `--v=4` in the checked tool documentation. Use backend lookup where serving-pod attribution is available.

Inspect several decisions at overlapping load, starting with L2 from the matrix. A separate targeted run is useful if the normal workload does not exercise the profile's intended behavior.

| Profile objective | Useful evidence |
|---|---|
| Load distribution | Different observed candidate loads, corresponding scores and selection consistent with the configured picker |
| Token load | Meaningful input/in-flight token estimates and decisions consistent with calculated token load; see Section 8 |
| Cache affinity | Reusable inputs, candidate match data and observed preference; actual backend cache reuse needs independent evidence |
| Session affinity | Multiple turns with session-token propagation and same-pod/changed-pod observations; ordinary independent requests are insufficient |
| Attribute, label or topology preference | Distinguishable eligible candidates, the relevant attributes and the expected preference |
| Predicted latency | Reachable, trained predictors and usable predictions for this workload |
| Combined profile | Each relevant component's scores and weights, the combined total and picker decision |

For `max-score-picker`, check selection against the highest combined candidate score, allowing ties. For another picker, use that picker's rules. An uneven distribution may be correct for an affinity or preference profile.

Equal scores can be legitimate. Missing data or a workload that never exercises the objective leaves scorer usefulness inconclusive; it does not automatically make the scorer faulty. Performance runs may still be retained, but do not present them as proof of the intended scoring effect.

### C. Run the matrix

Follow [test_matrix.md](test_matrix.md): both gateways, RR and each chosen SP, L1/L2, three repeats. L3 is an optional higher-load follow-up. The matrix is the source of truth for request counts, concurrency and naming; higher concurrency does not itself prove saturation.

Run one benchmark at a time against a shared backend pool. Within each repeat, keep RR and SP measurements close together. Alternate profile order between repeats, and alternate gateway order across comparison blocks. For several SPs, record the actual order and keep the matched RR control close in time.

Warm up each measured combination consistently, for example with **3×1** requests (**2×1 for images**) using the same input policy. Keep warm-up in separate runs and exclude it from measured results. Warm-cache behavior is part of that experiment, not a cold-start measurement.

The dashboard can select multiple profiles and loads, but runs them sequentially. For the clearest per-test naming and artifacts, use one profile/load per named run; otherwise identify the relevant profile/load within the saved combined result.

### D. Review and save

Use dashboard History and Compare for matched runs. Save the raw result JSON, a dashboard graph screenshot and short findings with the configuration record. If a comparison is unstable, investigate the cause and add matched repeats rather than choosing the best-looking run.

## 6. Routing evidence and dashboard limits

Keep **profile selection**, **scorer output**, **EPP's chosen endpoint** and **the backend that served the response** distinct.

The tool correlates EPP scores, weighted totals and picker decisions when logs contain matching request IDs. It obtains serving-pod attribution from gateway logs or the `X-Inference-Pod` response header where available. A picker decision alone is not independent confirmation of which pod served the response.

The default gateway log lookup assumes the `istio-proxy` container. For Praxis, use its actual container and check whether its access-log format or response headers provide attribution. Selecting a different container alone does not establish compatibility. Report the resolved fraction and keep unknown requests visible. When only EPP picks are known, label the chart **EPP selections**, not **served requests**.

For `noScorers`, no scorer entries are expected. The checked collector can label these decisions `partial` with an `incomplete scorer data` warning even when candidate totals and picker choices were captured. Inspect the issue details; that specific warning is not an RR failure. Missing totals, missing picks or unmatched requests still matter.

Dashboard caveats are curated and version-dependent. They do not identify the deployed router build, prove producers received useful input, measure GPU utilization or verify predictor training. Winner highlighting is a display aid, not validation of scorer behavior. Check the caveat file's own review date and the deployed build rather than copying an old compatibility table into a new result.

## 7. Measurements and interpretation

| Measurement | Meaning and limit |
|---|---|
| E2E | Client-observed request duration, including multipart upload; excludes local multipart construction |
| TTFT / first transcript text | First observed text/reasoning event for chat, or transcript text for ASR; not a server-stage timing |
| TTFA | First observed audio event; not proof that playback began or audio was decoded |
| Text/audio gaps | Gaps between received events; not exact per-token latency |
| TPOT estimate | Estimated per-output-token time for chat; depends on tokenization and stream timing |
| Valid count | Responses eligible for the tool's latency statistics; report attempted count and excluded outcomes alongside it |
| Eligible responses/s | `valid_responses / duration_seconds`; the script's printed requests/s uses attempted requests instead |
| Pod distribution | Serving-pod shares where attributed; preserve unknowns and distinguish EPP-pick shares |

Image latency statistics include only responses passing the tool's base64 PNG signature/header checks. URL-only or other recognized formats may be unverified. This is not full decoding or image-quality assessment. Empty ASR transcripts are recorded separately and excluded from latency statistics. Audio-event presence likewise does not establish intelligibility or correctness.

Compare **RR versus SP at the same workload, gateway and load**, then **Istio versus Praxis at the same workload, profile and load**. Inspect failures, missing outputs and exclusions before interpreting speed. Report outcome counts as recorded; categories may overlap, so do not assume they form a disjoint total.

Lead with p50, valid sample counts and the workload's first-output/streaming metrics. Small image runs and L1/L2 runs provide limited tail evidence. Even 100 valid samples make p99 depend on roughly one slow observation. L3 improves sampling and overlap, but does not turn p99 into a reliable tail guarantee.

Keep the three repeats visible. Do not average percentiles and present them as a pooled percentile, or treat a small difference within run-to-run variation as a winner. If more rigorous uncertainty estimates are needed, use the raw per-request data and repeated comparison blocks in a separate analysis; the dashboard does not automatically establish statistical significance.

## 8. Token-load diagnostic reference

Use this section when SP includes `token-load-scorer`. Other profiles need their own relevant signal checks from Section 5.

Token load is an estimate, not a direct measure of GPU use or all audio/image-generation work. Depending on the deployed router, scoring can include accumulated in-flight tokens, the incoming request's estimated uncached tokens and an estimated output component.

| Check | Why it matters |
|---|---|
| Parser and token-producer backend | The request must provide a useful estimate; support differs between endpoint types and router builds. An estimate backend and an engine-render backend are not interchangeable. |
| In-flight producer and EPP replicas | The scorer needs the relevant producer state. Record which EPP handled requests and how state is shared across replicas. |
| `queueThresholdTokens` | Normalization can make small differences look tied; inspect full-precision scores. Loads at or above the threshold receive score zero. Keep the threshold fixed within comparisons. |
| Cache discounts | A score difference can come from estimated uncached input, not only existing in-flight work. Approximate matches do not establish real backend cache hits. |
| `addEstimatedOutputTokens` and release timing | In the reviewed implementation, streaming input tokens can be released at the first response chunk; optional estimated output can remain until completion. An open audio stream therefore need not retain its input-token load. Check the deployed lifecycle behavior. |

Start with short and long distinct text inputs, separately at low load, then inspect overlapping decisions at L2. For ASR, different-duration clips require separate runs and a parser/producer that actually exposes meaningful audio input. Prompt or clip length alone is not evidence that EPP received an estimate.

For text-input TTS, embeddings and image generation, check that the deployed producer handles that request body. For image edits, check uploaded-image handling as well as prompt handling. Text estimates alone do not measure audio-output duration, image size or generation steps. Earlier reviews found missing endpoint support in older builds; consult the tool's dated caveats and the deployed source instead of assuming a PR or image tag proves support.

Capture candidate scores, totals and picks. Where telemetry permits, separate existing in-flight load from the incoming uncached contribution and output estimate. To demonstrate token amount matters beyond request count, capture candidates with equal active-request counts but different observed token loads and the subsequent selection. The ordinary matrix does not guarantee that controlled situation; it is an optional targeted follow-up.

## 9. Optional investigations

| Investigation | When useful | Interpretation |
|---|---|---|
| Direct request to one pinned backend | Diagnose whether the model works independently of the gateway/EPP path | A functional diagnostic. Its latency difference from a gateway run combines transport, gateway, EPP and possibly backend-selection effects. |
| Gateway route bypassing EPP | Investigate gateway contribution separately | Match backend selection, protocol, client location and workload; record remaining path differences. |
| No profile header | Verify default-profile behavior or header propagation | Record the actual default; do not substitute it for explicit RR. |
| Session replay | Evaluate session-affinity profiles | Use the tool's session mode and inspect token propagation and same-pod/changed-pod/unresolved turns. |
| Media quality checks | Investigate output correctness beyond presence/header checks | Decode/listen, compare ASR to reference transcripts, or inspect edit fidelity outside the timed benchmark. These are separate quality tests. |
| CSV exports, confidence intervals or additional plots | Summarize a larger result set | Build from saved per-request data when needed. No custom collector, plotting pipeline or new dashboard feature is required to run the matrix. |

CLI execution is optional. If scripting runs, use the dashboard's **Show command** preview as a starting point and preserve the same profiles, inputs, loads and result naming. Tool setup and command flags belong in the [dashboard guide](https://github.com/rh-waterford-et/voli-scorer-evaluation/blob/main/dashboard/README.md).

## 10. Results and completion

Use the run naming in [test_matrix.md](test_matrix.md). For multiple scorer profiles, use the actual profile name in place of `sp` so runs remain distinguishable. Existing `tl` result names identify token-load runs and remain valid historical labels.

Store artifacts under the appropriate existing `results/<cluster>/` area. Keep the JSON and graph screenshot identifiable by run name. The accompanying README should state the actual profile/configuration, inputs, run order and warm-up policy, then give a short finding with links to the relevant runs. A screenshot is a quick visual summary; the JSON remains the evidence for deeper review. Preserve inputs needed to reproduce the run.

| Status | Use |
|---|---|
| Pass | The specific functional or routing check is supported by evidence; a completed performance comparison need not favor SP |
| Fail | Observed behavior contradicts the stated check |
| Blocked | A required model, path, profile, signal or access is unavailable; name it |
| Inconclusive | The run completed but evidence or comparability is insufficient for the stated finding |
| N/A | The combination is deliberately outside the agreed scope; give a reason |

For each tested combination, report functional, routing and performance findings separately. A comparison is complete when the requested repeats and artifacts are available, outcomes and limitations are recorded, and missing combinations have a reason. No particular profile has to win.

For a team's quick review, show the relevant dashboard comparison graph with the run names, valid counts and one or two sentences describing the observed difference and uncertainty. Additional heatmaps, load curves or score-decomposition plots are optional when they answer a concrete question.

## References

- [Run matrix](test_matrix.md): workloads, loads, labels, repeats and naming.
- [Project context](../README.md): broader integration scope.
- [Scorer evaluation tool](https://github.com/rh-waterford-et/voli-scorer-evaluation): benchmark and dashboard.
- [Dashboard guide](https://github.com/rh-waterford-et/voli-scorer-evaluation/blob/main/dashboard/README.md): usage and collection requirements.
- [Scorer caveats](https://github.com/rh-waterford-et/voli-scorer-evaluation/blob/main/scripts/profile_caveats.json): dated endpoint-specific findings; check the version used for each experiment.
