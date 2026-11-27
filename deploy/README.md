# Deployment references

This directory contains deployment templates and evidence from the Wetlab
OpenShift AI-managed KServe, MaaS, Praxis and llm-d investigation. Start with
the [redeployment guide](docs/recovery/maas-kserve-multimodal.md). The files
are **sanitized examples**, not an export of the current cluster or a validated
OpenShift AI 3.7 installer.

Cluster names, node names, user identities, internal addresses and some paths
have been replaced with examples for this public repository. Replace every
example value consistently, obtain approved model weights and images, and
review the selected OpenShift AI version and existing infrastructure before
creating anything. No secrets, model weights or runtime images are included.
Do not download models without the cluster owner's approval.

The included test scripts also contain example hostnames, namespaces and test
users; inspect and update them before running. Links to archived Wetlab
operations history may require access to the source repository.

| Location | What it contains |
| --- | --- |
| [MaaS deployment templates](manifests/maas/wetlab-3.5/README.md) | Grouped platform, KServe-managed TTS/ASR, model-access, network, Praxis, optional database and test files. |
| [MaaS and KServe redeployment guide](docs/recovery/maas-kserve-multimodal.md) | Architecture, prerequisites, ordered commands and security limitations. |
| [Functional validation results](docs/validation/maas-kserve-multimodal-2026-11.md) | Successful tests, multipart ASR failure and untested behavior. |
| [Multipart ASR findings](docs/validation/asr-multipart-findings.md) | Failure evidence, reproduction and upstream handoff. |
| [Shared-EPP KServe handover](docs/recovery/kserve-llmd.md) | Earlier router-free workload integrated with independently managed Gateway, Praxis, pool and EPP. |
| [KServe workload templates](manifests/kserve/README.md) | Router-free workload and OpenShift AI component examples. |
| [Model-cache examples](manifests/model-cache/README.md) | Static node-local storage examples; model data is not included. |

The MaaS TTS test used a separate Praxis proxy forwarding to the MaaS Gateway,
which consulted a KServe-managed pool and EPP. The earlier shared-EPP setup and
the Istio/Praxis benchmark paths are different configurations. **The TTS EPP
profile here uses passthrough, queue and KV-cache scorers; it is not the
explicit RR or scorer-profile matrix configuration.** Use the
[evaluation plan](../docs/evaluation_plan.md) and
[test matrix](../docs/test_matrix.md) to configure and verify benchmark
profiles; do not infer load-aware results from this deployment reference.

The `models/tts.yaml` manifest is reconstructed from the recorded Wetlab
configuration and patches. It has not been verified as a standalone new-cluster
deployment or compared with the latest live state. Model replicas default to
zero, but schedulers and other components can still start. The older
`bm003-wetlab-node42.yaml` snapshot defaults to **one** replica; do not apply
it unchanged. Both are examples for review, not a single-command deployment.

Successful TTS used a temporary MaaS key and internal port-forwards. Revoked-key
and quota checks, multipart ASR through MaaS, two-replica TTS balancing,
production ingress and verified backend TLS remain unproven in this reference.
