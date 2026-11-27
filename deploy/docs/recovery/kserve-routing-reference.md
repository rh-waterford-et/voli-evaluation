# Wetlab routing settings observed on 12 November 2026

> Identifiers in this historical reference were sanitized for this public
> repository. Verify actual Gateway, EPP and pool configuration before use.

Reference for coordinating a rebuild with the owners of Gateway, Praxis and
EPP. These are selected non-secret observations, **not apply-ready manifests**
and not the owners' complete deployment source. Service accounts/RBAC, Istio
and Gateway controllers/policies, Praxis configuration, security and route
exposure are not captured here. Never copy the plaintext settings to another
environment without the platform owner's security review.

## InferencePool

```yaml
apiVersion: inference.networking.k8s.io/v1
kind: InferencePool
metadata:
  name: endpoint-picker
  namespace: model-serving
spec:
  appProtocol: http
  endpointPickerRef:
    failureMode: FailOpen
    group: ""
    kind: Service
    name: endpoint-picker-epp
    port:
      number: 9002
  selector:
    matchLabels:
      llm-d.ai/pool: qwen3-tts
  targetPorts:
    - number: 8000
```

## EPP

The `endpoint-picker-epp` Deployment uses ServiceAccount
`endpoint-picker-epp` and mounts ConfigMap `endpoint-picker-epp` at `/config`.
Its image reference was `quay.io/rh_et_wd/llm-d-router-endpoint-picker:new-approach`;
the running image ID was
`quay.io/rh_et_wd/llm-d-router-endpoint-picker@sha256:1be86297f2af55149f5c117d11f37ff6b0d85f983069ae93e064314560d25d00`.
The mutable tag is not a reproducible version pin. Its relevant arguments were:

```text
--pool-name endpoint-picker
--pool-namespace model-serving
--pool-group inference.networking.k8s.io
--config-file /config/tts.yaml
--grpc-health-port 9003
--secure-serving=false
--tracing=false
```

The EPP Service selector is `llm-d-router-gateway=endpoint-picker-epp`. It
exposes gRPC/h2c port 9002 and metrics port 9090. The Deployment's health port
is 9003. The active ConfigMap key `tts.yaml` contained:

```yaml
apiVersion: inference.networking.x-k8s.io/v1alpha1
kind: EndpointPickerConfig
plugins:
  - name: activeRequest
    type: active-request-scorer
  - name: maxScore
    type: max-score-picker
schedulingProfiles:
  - name: default
    plugins:
      - pluginRef: activeRequest
      - pluginRef: maxScore
dataLayer:
  injectDefaults: false
```

## Gateway route and TLS rule

The Gateway `inference-gateway` uses class `data-science-gateway-class` and a
port 80 HTTP listener. The HTTPRoute `endpoint-picker` attaches to the `http`
listener and has an InferencePool backend `endpoint-picker`. Its exact path
matches were `/v1/chat/completions`, `/v1/audio/speech` and
`/v1/audio/transcriptions`; its request timeout was 600 seconds. An OpenShift
Route named `demo-inference-gateway` provided edge TLS to the Gateway Service.

The existing DestinationRule selected plaintext for the EPP host:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: endpoint-picker-epp-plaintext
  namespace: model-serving
spec:
  host: endpoint-picker-epp.model-serving.svc.cluster.local
  trafficPolicy:
    tls:
      mode: DISABLE
```

Praxis is separately deployed as `praxis-ai-llmd`, listens on 8080, and loads
its configuration from ConfigMap `praxis-config`. Its image was
`quay.io/rh_et_wd/praxis-ai-llmd@sha256:53abcb85dcf5f95fc2f212eedf6fc6d7f114d57d727ed840894725fff8adef93`.
Obtain its authoritative configuration and security requirements from its
owner; do not treat this note as a full recreation package.
