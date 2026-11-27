#!/usr/bin/env python3
"""Test Praxis -> MaaS -> ASR with a small generated audio clip and ephemeral key."""
import argparse
import http.client
import importlib.util
import io
import json
import math
from pathlib import Path
import socket
import ssl
import struct
import sys
import wave

path = Path(__file__).with_name('check-praxis-maas.py')
spec = importlib.util.spec_from_file_location('praxis_check', path)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
maas = check.maas


def make_audio():
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b''.join(struct.pack('<h', int(1200 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(16000)))
    return stream.getvalue()


def request(port, token, context=None, model_direct=False, extra_headers=None):
    boundary = 'wetlab-asr-check-7fdc90'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nqwen3-asr\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="tone.wav"\r\n'
            'Content-Type: audio/wav\r\n\r\n').encode() + make_audio() + f'\r\n--{boundary}--\r\n'.encode()
    headers = {'Host': maas.HOST, 'Content-Type': 'multipart/form-data; boundary=' + boundary, 'Connection': 'close'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if extra_headers:
        headers.update(extra_headers)
    if context is None:
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=120)
    else:
        connection = http.client.HTTPSConnection('127.0.0.1', port, timeout=120, context=context)
        raw = socket.create_connection(('127.0.0.1', port), timeout=10)
        connection.sock = context.wrap_socket(raw, server_hostname=maas.HOST)
        connection.sock.settimeout(120)
    try:
        path = '/v1/audio/transcriptions' if model_direct else '/model-serving/qwen3-asr/v1/audio/transcriptions'
        connection.request('POST', path, body=body, headers=headers)
        response = connection.getresponse()
        return response.status, response.read(65536)
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--direct', action='store_true', help='Call MaaS Gateway directly instead of Praxis')
    parser.add_argument('--model-node', choices=('32', '42'), help='Test a model service directly, bypassing MaaS and Praxis')
    parser.add_argument('--guard-tests-only', action='store_true', help='Test denial cases before sending an authorized inference request')
    args = parser.parse_args()
    if args.model_node:
        name = 'kserve-maas-qwen3-asr' if args.model_node == '42' else 'kserve-maas-qwen3-asr-node32'
        process, port = check.forward('model-serving', 'service/' + name + '-kserve-workload-svc', 8000)
        try:
            # Diagnostic connection through a localhost-only port-forward, no credentials.
            status, body = request(port, None, ssl._create_unverified_context(), model_direct=True)
            print(f'Node {args.model_node} direct model: HTTP {status}; response: {body[:500].decode("utf-8", "replace")}')
            if status != 200 or not isinstance(json.loads(body).get('text'), str):
                raise RuntimeError('Direct model did not return a transcription response')
        finally:
            process.terminate()
            process.wait(timeout=5)
        return
    ca = json.loads(maas.oc('get', 'configmap', 'default-ingress-cert', '-n', 'openshift-config-managed', '-o', 'json'))['data']['ca-bundle.crt']
    context = ssl.create_default_context(cadata=ca)
    token = maas.oc('whoami', '-t').strip()
    forwards = []
    try:
        process, maas_port = check.forward('openshift-ingress', 'service/maas-default-gateway-data-science-gateway-class', 443)
        forwards.append(process)
        if args.direct:
            target_port = maas_port
        else:
            process, target_port = check.forward('model-serving', 'service/praxis-maas', 8080)
            forwards.append(process)
        status, data = maas.request(maas_port, context, 'POST', '/maas-api/v1/api-keys', token,
                                    {'name': 'wetlab-asr-praxis-check', 'subscription': 'wetlab-qwen3-asr-test', 'ephemeral': True, 'expiresIn': '15m'})
        print(f'Temporary MaaS key creation: HTTP {status}')
        if status not in (200, 201): raise RuntimeError('Key creation failed; response withheld')
        key = json.loads(data).get('key')
        if not isinstance(key, str) or not key.startswith('sk-oai-'): raise RuntimeError('Key missing; response withheld')
        if args.guard_tests_only:
            status, data = maas.request(maas_port, context, 'POST', '/maas-api/v1/api-keys', token,
                                        {'name': 'wetlab-asr-wrong-sub-check', 'subscription': 'wetlab-bm003-test', 'ephemeral': True, 'expiresIn': '15m'})
            if status not in (200, 201): raise RuntimeError('Wrong-model key creation failed')
            other_key = json.loads(data).get('key')
            if not isinstance(other_key, str) or not other_key.startswith('sk-oai-'): raise RuntimeError('Wrong-model key missing')
            for label, bearer, extra, allowed in (
                ('Anonymous', None, None, (401,)),
                ('Invalid key', 'sk-oai-invalid-wetlab-test', None, (401, 403)),
                ('Wrong model subscription', other_key, None, (403,)),
                ('Forged identity header', key, {'X-MaaS-Username': 'example-user'}, (403,)),
            ):
                status, _ = request(target_port, bearer, context if args.direct else None, extra_headers=extra)
                print(f'{label} multipart ASR: HTTP {status}')
                if status not in allowed: raise RuntimeError(f'{label} did not produce an expected denial')
            return
        results = []
        for label, bearer in (('Anonymous', None), ('Invalid key', 'sk-oai-invalid-wetlab-test'), ('Test key', key)):
            status, body = request(target_port, bearer, context if args.direct else None)
            print(f'{label} ASR via {"MaaS" if args.direct else "Praxis"}: HTTP {status}')
            if label == 'Test key':
                # No private input or credentials are included: this is a generated tone.
                print('Response:', body[:500].decode('utf-8', 'replace'))
            results.append((status, body))
        if results[0][0] != 401 or results[1][0] not in (401, 403): raise RuntimeError('Unexpected auth result')
        if results[2][0] != 200 or not isinstance(json.loads(results[2][1]).get('text'), str):
            raise RuntimeError('ASR did not return a successful transcription response')
    finally:
        for process in forwards:
            process.terminate()
            try: process.wait(timeout=5)
            except Exception:
                process.kill(); process.wait()


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print(f'ASR test failed: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
