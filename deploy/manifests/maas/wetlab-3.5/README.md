# Wetlab 3.5 MaaS redeployment files

Start with the [redeployment guide](../../../docs/recovery/maas-kserve-multimodal.md)
for the architecture, prerequisites and ordered commands. These are examples
from the OpenShift AI 3.5 Wetlab proof of concept, not a tested 3.7 installer.
Adapt every file to the destination cluster and inspect the rendered result.
Node names, identities, hostnames and addresses here are sanitized examples.

| Directory | Contents |
| --- | --- |
| `platform/` | RHCL and cert-manager subscriptions, Kuadrant, MaaS Gateway and component enablement patches. |
| `optional-postgres/` | The Wetlab local PostgreSQL example. Use an approved existing service where available. |
| `models/` | KServe `LLMInferenceService` resources for TTS and ASR; the separate node 32 TTS resource is standalone and not in the MaaS pool. |
| `access/` | MaaS model references and **test-only** subscriptions and access policies. |
| `networking/` | Gateway-to-model and EPP-to-API network policies. |
| `praxis/` | The internal Praxis proxy, configuration, policy and public CA export helper. |
| `tests/` | Internal, small TTS and ASR checks. Inspect the scripts' Wetlab-specific hostnames and identities before use. |

`models/tts.yaml` is reconstructed from the recorded live TTS specification and
the patches applied on Wetlab. It has **not** been freshly compared to the
cluster or deployed as a single manifest. Its model replica count is zero;
its scheduler is configured to start. `models/asr.yaml` also defaults model
replicas to zero while its EPP can start. Review images, network access and
the potential side effects before creating either resource.

The [test record](../../../docs/validation/maas-kserve-multimodal-2026-11.md)
identifies successful checks and remaining gaps. The previous detailed
[working notes](https://github.com/PoolPooer/wetlab-operations/blob/6146d2f/manifests/maas/wetlab-3.5/WORKING-NOTES.md)
and experimental files are preserved in Git history.
