#!/usr/bin/env python3
"""Exercise isolated Praxis -> MaaS -> KServe with an ephemeral in-memory key.

Defaults to expecting no model endpoints (503). Pass --expect-audio when the
model is running to require a WAV response. No key is printed or saved.
"""
import argparse
import http.client
import importlib.util
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location('maas_check', Path(__file__).with_name('check-bm003-auth.py'))
maas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maas)


def forward(namespace, target, target_port):
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    process = subprocess.Popen(
        ['oc', '-n', namespace, 'port-forward', target, f'{port}:{target_port}', '--address=127.0.0.1'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Port-forward failed for {target}')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return process, port
        except OSError:
            time.sleep(0.2)
    process.terminate()
    raise RuntimeError(f'Port-forward timed out for {target}')


def request_via_praxis(port, token):
    body = json.dumps({'model': 'bm-003', 'input': 'Hi.', 'voice': 'Vivian', 'response_format': 'wav'}).encode()
    headers = {'Host': maas.HOST, 'Content-Type': 'application/json', 'Connection': 'close'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=120)
    try:
        conn.request('POST', maas.PATH, body=body, headers=headers)
        response = conn.getresponse()
        return response.status, response.read(1048576)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-audio', action='store_true')
    args = parser.parse_args()
    ca = json.loads(maas.oc('get', 'configmap', 'default-ingress-cert', '-n', 'openshift-config-managed', '-o', 'json'))['data']['ca-bundle.crt']
    context = ssl.create_default_context(cadata=ca)
    token = maas.oc('whoami', '-t').strip()
    forwards = []
    try:
        process, maas_port = forward('openshift-ingress', 'service/maas-default-gateway-data-science-gateway-class', 443)
        forwards.append(process)
        process, praxis_port = forward('model-serving', 'service/praxis-maas', 8080)
        forwards.append(process)
        status, data = maas.request(maas_port, context, 'POST', '/maas-api/v1/api-keys', token,
                                    {'name': 'wetlab-praxis-maas-check', 'subscription': 'wetlab-bm003-test', 'ephemeral': True, 'expiresIn': '15m'})
        print(f'Temporary MaaS key creation: HTTP {status}')
        if status not in (200, 201):
            raise RuntimeError('Key creation failed; response withheld')
        key = json.loads(data).get('key')
        if not isinstance(key, str) or not key.startswith('sk-oai-'):
            raise RuntimeError('Key missing or unrecognized; response withheld')
        results = []
        for label, bearer in (('Anonymous', None), ('Invalid key', 'sk-oai-invalid-wetlab-test'), ('Test key', key)):
            status, data = request_via_praxis(praxis_port, bearer)
            print(f'{label} TTS via Praxis: HTTP {status}')
            if label == 'Test key' and status == 200:
                print(f'Audio response bytes read: {len(data)}; WAV header: {data[:4] == b"RIFF"}')
            results.append((status, data))
        if results[0][0] != 401 or results[1][0] not in (401, 403):
            raise RuntimeError('Unexpected unauthenticated or invalid-key behavior')
        expected = 200 if args.expect_audio else 503
        if results[2][0] != expected or (args.expect_audio and not results[2][1].startswith(b'RIFF')):
            raise RuntimeError(f'Expected valid-key HTTP {expected}'+(' with a WAV header' if args.expect_audio else ''))
    finally:
        for process in forwards:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ssl.SSLError, subprocess.TimeoutExpired, ValueError) as error:
        print(f'Praxis/MaaS test failed: {type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(1)
