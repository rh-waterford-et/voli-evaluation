# Multimodal Baseline Evaluation (3.7)

## Objective

Deliver a 3.7 reference deployment for end-to-end multimodal baseline
support. This includes RR baseline routing, Load Aware EPP, GW Praxis,
and Istio passthrough with Auth and BBR, with metering as a stretch
goal.

## Context

This epic is based on the referenced RHAISTRAT tickets and supporting
strategy documents. It focuses on making multimodal AI workloads work
as a coherent platform across voice, vision, audio, and omni-modality.
The linked work also notes that Praxis Auth and BBR are pending for the
3.7 deliverable.

Relevant links:

- [RHAISTRAT-2446][rhaistrat-2446]: Platform Multimodal Experience
- [RHAISTRAT-2999][rhaistrat-2999]: llm-d + Praxis passthrough
  with RR + Load Aware EPP

Reference documents:

- [Omni Modality North Star][omni-modality]
- [Modality Inference Feature Strategy][modality-strategy]

## Scope

### Included

- End-to-end baseline for:
  - Voice in → text out
  - Multimodal in → text out
  - Multimodal in → multimodal out
- End-to-end passthrough for llm-d
- Load-aware routing and minimal metrics support
- A spike for batch async support, focused on audio/image/video
  multimodal input and output
- Baseline performance work for 3.7 EA and follow-up work for 3.7 GA
  based on bottlenecks
- Multimodal reference deployment for MaaS

### Not included

- Full-blown flow control
- Full productization beyond the stated 3.7 deliverable
- Work outside the referenced multimodal and llm-d baseline effort

## Success criteria

- Multimodal reference deployment is available
- Load-aware routing works with minimal EPP metrics
- End-to-end passthrough is delivered for llm-d
- Batch async spike is explored for multimodal and large audio
  transcription
- Baseline performance is established for 3.7 EA
- Bottlenecks are identified for 3.7 GA follow-up work
- Best practices documentation or article is produced

## Risks and dependencies

- Praxis Auth and BBR are pending for the 3.7 deliverable
- Stretch metering work may depend on additional time or scope
- Baseline performance findings from 3.7 EA may require further work
  before 3.7 GA
- Progress depends on the referenced RHAISTRAT tickets and supporting
  strategy documents

## Other information

- RFE reference: [RHAIRFE-3817][rhairfe-3817]
- MaaS multimodal support reference: [RHAISTRAT-2891][rhaistrat-2891]

[rhaistrat-2446]: https://redhat.atlassian.net/browse/RHAISTRAT-2446
[rhaistrat-2999]: https://redhat.atlassian.net/browse/RHAISTRAT-2999
[omni-modality]: https://docs.google.com/document/d/1jAYrchZzza6I6nioLegMqGFDQUYW4_X-lGFRtDrIV18/edit?tab=t.15m0153auojc
[modality-strategy]: https://docs.google.com/document/d/17ZJSu4o1UxSvcNVEFvYzt4YMXwBHef8BE3O64KQ6EfI/edit?tab=t.8taasm6035rx#heading=h.t8a1hn56953j
[rhairfe-3817]: https://redhat.atlassian.net/browse/RHAIRFE-3817
[rhaistrat-2891]: https://redhat.atlassian.net/browse/RHAISTRAT-2891
