# KServe model workload manifests

These files document the OpenShift AI-managed KServe integration with the
existing Wetlab pool and EPP. Start with the [recovery and redeployment
guide](../../docs/recovery/kserve-llmd.md).

This is the earlier router-free integration. The later MaaS proof of concept
uses a KServe-managed route, pool and EPP and is documented separately in the
[MaaS recovery guide](../../docs/recovery/maas-kserve-multimodal.md).

| File | Purpose |
| --- | --- |
| `bm003-wetlab-node42.yaml` | Sanitized historical workload example. It requests one replica; applying it after adaptation can start a GPU pod and admit traffic. |
| `llminferenceservice-template.yaml` | Adaptable workload template with `replicas: 0`. Replace all placeholders, including the final pool label, before creating it. |
| `datasciencecluster-example.yaml` | Cluster-scoped KServe enablement example for platform administrator review. It is not a general installer and must not be applied blindly. |

The existing Gateway, Praxis, EPP, InferencePool, GPU setup and model cache
remain separately managed. The workload omits `spec.router` to avoid KServe
reconciling TLS rules against the shared routing components. See the guide for
the prerequisites, validation, security limitations and known incident.
