#!/usr/bin/env python3
"""Send small authenticated JSON diagnostics and summarize chosen ASR pods.

These intentionally lack an audio file: model responses are expected to be
HTTP 400. This checks endpoint routing, not multipart ASR or load balancing.
The short-lived MaaS key is held in memory and is never printed.
"""
import http.client
import importlib.util
import json
from pathlib import Path
import ssl
import subprocess
import sys
import time
import uuid

spec = importlib.util.spec_from_file_location('praxis_check', Path(__file__).with_name('check-praxis-maas.py'))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
maas = check.maas


def main():
    ca = json.loads(maas.oc('get', 'configmap', 'default-ingress-cert', '-n', 'openshift-config-managed', '-o', 'json'))['data']['ca-bundle.crt']
    context = ssl.create_default_context(cadata=ca)
    token = maas.oc('whoami', '-t').strip()
    pod_info = json.loads(maas.oc('get', 'pods', '-n', 'model-serving', '-l',
                                  'evaluation.example.com/model=qwen3-asr,app.kubernetes.io/part-of=llminferenceservice,kserve.io/component=workload', '-o', 'json'))
    ips = {x['status']['podIP']: x['spec']['nodeName'] for x in pod_info['items'] if x['status'].get('podIP')}
    forwards = []
    try:
        proc, gateway = check.forward('openshift-ingress', 'service/maas-default-gateway-data-science-gateway-class', 443); forwards.append(proc)
        proc, praxis = check.forward('model-serving', 'service/praxis-maas', 8080); forwards.append(proc)
        status, data = maas.request(gateway, context, 'POST', '/maas-api/v1/api-keys', token,
                                    {'name': 'wetlab-asr-pool-check', 'subscription': 'wetlab-qwen3-asr-test', 'ephemeral': True, 'expiresIn': '15m'})
        if status not in (200, 201): raise RuntimeError(f'Key creation failed: HTTP {status}')
        key = json.loads(data).get('key')
        if not isinstance(key, str) or not key.startswith('sk-oai-'): raise RuntimeError('Key missing')
        ids = []
        for _ in range(8):
            request_id = str(uuid.uuid4()); ids.append(request_id)
            headers = {'Host': maas.HOST, 'Content-Type': 'application/json', 'Connection': 'close',
                       'Authorization': 'Bearer ' + key, 'X-Request-ID': request_id}
            conn = http.client.HTTPConnection('127.0.0.1', praxis, timeout=30)
            try:
                # Praxis can replace X-Request-ID, so include a non-secret
                # correlation ID in the query string retained in gateway logs.
                conn.request('POST', '/model-serving/qwen3-asr/v1/audio/transcriptions?wetlab_probe=' + request_id,
                             body=json.dumps({'model': 'qwen3-asr'}).encode(), headers=headers)
                response = conn.getresponse(); data = response.read(65536)
                if response.status != 400 or b'body.file' not in data:
                    raise RuntimeError(f'Unexpected diagnostic response: HTTP {response.status}')
            finally: conn.close()
        deadline = time.monotonic() + 10
        while True:
            result = subprocess.run(['oc', 'logs', '-n', 'openshift-ingress', '-l',
                                     'gateway.networking.k8s.io/gateway-name=maas-default-gateway',
                                     '--since=5m', '--tail=1000', '--request-timeout=10s'],
                                    capture_output=True, text=True, timeout=20, check=True)
            selected = {node: 0 for node in ips.values()}; unmatched = []
            for rid in ids:
                # The Gateway access log records the rewritten model path.
                lines = [line for line in result.stdout.splitlines() if rid in line and 'asr-maas-modelref-path' in line]
                matched = {node for line in lines for ip, node in ips.items() if ip + ':8000' in line}
                if len(matched) == 1: selected[matched.pop()] += 1
                else: unmatched.append(rid)
            if not unmatched or time.monotonic() >= deadline: break
            time.sleep(0.5)  # Gateway access-log writes can lag responses.
        print(f'Authenticated JSON diagnostics: {len(ids)} HTTP 400 responses, as expected without audio files')
        for node, count in sorted(selected.items()): print(f'{node}: {count} selected requests')
        print(f'Gateway log entries without one identifiable endpoint: {len(unmatched)}')
        if unmatched: raise RuntimeError('Could not correlate every diagnostic request')
    finally:
        for proc in forwards:
            proc.terminate(); proc.wait(timeout=5)


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(f'ASR pool test failed: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
