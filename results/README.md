# Overview

Results are grouped by cluster: `lab-cluster` (our in-office lab in Waterford) and `ocp` (the OpenShift cluster used for evaluation).

## Results format

Each test uses the following labels for easier access and comparison.

- Test Name
  - TTS (text-to-speech)
  - ASR-B (audio transcription, batch response)
  - ASR-S (audio transcription, `stream=true`)
  - EMB (embeddings)
  - IMG-G (image generation)
  - IMG-E (image editing)
  - CHAT-T (chat, streaming text output)
  - CHAT-TA (chat, streaming text and audio output)

- API Gateway
  - Istio
  - Praxis

- EPP
  - RR (round robin)
  - TL (token load, used in the existing results)
  - SP (any scorer profile; use its actual name when testing multiple profiles)

- Load
  - L1 (`30×1`; `8×1` for IMG-G and IMG-E)
  - L2 (`60×4`; `12×2` for IMG-G and IMG-E)

`N×C` means N total requests at up to C concurrent requests. See the [test matrix](../docs/test_matrix.md) for repeats, run naming and optional L3 loads.

## Artifacts

Each test folder contains a complete dashboard run directory (`meta.json`, `log.txt`, `profiles/` and any saved inputs) and a screenshot for quick viewing. Keep the timestamped run directory's name and internal structure unchanged. A per-test README is optional for run-specific notes; shared viewing instructions are below.

## View and compare results

Viewing and comparing saved results does not require cluster access or an `oc login`.

1. Clone [voli-scorer-evaluation](https://github.com/rh-waterford-et/voli-scorer-evaluation) if needed, then follow its [dashboard setup guide](https://github.com/rh-waterford-et/voli-scorer-evaluation/blob/main/dashboard/README.md) to install the local dependencies.

2. Copy the timestamped run directories into the tool's `dashboard/data/runs/` directory. For the existing lab TTS results, run these commands from this repository's root (assuming the tool is checked out alongside it):

   ```bash
   mkdir -p ../voli-scorer-evaluation/dashboard/data/runs/
   cp -Rn results/lab-cluster/tts-istio-rr-l1/20261123-111615-76f8e0 ../voli-scorer-evaluation/dashboard/data/runs/
   cp -Rn results/lab-cluster/tts-istio-tl-l1/20261123-113202-4fa9a9 ../voli-scorer-evaluation/dashboard/data/runs/
   ```

   The dashboard reads the copied runs from its own directory; it does not scan this repository's `results/` directory.

3. Start the dashboard from the tool repository:

   ```bash
   cd ../voli-scorer-evaluation
   dashboard/.venv/bin/uvicorn app:app --app-dir dashboard/backend --port 8765
   ```

   Open [http://localhost:8765](http://localhost:8765).

4. In **History**, select the RR and token-load runs and click **Compare selected**. Expand suite runs to select individual profiles if needed. Choose the same load (`30×1` for these results), then compare **TTFA** (first audio) and **E2E** (full request duration), starting with **p50**. Open individual runs for pod distribution and per-request EPP scores. Check response counts and failures alongside latency, and read any comparison warnings.
