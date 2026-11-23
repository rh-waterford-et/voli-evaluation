# VOLI Test Matrix

Run every row in the dashboard through **both Istio and Praxis**, using **RR and SP**, at **L1 and L2**. **L3 is optional** for a higher-load follow-up. `N×C` means **N total requests, up to C running at once**.

Repeat each combination **three times**, one run at a time. Alternate RR/SP order between repeats. Keep the model, inputs, backend pool and output settings identical within comparisons.

| Test | Workload and endpoint | L1 | L2 | L3 (optional) | Additional results to inspect |
|---|---|---|---|---|---|
| **TTS** | Text-to-speech; `/v1/audio/speech`, streaming audio | `30×1` | `60×4` | `100×8` | First audio, audio-event gaps, audio present |
| **ASR-B** | Audio transcription; `/v1/audio/transcriptions`, batch response | `30×1` | `60×4` | `100×8` | Nonempty transcript |
| **ASR-S** | Audio transcription; `/v1/audio/transcriptions`, `stream=true` | `30×1` | `60×4` | `100×8` | First transcript text, text-event gaps, incremental delivery |
| **EMB** | Embeddings; `/v1/embeddings`, non-streaming | `30×1` | `60×4` | `100×8` | Nonempty vectors, consistent dimensions |
| **IMG-G** | Image generation; `/v1/images/generations`, non-streaming | `8×1` | `12×2` | `20×4` | PNG-header validation, returned dimensions |
| **IMG-E** | Image editing; `/v1/images/edits`, uploaded image, non-streaming | `8×1` | `12×2` | `20×4` | PNG-header validation, returned dimensions |
| **CHAT-T** | Chat; `/v1/chat/completions`, streaming text output | `30×1` | `60×4` | `100×8` | First text, text-event gaps, text present |
| **CHAT-TA** | Chat; `/v1/chat/completions`, streaming text + audio output | `30×1` | `60×4` | `100×8` | First text, first audio, text/audio-event gaps, both outputs present |

ASR uploads a complete audio file; ASR-S streams the response. Both chat rows use text input.

**EPP labels:** `RR` = round-robin baseline (`noScorers`, using `max-score-picker` tie-breaking). `SP` = scorer profile (a single scorer or a combination of scorers). For SP, inspect candidate scores and picker choices against the profile’s intended behavior; an even pod split is not always the goal.

**Run names:** `<test>-<gateway>-<epp>-<load>-r<repeat>`, all lowercase. Example: `tts-istio-rr-l1-r1`. Repeat suffixes are `r1`, `r2`, `r3`. When testing multiple scorer profiles, replace `sp` in the run name with the actual profile name to distinguish them.

**Compare:** valid/failed/missing/empty/unverified counts, p50 end-to-end latency, the row's additional results, and pod distribution. Compare RR versus SP at the same gateway/load, then Istio versus Praxis at the same EPP/load. Treat p99 as a rough indicator at these sample sizes. Missing SP scores leave scorer behavior inconclusive; unavailable serving-pod attribution leaves distribution unknown.

**Keep per run:** result JSON and a dashboard graph screenshot under the run name. Mark unavailable combinations as blocked with a short reason.
