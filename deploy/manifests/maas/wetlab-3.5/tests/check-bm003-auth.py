#!/usr/bin/env python3
"""Check MaaS discovery/auth using a short-lived key held only in memory.

The model may be scaled to zero: a non-2xx response to the authorized inference
request is then expected and does not by itself prove inference works.
No key is printed, written to disk, revoked, or reused outside this process.
"""
import http.client
import json
import socket
import ssl
import subprocess
import sys
import time

HOST = 'maas.apps.example.com'
PATH = '/model-serving/bm-003/v1/audio/speech'


def oc(*args):
    result = subprocess.run(['oc', *args], capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError('OpenShift command failed; check login and permissions')
    return result.stdout


def request(port, context, method, path, token=None, body=None):
    headers = {'Host': HOST, 'Connection': 'close'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if body is not None:
        body = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
        headers['Content-Length'] = str(len(body))
    connection = http.client.HTTPSConnection('127.0.0.1', port, timeout=120, context=context)
    # Hostname verification must use the gateway certificate's DNS name.
    raw = socket.create_connection(('127.0.0.1', port), timeout=10)
    connection.sock = context.wrap_socket(raw, server_hostname=HOST)
    connection.sock.settimeout(120)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        return response.status, response.read(1048576)
    finally:
        connection.close()


def main():
    ca = json.loads(oc('get', 'configmap', 'default-ingress-cert', '-n', 'openshift-config-managed', '-o', 'json'))['data']['ca-bundle.crt']
    token = oc('whoami', '-t').strip()
    context = ssl.create_default_context(cadata=ca)
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    forward = subprocess.Popen(
        ['oc', '-n', 'openshift-ingress', 'port-forward', 'service/maas-default-gateway-data-science-gateway-class', f'{port}:443', '--address=127.0.0.1'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if forward.poll() is not None:
                raise RuntimeError('Port-forward exited before becoming ready')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=1):
                    break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError('Port-forward did not become ready')
        status, data = request(port, context, 'POST', '/maas-api/v1/api-keys', token,
                               {'name': 'wetlab-bm003-integration-check', 'subscription': 'wetlab-bm003-test', 'ephemeral': True, 'expiresIn': '15m'})
        print(f'Temporary test key creation: HTTP {status}')
        if status not in (200, 201):
            raise RuntimeError('Key creation failed; response body withheld')
        payload = json.loads(data)
        key = payload.get('key')
        if not isinstance(key, str) or not key.startswith('sk-oai-'):
            raise RuntimeError('Key missing or unrecognized; response body withheld')
        if payload.get('expiresAt'):
            print(f'Test key expiration: {payload["expiresAt"]}')
        status, data = request(port, context, 'GET', '/v1/models', key)
        print(f'Test key model listing: HTTP {status}')
        if status == 200:
            models = json.loads(data).get('data', [])
            print('Model IDs: ' + ', '.join(str(item.get('id')) for item in models))
        body = {'model': 'bm-003', 'input': 'Hi.', 'voice': 'Vivian', 'response_format': 'wav'}
        for label, bearer in (('Anonymous', None), ('Invalid key', 'sk-oai-invalid-wetlab-test'), ('Test key', key)):
            result, response = request(port, context, 'POST', PATH, bearer, body)
            print(f'{label} TTS request: HTTP {result}')
            if label == 'Test key' and result == 200:
                print(f'Audio response bytes read: {len(response)}; WAV header: {response[:4] == b"RIFF"}')
    finally:
        forward.terminate()
        try:
            forward.wait(timeout=5)
        except subprocess.TimeoutExpired:
            forward.kill()
            forward.wait()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ssl.SSLError, subprocess.TimeoutExpired, ValueError) as error:
        print(f'MaaS check failed: {type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(1)
