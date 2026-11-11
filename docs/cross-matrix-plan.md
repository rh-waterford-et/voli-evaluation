# Cross-Matrix Evaluation Plan

## Istio and Praxis across TTS, ASR, embeddings, image and omni-modality

Status: draft for review
Owner: TBD
Last updated: 2026-11-10

The deliverable is a set of figures and tables, plus a short claims
appendix stating what we can and cannot say. The matrix is the artifact:
gateway × modality cell × scheduling profile × load.

## 1. Scope

In scope:

- `/v1/audio/speech` with `qwen3-tts`
- `/v1/audio/transcriptions` (batch) and streaming transcription, model TBD
- `/v1/embeddings` with `Qwen3-Embedding`
- `/v1/images/generations` and `/v1/images/edits` with `Qwen-Image-2.1`
- `/v1/chat/completions` with `Qwen-Omni-30B-A3B-Instruct` (text in,
  text + audio out)
- Compare Istio and Praxis on the same ready workloads and EPP profiles
- Both gateways with EPP enabled, plus a direct-to-model control (bypass). The
  control measures the full path difference, including gateway, EPP,
  transport and any change in backend selection (Section 5.3)

Out of scope (tracked separately):

- Metering (stretch goal of the epic)
- Batch/async multi-file workloads
- Productization, autoscaling and flow control
- Model quality tuning; we only run validity and optional quality
  sidecars (Section 6.4)

## 2. What the tool gives us, and what it does not

The evaluation harness is `rh-waterford-et/voli-scorer-evaluation`:
`scripts/stream_metrics.py` plus the dashboard (FastAPI + React/Recharts).
It is the right tool for this matrix because it normalizes streaming
timing per modality, stores per-request results, and already encodes
scorer caveats. The plan below is built on its real behavior, not on
assumptions.

### 2.1 Supported measurements

| Cell | Endpoint | Primary metrics produced |
| --- | --- | --- |
| TTS | `/v1/audio/speech` | TTFA (first audio event), audio chunk gap, E2E, bytes, error status |
| ASR batch | `/v1/audio/transcriptions` | E2E, empty-transcript rate, HTTP status |
| ASR stream | `/v1/audio/transcriptions` with `stream=true` | time to first transcript text, text chunk gap, E2E |
| Embeddings | `/v1/embeddings` | E2E, returned vector dimension, usage |
| Image gen | `/v1/images/generations` | E2E, validated-PNG rate, dimensions, bytes |
| Image edit | `/v1/images/edits` | E2E, validated-PNG rate, dimensions, bytes |
| Omni | `/v1/chat/completions` | TTFT, TTFA, TPOT estimate, text/audio gap, E2E |

Each run records response outcomes and may include per-request pod
attribution and raw EPP scores (`--epp-scores`) when the deployed path
and log collection support them. Mark unavailable attribution or scores
as unknown.

Latency eligibility is already filtered: image runs count only
base64 PNGs with a valid header; transcription runs exclude empty
transcripts. This means **throughput and latency must be read together**,
or a server that returns empty audio looks artificially fast.

### 2.2 Known gaps to plan around

These are the constraints that most affect the matrix design.

1. **Chat input is text only.** `payload_for()` sends
   `messages[0].content` as a string. The tool cannot attach an image or
   audio file to `/v1/chat/completions`. The Omni cell therefore measures
   text-in → text+audio-out, not true multimodal input. True
   multimodal-in needs a small tool patch (`--chat-image`, `--chat-audio`)
   or it stays a documented limitation.
2. **There is no `/v1/audio/transcriptions/stream` endpoint selection.**
   `--endpoint` is restricted to six paths, and streaming means
   `stream=true` on the base transcription path with
   `Accept: text/event-stream`. If the deployment exposes a distinct
   `/stream` route, the tool cannot address it as-is; either map that
   route through the gateway or add it to `ENDPOINTS`.
3. **`--suite-file` only accepts built-in profile names.** Live or
   builder-created combined profiles must be driven with `--profile NAME`.
   The matrix driver has to loop per profile (Section 7.1), not rely on a
   single suite invocation.
4. **The gateway lookup assumes Istio.** `--gateway-container` defaults to
   `istio-proxy`; backend attribution uses gateway access logs and the
   `X-Inference-Pod` response header. Praxis needs an explicit container
   name and a verified attribution path (Section 6.2).
5. **Image quality is a header check, not a decode.** Only PNG signature
   and IHDR are validated. Pixel correctness, edit fidelity and
   prompt adherence need a sidecar (Section 6.4).
6. **Scorer caveats are curated, not computed.** The dashboard joins
   `scripts/profile_caveats.json` (verified as of 2026-10-22). Use it as
   a starting point and recheck its conclusions against the deployed
   router before marking or ranking cells.
7. **No curated caveats exist for `/v1/embeddings`.** Absence of a caveat
   is not evidence of support; treat embedding scorer results as
   *unverified* until we observe score data on the deployed router.

### 2.3 What we must not claim

- That cache-aware or latency-predictor routing helps a workload without
  checking the deployed router, data producers and observed scores.
  Router v0.11.0 and v1.0.0 could not estimate TTS input. PR #3712 merged
  to upstream `main` on 2026-11-02 and added TTS input estimation to the
  default estimate backend. Confirm the deployed image contains the fix
  and that the estimate backend is configured. Pseudo-tokens support
  approximate matching, not precise engine KV-block matching; latency
  prediction also needs working sidecars and training samples.
- That a faster response is a better response for media endpoints,
  without the validity counts and (optionally) the quality sidecar.
- That a Praxis result demonstrates a routing or pod-distribution effect
  when backend attribution or EPP selection is unknown. Functional and
  latency observations can still be reported with that limitation.

## 3. Matrix definition

### 3.1 Dimensions

| Dimension | Values | Notes |
| --- | --- | --- |
| Gateway | `istio`, `praxis` | Match workloads and configuration (e.g. same model, inputs, EPP profile and load); repeat comparisons in recorded blocks |
| Routing mode | `epp` (profile header set), `default` (no header), `bypass` (direct to model service) | `bypass` isolates gateway overhead from routing |
| Cell | 7 modality cells (4.2) | One endpoint and one model per cell |
| Profile | Per-cell valid set (4.3) | Invalid cells are recorded, not ranked |
| Load | L1 steady `30x1`, L2 moderate `100x4`, L3 saturation `200x8` | Images use smaller N (4.4) |
| Repeat | 1 for screens, 3 for finalists, 5 for tail confirmation | Run order randomized within a repeat |

The full cartesian product is deliberately not run. We screen at one
load, promote two finalists per cell, and spend the budget on repeats
where the signal exists.

### 3.2 Cell catalog

| ID | Endpoint | Model | Fixture set | Streams | Key metrics |
| --- | --- | --- | --- | --- | --- |
| `tts` | `/v1/audio/speech` | `qwen3-tts` | 12 prompts, 1 fixed voice, fixed format | yes (SSE) | TTFA, audio gap, E2E, bytes |
| `asr-batch` | `/v1/audio/transcriptions` | TBD | 6 clips, 5-30 s, 2 languages | no | E2E, empty rate, WER (sidecar) |
| `asr-stream` | `/v1/audio/transcriptions` | same as batch | same clips | yes | first text, text gap, E2E |
| `emb` | `/v1/embeddings` | `Qwen3-Embedding` | 50 texts, short and long | no | E2E, dimension, cross-pod cosine |
| `img-gen` | `/v1/images/generations` | `Qwen-Image-2.1` | 10 prompts, fixed size | no | E2E, validated-PNG rate |
| `img-edit` | `/v1/images/edits` | `Qwen-Image-2.1` | 6 prompts, 1 input image | no | E2E, validated-PNG rate |
| `omni` | `/v1/chat/completions` | `Qwen-Omni-30B-A3B-Instruct` | 20 prompts, `--modalities text,audio` | yes | TTFT, TTFA, gaps, E2E |

Rules:

- One model version per cell, recorded in run metadata. Never mix model
  versions inside a cell; a model change invalidates the comparison.
- Fixtures are frozen in `experiments/fixtures/` and hashed into run
  metadata. Prompt reuse across gateways is what makes the comparison
  paired.
- Transcription streaming needs a clip long enough to produce multiple
  text events; a single event does not prove incremental delivery.
- For `emb`, keep the same input text so cross-pod vectors are comparable.

### 3.3 Profile policy per cell

Legend: **R** = required, **O** = optional/limited interpretation,
**U** = unverified, run as diagnostic only, **X** = do not run.

Check that profiles and their scorer signals work before drawing conclusions.

| Profile (built-in name) | tts | asr-batch | asr-stream | emb | img-gen | img-edit | omni |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `default` (no header) | R | R | R | R | R | R | R |
| `queueProfile` | R | R | R | R | R | R | R |
| `activeRequestProfile` | R | R | R | R | R | R | R |
| `runningRequestSizeProfile` | R | R | R | R | R | R | R |
| `loadAwareProfile` | R | R | R | R | R | R | R |
| `kvCacheUtilizationProfile` | O | O | O | X | O | O | R |
| `noHitLruProfile` | O | O | O | X | O | O | R |
| `endpointAttributeWeightProfile` | O | O | O | O | O | O | O |
| `prefixCacheProfile` | U | U | U | X | U | U | R |
| `latencyProfile` | U | U | U | X | U | U | R |
| `contextLengthProfile` | U | U | U | X | U | U | R |
| `tokenLoadProfile` | U | U | U | O | U | U | R |
| `mmEmbeddingsCacheProfile` | X | U | U | X | X | U | U |
| `sessionAffinityProfile` | O | X | X | X | X | X | R |
| `loraAffinityProfile` | X | X | X | X | X | X | O |
| `topologyAffinityProfile` | X | X | X | X | X | X | O |
| `headerLabelAffinityProfile` | O | O | O | O | O | O | O |

Notes on the soft cells:

- `sessionAffinityProfile` on `tts` only exercises affinity if the TTS
  server echoes the `x-session-token` header. If it does not, the run is
  a no-op and should be dropped rather than reported as flat.
- `headerLabelAffinityProfile` and `endpointAttributeWeightProfile` need
  distinguishable pod labels. The current TTS pods share one baseline
  label, so these collapse to a fixed preference; keep them as `O` and
  say so in the caption.

Combined profiles (`queueRunningProfile`, `activeQueueProfile`,
`activeRunningProfile`, `kvacheQueueDepthProfile`, `sessionActiveProfile`,
`sessionQueueProfile`, ...) are only promoted from Wave 3 onward, after
the single-scorer screen identifies which components matter.

For TTS on v0.11.0 or v1.0.0, exclude the four token-dependent
profiles above. On a build containing #3712, keep them diagnostic until
the configured producer and resulting scores have been checked. For
latency, also verify sidecars and training samples; for prefix matching,
describe the approximate nature of pseudo-tokens. Revalidate the curated
caveats against the deployed image: the tool's caveat file reflects an
earlier verification date and does not establish live support.

Run `U` cells only when the diagnostic has a defined signal to inspect;
record the configuration and observations. The tool may not flag every
unsupported case. Promote a cell only after verifying the signal and
documenting the reason; otherwise retain it as unverified.

### 3.4 Load and sample sizing

`--run NxC` means N total requests at concurrency C. The tool itself
warns that p99 from fewer than 100 valid requests is a rough tail
indicator, so size accordingly.

| Cell group | L0 smoke | L1 steady | L2 moderate | L3 saturation |
| --- | --- | --- | --- | --- |
| tts, omni | `10x1` | `30x1` | `100x4` | `200x8` |
| asr-batch, asr-stream | `8x1` | `30x1` | `100x4` | `200x8` |
| emb | `20x1` | `100x1` | `500x8` | `1000x16` |
| img-gen, img-edit | `4x1` | `12x1` | `40x2` | `60x4` |

Images are the budget driver: each request costs seconds to tens of
seconds. For those cells, lead with p50, validated-PNG rate and
throughput, and treat p99 as directional until Wave 4.

### 3.5 Run arithmetic

| Wave | What | Approx. runs |
| --- | --- | --- |
| W0 | Smoke: 7 cells × `default` × L0 × 2 gateways | 14 |
| W1 | Baseline: 7 cells × {`default`, `activeRequestProfile`} × {L1, L2} × 2 gateways | 56 |
| W2 | Screen: 7 cells × 4-6 required profiles × L2 × Istio, then winners on Praxis | 60-90 |
| W3 | Finalists: 2 per cell × 7 cells × {L2, L3} × 3 repeats × 2 gateways | 168 |
| W4 | Tail: 1 per cell × L3 × 5 repeats, interleaved gateways | 70 |

These are benchmark invocations, not requests. Recalibrate after W0 with
the observed per-run duration; the total is roughly 1.5-2 cluster-days
of GPU time plus wall-clock for setup and analysis.

## 4. Per-cell playbook

Each cell uses the same shape: freeze fixtures, verify attribution, run
baseline, screen profiles, promote finalists. Only the specifics differ.

### 4.1 TTS (`/v1/audio/speech`, `qwen3-tts`)

- Fixed voice and format across all runs (`--voice`, `--audio-format`);
  the payload defaults are `vivian` and `pcm` with SSE streaming.
- Prompt set should include one short (~10 words), one medium (~40) and
  one long (~120) text, so TTFA and audio-gap scale with text length.
- Expected: distribution scorers differentiate pods; TTFA is the
  sensitive metric; E2E is dominated by synthesis and less sensitive to
  routing.
- Watch: v0.11.0 and v1.0.0 cannot estimate TTS input. For builds with
  #3712, check the estimate backend and verify the candidate signals as
  described in 3.3. Investigate differences in warm-up and load before
  attributing a large result to routing.
- Optional quality check: synthesize, then transcribe with the ASR cell
  and compute WER against the prompt; record it as a sidecar metric, not
  a tool metric.

### 4.2 ASR batch (`/v1/audio/transcriptions`, model TBD)

- **Decision needed before ASR W0.** Pick a compatible transcription
  model, pin the version, and record its batch and streaming support.
  Until then mark both ASR cells blocked and proceed with ready cells;
  if only batch is supported, proceed with batch and mark streaming blocked.
- Fixture clips: clean 5 s, clean 20 s, noisy 20 s, accented 20 s,
  non-English 15 s, and one 30 s clip near the streaming boundary.
  Vary duration deliberately; ASR latency tracks audio length.
- `--language` fixed per fixture. Do not let auto-detection vary across
  gateways.
- Watch: with the passthrough parser the EPP may not extract workload
  data (issue #3963; PR #3964 pending), so distribution scorers may be
  unavailable/blind. Inspect the actual producer and score output; record
  unverified signals and use path and load-spread results where supported.
- Empty transcripts are excluded from latency by design; report the
  empty rate next to every latency number.

### 4.3 ASR stream (`stream=true`)

- Same clips as batch, so batch vs stream is a paired comparison.
- The tool reports time to first transcript text and text chunk gaps;
  `--transcription-stream` sets `stream=true` and
  `Accept: text/event-stream`.
- If the deployment exposes a dedicated `/v1/audio/transcriptions/stream`
  path, decide explicitly: either route it through the gateway for the
  test and document that the client used the base path, or add the path
  to `ENDPOINTS` in a fork. Do not silently test a different route than
  the one we claim to have tested.
- Watch: a single text event is not incremental delivery. Assert at
  least two text events on the long clip, and plot the chunk-gap CDF
  rather than only the mean.

### 4.4 Embeddings (`/v1/embeddings`, `Qwen3-Embedding`)

- Cheap and fast, so use high N and high concurrency; this is the best
  cell for load-spread and gateway-throughput conclusions.
- Inputs: 50 texts across three length bands; same list for every run.
- Metrics: E2E, returned dimension (must be constant), and a
  cross-pod determinism check: send the same text repeatedly and compare
  vectors by cosine per pod. A pod returning truncated or different
  vectors is a defect, not a latency result.
- Watch: no curated caveats exist for this endpoint. Treat scorer
  behavior as unverified and state that in the figure caption.
- `tokenLoadProfile` is marked **O** rather than **X**: prompt tokens are
  likely estimable here, so it is worth one diagnostic run. Confirm that
  the EPP actually reports a token-load signal before trusting it.

### 4.5 Image generation (`/v1/images/generations`, `Qwen-Image-2.1`)

- Fixed `--size` (for example `1024x1024`) across every run. Changing
  size changes generation cost and invalidates the comparison.
- 10 prompts covering short/long and simple/complex scenes.
- Only validated base64 PNGs count; report unverified and URL-only
  responses separately. A gateway that downgrades `response_format` or
  rewrites the body will show up here, which is itself a finding.
- Watch: diffusion cost can dominate E2E. The `bypass` control measures
  the combined path difference, not gateway overhead alone; a small E2E
  difference does not establish that gateway overhead is negligible.
- `kvCache` is limited (stage-0 usage only) and `mmcache` is structurally
  not useful for text-prompt generation.

### 4.6 Image edits (`/v1/images/edits`, `Qwen-Image-2.1`)

- One uploaded input image (`--image`), stored with the run. Reusing the
  same input can warm server caches; keep the reuse constant across
  gateways, or alternate two images and treat image identity as a
  blocking factor.
- Latency includes upload and response processing. Compare like with
  like: same file, same size, same prompt.
- Watch: the parser may skip uploaded file parts, so `mmcache` and
  prefix signals are unverified. Multipart handling is also where
  gateways most often differ (`Expect`, timeouts, body size limits), so
  this cell is a useful gateway stress test even if routing is blind.
- Quality sidecar: decode and check dimensions plus a perceptual hash
  distance to the input; flag outputs that ignore the source image.

### 4.7 Omni (`/v1/chat/completions`, `Qwen-Omni-30B-A3B-Instruct`)

- Chat can provide inputs for several scorer paths, but each still needs
  the configured producer and an observable signal. The current text-only
  input does not establish a reusable multimodal-embedding cache signal;
  keep `mmcache` unverified for this cell.
- Requires `transformers` in the benchmark venv for tokenization.
- Two sub-rows worth separating:
  - `omni-text`: `--modalities text` (TTFT only)
  - `omni-av`: `--modalities text,audio` (TTFT + TTFA + audio gaps)
- Session affinity: use `--session-length 4` and `--concurrency` equal to
  the number of sessions, then read `same_pod` vs `changed_pod` from
  `session_replay`. This is the cleanest way to prove the gateway
  preserves session tokens.
- True multimodal input (image or audio in) is **not supported** by the
  current payload builder. If the epic needs it, budget a small upstream
  patch and a new fixture path; do not fake it with a text description.

## 5. Gateway comparison protocol

### 5.1 Freeze the variables

Before W0 on Istio and again before the Praxis rerun (before each subsequent comparison block), capture into
`experiments/meta/<wave>.json`:

- cluster, namespace, node pool, GPU type and count
- model server image digests and replica counts per cell
- EPP image and router version, and the live ConfigMap hash
- gateway image digest, and for Praxis the Auth/BBR feature state
- tool git SHA, `profile_caveats.json` `verified_as_of`
- fixtures hash, prompt list hash, image and audio file hashes
- date/time window and who else was on the cluster

If any of these changed between Istio and Praxis, the gateway delta is
confounded. Record it and split the comparison rather than averaging
over it.

### 5.2 Make Praxis attribution work, or declare it unknown

The tool's pod attribution is the foundation of the routing figures. On
Istio it reads gateway access logs from the `istio-proxy` container and
falls back to the `X-Inference-Pod` response header. For Praxis:

1. Identify the gateway pod container name and pass
   `--gateway-container <name>`.
2. Verify that the backend pod is visible: run a single-profile smoke
   with `--debug` and require that at least 95% of requests resolve to a
   real pod, not `unknown`.
3. If the response header is not preserved, check whether the EPP score
   log records the picker decision and use that as the attribution
   source.
4. If neither works, mark `routing_attribution: unknown` in run metadata
   and drop the per-pod figures for Praxis. Report latency and failure
   results, and say explicitly that distribution is unavailable.

Do this in W0, before spending runs. A Praxis matrix collected with
broken attribution produces charts that look fine and mean nothing.

### 5.3 Control runs

For every cell, at L2 only:

- `bypass`: call the model service directly, no gateway, no EPP
- `default`: through the gateway with no `EPP-Profile` header
- `epp`: through the gateway with an explicit profile

Interpret matched comparisons as follows:

- `default` minus `bypass` is the **combined path difference**. The
  paths differ in gateway, EPP, transport and possibly backend selection;
  do not label the result gateway overhead.
- Explicit `epp` profile minus `default` on the same gateway compares
  two configured routing paths. Confirm the live default profile, and
  use EPP scores and selections to investigate any observed difference.
  A latency difference alone does not prove a routing benefit.
- Praxis minus Istio compares the gateway paths for the same workload,
  profile, backend configuration and client location; report remaining
  differences such as authentication, transport and run time.

To estimate gateway overhead separately, add a verified gateway route
that bypasses EPP to the same model backend, and compare it with direct
access using matched protocol, network location, backend selection and
workload. If those conditions cannot be matched, report only the
combined path difference and its confounders. Record the actual default
configuration before calling it round robin.

### 5.4 Quality sidecars (optional, but cheap insurance)

The tool does not score media quality. Add three small checks that run
after each finalist run, outside the latency path:

- TTS: ASR round-trip WER against the input text
- ASR: WER/CER against reference transcripts, per fixture
- Images: decode success, requested-vs-returned dimensions, mean
  perceptual distance for edits

Embeddings: cosine consistency across pods for identical input. Omni:
assert both text and audio events are present, and transcribe the
generated audio to confirm it is not noise.

### 5.5 Ordering and randomization

- Compare gateways (Istio, Praxis) in repeated, time-near blocks where feasible. 
  Alternate gateway order across blocks and interleave `default` and `epp` within
  each block; record ordering and cluster changes.
- Randomize profile order within each repeat, and log the order. The
  dashboard already shows an execution-order note for profiles measured
  inside a suite run; our own plots must carry the same caveat.
- Send a few warm-up requests before each measured run. Don’t include them in the 
  results.
- Never run two cells or two gateways concurrently on the same GPU pool.
- If more than 1% of requests fail, investigate before interpreting latency. 
  Report failures alongside latency.

### 5.6 Decision rules

A gateway difference is only reported when all of the following hold:

- Same cell, model version, fixture set, load and routing mode
- At least 100 valid requests per side for tail claims (or mark the
  claim directional). Note that 100 requests still gives a rough p99: the 
  slowest 1% is only about one request.
- Median or p99 difference larger than 5% / 10% respectively, with
  non-overlapping bootstrap 95% confidence intervals
- No increase in failure rate above 0.5 percentage points
- Stream shape preserved (event count, first-event timing, no buffering
  collapse)

If the effect is inside the noise band, report "no measurable
difference" with the confidence interval, not a winner.

## 6. Data pipeline and plotting

### 6.1 Collection

Drive the CLI, not the UI, for the matrix. The dashboard is for review
and Compare, not for batch execution.

```bash
# one cell, one profile, one load, one repeat
uv run --project /path/to/voli-scorer-evaluation python \
  scripts/stream_metrics.py \
  --url "$GATEWAY_URL" \
  --endpoint /v1/audio/speech \
  --model qwen3-tts \
  --profile queueProfile \
  --run 100x4 \
  --prompts-file experiments/fixtures/tts-prompts.txt \
  --output-json "results/raw/${RUN_ID}.json" \
  --epp-scores
```

Driver rules:

- `--profile NAME` per invocation, because `--suite-file` rejects live
  or combined profiles and `--run` cannot be combined with it.
- Use `--profiles a,b,c` only for screens where every profile is in the
  built-in map.
- Collect EPP scores during W0/W1 preflight for representative routing
  checks and for W3/W4 comparisons where available. `--epp-scores` needs
  EPP JSON logging with `--v=4` and PyYAML, and adds log volume.
- For direct bypass controls, disable gateway lookup if it is not
  applicable and record the direct backend selection separately. For
  gateway runs, retain lookup and mark unresolved attribution as unknown.
- Emit one JSON per (wave, gateway, cell, profile, load, repeat) with the
  run ID convention in Appendix C.

After collection, copy or symlink the finalist JSONs into the tool
repo's `reports/` directory so reviewers can open them in History and
Compare. Keep the canonical copies in this repo.

### 6.2 Normalize to tidy tables

`experiments/collect.py` reads raw JSON and writes two tables:

`runs.csv` (one row per run):

| Column | Source |
| --- | --- |
| `run_id, wave, gateway, routing_mode, cell, profile, scorer` | metadata |
| `iterations, concurrency, repeat` | run block |
| `valid, failed, missing, excluded_unverified, empty` | run counts |
| `p50_ttft, p99_ttft, p50_ttfa, p99_ttfa, p50_e2e, p99_e2e` | `metrics.*` |
| `p50_text_gap, p99_text_gap, p50_audio_gap, p99_audio_gap` | `metrics.*` |
| `throughput_rps` | valid / duration |
| `caveat_status` | join with `profile_caveats.json` |
| `tool_sha, router_version, model_digest` | metadata |

`requests.csv` (one row per request): `run_id, index, status,
http_status, pod, ttfa_ms, ttft_ms, e2e_ms, bytes, transcript_chars,
image_format, image_dimensions, embedding_dimensions, session_id,
session_turn, epp_pick`.

The per-request table matters: percentiles from summary blocks cannot be
recomputed, cannot be bootstrapped, and cannot exclude warm-up.

### 6.3 Figure catalog

| ID | Figure | Encoding | Purpose |
| --- | --- | --- | --- |
| F1 | Cross-matrix heatmap | rows cells, cols profiles, color = Δp99 vs `default`, facets Istio and Praxis | Show differences with uncertainty and caveats |
| F2 | Path comparison | per cell, p50 and p99 for bypass / Istio / Praxis | Compare complete paths and disclose confounders |
| F3 | Load curves | p99 and failure rate vs concurrency, one line per profile, small multiples per cell | Where the knee is |
| F4 | Profile ranking bars | p50/p99 with bootstrap CIs, n annotated, per cell and gateway | Defensible ranking |
| F5 | Pod share | stacked bars per cell/profile with uniform-share line and CV | Is load actually spread |
| F6 | Score decomposition | stacked weighted contributions per picker decision | Why a pod won |
| F7 | Streaming CDFs | first-event latency and inter-chunk gap CDFs (ASR, TTS, Omni AV) | Does streaming survive the gateway |
| F8 | Outcome accounting | ok / failed / missing / empty / unverified per cell | Do not read speed without this |
| F9 | Session affinity | same-pod vs changed-pod vs unresolved | Does the gateway preserve tokens |

Rules for every figure:

- Annotate valid n and the operability status checked against the live
  router, using `profile_caveats.json` as a starting point.
- Hatch or gray out excluded and still-unverified cells; do not rank
  profiles without verified signals.
- Use Δp99 as a ratio to the cell's `default`, not raw milliseconds
  across cells; raw milliseconds make image cells dominate everything.
- Put tool SHA, router version and run IDs in the caption.
- Use log scale for latency distributions, linear for ratios.

F1 is the required artifact; F2 and F8 are required for the gateway
claim. The rest support the narrative.

### 6.4 Reading the results

- Compare cells within a row, profiles within a column, gateways
  between panels.
- If the interval for the `default` versus `epp` difference is too wide
  to resolve the agreed effect, report an inconclusive comparison.
- Uniform pod shares can result from ties, workload, or several routing
  mechanisms. Inspect the topology and EPP selections before attributing
  the pattern to any one component.
- If `bypass` is faster, report the combined path difference and inspect
  transport, gateway, EPP and backend selection before assigning a cause.
- If exclusion rates differ across gateways, the latency comparison is
  invalid until the cause is understood (usually a changed
  `response_format` or a truncated stream).

## 7. Execution waves and gates

| Wave | Gate to proceed |
| --- | --- |
| W0 Smoke | Start with one ready, agreed workload through both gateways; verify valid results and EPP path, and record versions. Check attribution and streaming where applicable. Mark other cells blocked until prerequisites are ready. |
| W1 Baseline | For each ready cell, run both gateways at L1/L2 with `default` and an available load-aware candidate, twice per combination; run the L2 bypass twice. Record outcomes and differences without assuming stability from two repeats. |
| W2 Screen | For cells with a functional baseline on both gateways, check candidate signals and screen usable profiles; record unavailable or inconclusive results. |
| W3 Finalists | Repeat up to two supported candidates per ready cell; record confounders and estimate differences where enough independent blocks exist. |
| W4 Tail | Add load and repeats where feasible; qualify sparse p99 results and draft the claims appendix. |

Choose and pin the ASR model before its W0 runs; it does not block W0 for
other cells. For routing claims require verified EPP selection and at
least 95% pod attribution for the relevant runs. If attribution remains
unknown, mark it explicitly and keep functional and latency results
separate from routing claims. Run the small baseline through both
gateways before expanding the matrix. Alternate gateway order across
subsequent blocks when feasible; record drift and repeat matched controls
when the environment changes.

## 8. Deliverables and repo layout

```text
docs/cross-matrix-plan.md          # this plan
experiments/
  matrix.yaml                      # cells, profiles, loads, repeats
  meta/<wave>.json                 # frozen environment metadata
  fixtures/                        # prompts, audio, images + hashes
  bin/run-matrix.sh                # driver (per-profile invocations)
  collect.py                       # raw JSON -> runs.csv + requests.csv
  plot.py                          # runs.csv -> figures
  reports/                         # finalist JSONs for the dashboard
  results/raw/                     # untouched tool output
  results/tidy/                    # CSV tables
  results/figures/                 # SVG/PNG
docs/results/                      # claims appendix + figure captions
```

Definition of done:

1. F1, F2, F8 published with n and caveat annotations.
2. `runs.csv` covers both gateways and every cell, including skipped
   cells with a reason.
3. Claims appendix lists supported, unsupported and unverified
   statements per cell.
4. Raw JSON retained and reproducible from the driver plus metadata.
5. The three tool gaps that block us (media input for chat, `/stream`
   route, Praxis container/attribution) are filed with concrete
   reproduction notes.

## 9. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Praxis attribution fails | No per-pod routing figures | W0 gate; fall back to EPP logs; declare unknown |
| Transcription model undecided | ASR cells blocked | Decide before ASR W0; continue ready cells |
| Router cannot parse media bodies | Misleading scorer results | Follow 4.3; do not promote `U` to finalists |
| Image runs dominate budget | Matrix incomplete | Small N for images; lead with p50 and validity |
| Cluster drift between gateways | False gateway delta | Freeze metadata; rerun controls; interleave |
| Image/audio cache warmth | Biased E2E | Fixed fixtures, alternate two inputs, warm-up discard |
| Builder or Helm overwrite between waves | Config hash mismatch | Snapshot ConfigMap per wave; verify before each wave |
| p99 from small N | Overconfident tails | Report valid N and tail observations; repeat independent blocks and qualify sparse estimates |
| Tool version changes mid-matrix | Schema drift | Pin tool SHA; upgrade only between waves |

## 10. Open questions

1. Which transcription model, and does it support `stream=true` with
   multiple text events?
2. Does the deployment expose `/v1/audio/transcriptions/stream` as a
   distinct route, or is streaming only a request field?
3. Which Praxis features are actually available for this window (Auth,
   BBR), and should each be a separate matrix axis?
4. Do we need true multimodal input for Omni now, which implies an
   upstream tool patch, or is text-in acceptable for this baseline?
5. Who owns the quality sidecars, and is WER acceptable as a gating
   metric or only reported?
6. Is there a second GPU pool for `bypass` controls, or must bypass runs
   steal capacity from the gateway runs?

## Appendix A. First commands

```bash
# environment
python3 -m venv /tmp/voli-venv
/tmp/voli-venv/bin/pip install -r dashboard/backend/requirements.txt
/tmp/voli-venv/bin/pip install transformers   # omni chat only

# smoke, one cell, direct
/tmp/voli-venv/bin/python scripts/stream_metrics.py \
  --url "$MODEL_URL" \
  --endpoint /v1/embeddings \
  --model Qwen3-Embedding \
  --no-backend-lookup \
  --run 20x1 \
  --output-json /tmp/emb-smoke.json

# smoke, through the gateway, with attribution checks
/tmp/voli-venv/bin/python scripts/stream_metrics.py \
  --url "$GATEWAY_URL" \
  --endpoint /v1/embeddings \
  --model Qwen3-Embedding \
  --profile default \
  --namespace "$NAMESPACE" \
  --run 20x1 \
  --debug \
  --output-json /tmp/emb-gateway-smoke.json

# dashboard, for review only
dashboard/.venv/bin/uvicorn app:app --app-dir dashboard/backend --port 8765
```

## Appendix B. Matrix manifest sketch

```yaml
gateways:
  istio:  { url_env: ISTIO_URL,  container: istio-proxy }
  praxis: { url_env: PRAXIS_URL, container: TBD }
cells:
  - id: tts
    endpoint: /v1/audio/speech
    model: qwen3-tts
    fixtures: tts-prompts.txt
    loads: [{ n: 30, c: 1 }, { n: 100, c: 4 }, { n: 200, c: 8 }]
    profiles: [default, queueProfile, activeRequestProfile,
               runningRequestSizeProfile, loadAwareProfile,
               kvCacheUtilizationProfile, noHitLruProfile]
  - id: emb
    endpoint: /v1/embeddings
    model: Qwen3-Embedding
    fixtures: emb-inputs.txt
    loads: [{ n: 100, c: 1 }, { n: 500, c: 8 }, { n: 1000, c: 16 }]
    profiles: [default, queueProfile, activeRequestProfile,
               runningRequestSizeProfile, loadAwareProfile]
repeats: { baseline: 2, screen: 1, finalist: 3, tail: 5 }
```

## Appendix C. Run ID convention

```text
<wave>-<gateway>-<cell>-<profile>-<n>x<c>-r<repeat>
W2-istio-img-edit-queueProfile-40x2-r1
W3-praxis-omni-av-activeQueueProfile-200x8-r2
```

## Appendix D. Metric definitions

| Metric | Meaning |
| --- | --- |
| TTFT | Time to first text or reasoning token/event |
| TTFA | Time to first audio event (TTS, or Omni with audio modality) |
| TPOT estimate | Per-output-token time derived from stream timing |
| Text gap | Inter-chunk gap for text events |
| Audio gap | Inter-chunk gap for audio events |
| E2E | Full HTTP request duration, including upload for multipart |
| Valid response | Successful response whose required output is verifiable |
| Unverified | Successfully parsed but output not verifiable (image URL, non-PNG, empty transcript) |

## References

- Tool: <https://github.com/rh-waterford-et/voli-scorer-evaluation>
- Dashboard guide: <https://github.com/rh-waterford-et/voli-scorer-evaluation/blob/main/dashboard/README.md>
- Scorer caveats: <https://github.com/rh-waterford-et/voli-scorer-evaluation/blob/main/scripts/profile_caveats.json>
- Epic context: [README.md](../../README.md)
