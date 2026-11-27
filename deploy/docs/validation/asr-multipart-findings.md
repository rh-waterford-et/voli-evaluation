# Multipart ASR requests fail in the MaaS payload processors

**Status:** reproduced on Wetlab with OpenShift AI 3.5.4 on 25 November 2026.
No fix or upstream PR was recorded in this investigation. Verify current issue
and product status with the MaaS/AI Gateway maintainers. The original detailed
[findings and draft issue/PR text](https://github.com/PoolPooer/wetlab-operations/blob/6146d2f/manifests/maas/wetlab-3.5/ASR-MULTIPART-FINDINGS-AND-DRAFT-PR.md)
remain in Git history.

Hostnames, namespaces and identities in these examples have been sanitized for
this public repository. Update the scripts and configuration before repeating
the checks.

## What happened

An OpenAI-compatible `multipart/form-data` request to
`/v1/audio/transcriptions`, containing a `model` field and WAV file, returned
HTTP 400 through Praxis and directly through the MaaS Gateway. It did not
reach the model. The payload processor reported:

```text
inference error: BadRequest - failed to parse request body: invalid character '-' in numeric literal
```

Both Qwen3-ASR model pods accepted the same generated one-second tone directly
and returned HTTP 200 with a JSON `text` field. An empty transcript for a tone
is a protocol check, not evidence of speech-recognition accuracy. Separately,
eight authenticated JSON diagnostics reached both nodes via the KServe-managed
pool and EPP, then returned the expected model HTTP 400 for a missing file.
That checks routing, not governed multipart transcription or load balancing.

A controlled, route-specific experiment disabled the pre-auth payload
processor only. Missing credentials returned 401; an invalid key, a key for a
different model and a forged identity header returned 403. An authorized
multipart request then failed JSON parsing in the post-auth processor. The
experiment was disabled afterward. Do not bypass these processors on a shared
Gateway: they participate in security and model identity handling.

The pre-processor failure used request ID
`da34f917-d3e3-402f-8ebd-a4a932e3277c`; the post-processor failure in the
isolated experiment used `d5d54aaa-654b-435e-a480-26dd165bba76`. Logs may have
expired. Preserve only sanitized excerpts, never credentials or private audio.

## Likely failure point

The Wetlab error stack identified llm-d inference payload processor revision
`a8bbe6a6a75a`. Its [request handler](https://github.com/llm-d/llm-d-inference-payload-processor/blob/a8bbe6a6a75a/pkg/handlers/request.go)
decodes request bytes as JSON before calling request plugins. The upstream
[v1.0.0 handler](https://github.com/llm-d/llm-d-inference-payload-processor/blob/v1.0.0/pkg/handlers/request.go)
shows the same JSON-first behavior. This explains the observed failure but does
not establish what every newer Red Hat version ships or supports.

Ask the MaaS/AI Gateway and llm-d maintainers to confirm ownership and the
supported approach. A fix must preserve model identification, authentication,
authorization, quotas, identity-header protection, multipart boundaries and
file bytes through both stages. The earlier public issue/PR search was dated
and non-exhaustive; related research is preserved in the archived findings.

## Reproduce

These commands require the existing Wetlab services, an active authorized
`oc` session, the test MaaS subscription and running ASR workloads. Review and
adapt the scripts for another cluster. They create short-lived MaaS keys in
memory and generate a synthetic tone; no model weights or images are downloaded.

```sh
# Praxis → MaaS: last observed result was HTTP 400 and a parsing error.
python3 deploy/manifests/maas/wetlab-3.5/tests/check-qwen3-asr-praxis.py

# MaaS Gateway directly: isolates the same failure from Praxis.
python3 deploy/manifests/maas/wetlab-3.5/tests/check-qwen3-asr-praxis.py --direct

# Compare each model directly, bypassing Praxis, MaaS and EPP.
python3 deploy/manifests/maas/wetlab-3.5/tests/check-qwen3-asr-praxis.py --model-node 42
python3 deploy/manifests/maas/wetlab-3.5/tests/check-qwen3-asr-praxis.py --model-node 32
```

The direct-model checks use local port-forwards and do not verify model TLS
identity; they are diagnostics, not a production client configuration. In the
normal route the pre-processor fails first. The post-processor error was
observed only in the controlled experiment described above.

Relevant private context: [OCTOET-2328](https://redhat.atlassian.net/browse/OCTOET-2328)
and [RHAISTRAT-2891](https://redhat.atlassian.net/browse/RHAISTRAT-2891).
