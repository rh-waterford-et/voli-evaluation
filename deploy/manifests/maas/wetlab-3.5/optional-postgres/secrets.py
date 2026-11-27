#!/usr/bin/env python3
"""Create the Wetlab POC database Secrets without printing credentials.

Run only after reviewing namespace, endpoint and TLS settings. This does not
rotate an existing database password; restoring a DB requires its original
credentials. Never commit Kubernetes Secret values to version control.
"""

import base64
import json
import secrets
import subprocess
import sys
from urllib.parse import quote


def oc(*args, input_data=None):
    result = subprocess.run(
        ["oc", *args], input=input_data, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise RuntimeError("OpenShift command failed; check access and resource state")
    return result.stdout


def exists(namespace, name):
    return bool(oc("get", "secret", name, "-n", namespace, "-o", "name", "--ignore-not-found").strip())


def create_secret(namespace, name, values):
    if exists(namespace, name):
        raise RuntimeError(f"Secret {namespace}/{name} already exists; it was not changed")
    body = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": name, "namespace": namespace},
        "type": "Opaque",
        "stringData": values,
    }
    oc("create", "-f", "-", "-o", "name", input_data=json.dumps(body))
    print(f"Created Secret {namespace}/{name}")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"database", "maas"}:
        raise RuntimeError("Usage: python3 postgres-secrets.py database|maas")
    if sys.argv[1] == "database":
        create_secret(
            "model-serving", "maas-postgres-credentials",
            {"POSTGRES_USER": "maas", "POSTGRES_DB": "maas", "POSTGRES_PASSWORD": secrets.token_urlsafe(32)},
        )
        return

    raw = json.loads(oc("get", "secret", "maas-postgres-credentials", "-n", "model-serving", "-o", "json"))
    data = {key: base64.b64decode(value).decode() for key, value in raw["data"].items()}
    connection = (
        "postgresql://" + quote(data["POSTGRES_USER"], safe="") + ":"
        + quote(data["POSTGRES_PASSWORD"], safe="")
        + "@maas-postgres.model-serving.svc:5432/"
        + quote(data["POSTGRES_DB"], safe="") + "?sslmode=require"
    )
    create_secret("redhat-ai-gateway-infra", "maas-db-config", {"DB_CONNECTION_URL": connection})


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, KeyError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
