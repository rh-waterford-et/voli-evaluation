#!/usr/bin/env python3
"""Export the public cluster ingress CA for a Praxis test ConfigMap.

The CA is public trust material, not the ingress private key. No credentials
are printed or saved. Regenerate on each cluster and when the CA rotates.
"""
import json
import pathlib
import subprocess
import tempfile

result = subprocess.run(
    ['oc', 'get', 'configmap', 'default-ingress-cert', '-n', 'openshift-config-managed', '-o', 'json'],
    capture_output=True, text=True, check=True, timeout=20,
)
cert = json.loads(result.stdout)['data']['ca-bundle.crt']
path = pathlib.Path(tempfile.gettempdir()) / 'wetlab-praxis-maas-ingress-ca.crt'
path.write_text(cert)
print(f'Wrote public ingress CA to {path}')
