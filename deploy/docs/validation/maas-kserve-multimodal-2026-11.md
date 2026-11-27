# Wetlab Praxis, MaaS and KServe validation — November 2026

These are dated observations from OpenShift AI 3.5.3–3.5.4, not a live status
or a support statement for 3.7. The detailed record, command history and
request IDs are in [the archived working notes](https://github.com/PoolPooer/wetlab-operations/blob/6146d2f/manifests/maas/wetlab-3.5/WORKING-NOTES.md).
The [redeployment guide](../recovery/maas-kserve-multimodal.md) describes the
configuration and its limitations.

| Test | Result | Scope |
| --- | --- | --- |
| 24 November, MaaS Gateway → KServe EPP → Qwen TTS | Valid temporary key: HTTP 200, 57,644-byte WAV; no key: 401; invalid key: 403. | Internal port-forward; EPP logged the successful request. |
| 25 November, Praxis → MaaS → KServe EPP → Qwen TTS | Valid key: HTTP 200 and WAV; missing and invalid keys: 401/403. | Separate Praxis proxy and internal port-forwards; Gateway and EPP recorded the same request ID. |
| 26 November, same TTS path | Valid key: HTTP 200 and 57,644-byte WAV; missing and invalid keys: 401/403. | JSON request; EPP logged a request during the test; zero model pod restarts. |
| 25 November, two ASR replicas | Eight authenticated JSON diagnostics reached the managed pool: five selected node 32 and three node 42. Both models returned expected 400 for a missing audio file. | Demonstrates routing and EPP involvement, not ASR transcription, fair balancing or load-aware performance. |
| 25 November, multipart ASR | Praxis and direct MaaS Gateway requests failed HTTP 400 during payload parsing. Direct model requests on each node returned transcription JSON for a synthetic tone. | Does not prove speech accuracy or governed multipart inference. See [multipart findings](asr-multipart-findings.md). |
| 26 November, second TTS model | Node 32 standalone KServe workload returned HTTP 200 and a 57,644-byte WAV through a direct local port-forward. | Not in the MaaS TTS pool at that point; no two-replica TTS routing test. The local direct test skipped certificate verification. |

After the direct node 32 test, the standalone TTS workload was scaled to zero.
At the final recorded check on 26 November all KServe model replicas were at
zero and namespace GPU requests were zero. The shared-pool patch for two TTS
replicas was prepared but not applied. Check the live cluster; readiness of a
zero-replica resource does not prove model availability.

Still outstanding: revoked-key denial, over-quota denial and audio accounting,
real multipart ASR through MaaS, two-replica TTS routing and load-aware
performance, streaming, production ingress and verified backend TLS. No result
above establishes a production-ready deployment or the final 3.7 architecture.
