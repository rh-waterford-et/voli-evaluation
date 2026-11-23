# Overview

The results are broken down into our lab-cluster (based in Waterford) and the actual ocp cluster we used for evaluation

## Results format

Each test will have the following labeling (naming convention for easier access and viewing)

- Test Name
  - TTS (text-to-speech)
  - ASR-B (audio transciption batch response)
  - ASR-S (audio transcription stream = true)
  - EMB (embeddings)
  - IMG-G (image generation)
  - IMG-E (image editing)
  - CHAT-T (chat streaming text)
  - CHAT-TA (streaming text audio output)

- Api-Gateway
  - Istio
  - Praxis

- EPP
  - RR (round robin)
  - TL (token load)

- Load 
  - L1 (30x1) for IMG-G and IMG-E (8x1)
  - L2 (60x4) for IMG-G and IMG-E (12x2)

## Artifacts

Each folder will have the relevant json file (all test results), a jpeg snapshot for quick viewing, and a README.md (a howto) for launching the evaluation tool for deeper analysis and comparison checks
