# Optional Wetlab PostgreSQL example

Use an approved existing PostgreSQL service where available. This is the
single-node Wetlab proof of concept, not a production database. It needs
adapted storage, UID/GID, SELinux permissions, namespaces, network policy,
image availability, certificates, backups and recovery. Its 20 GiB local PV
does not reserve or enforce physical capacity. Do not use a model-cache path.

For a new **empty** database, after reviewing and adapting the files:

```sh
oc create -f deploy/manifests/maas/wetlab-3.5/optional-postgres/storage.yaml
oc create -f deploy/manifests/maas/wetlab-3.5/optional-postgres/service-and-tls.yaml
oc get secret maas-postgres-tls -n model-serving -o name
python3 deploy/manifests/maas/wetlab-3.5/optional-postgres/secrets.py database
# Only when the namespace doesn't already exist:
oc create -f deploy/manifests/maas/wetlab-3.5/optional-postgres/maas-infra-namespace.yaml
python3 deploy/manifests/maas/wetlab-3.5/optional-postgres/secrets.py maas
oc create -f deploy/manifests/maas/wetlab-3.5/optional-postgres/deployment.yaml
oc get deployment,pods -n model-serving -l app=maas-postgres
```

The script creates credentials in Kubernetes without printing or saving the
values locally and refuses to replace existing Secrets. It is specific to the
Wetlab namespaces and service hostname. For an existing database, restore the
original database credentials and data rather than generate a new password.
Verify that the MaaS API can connect after enabling it.

The recorded MaaS connection used `sslmode=require`: it encrypts traffic but
does not verify server identity. The server was not configured to reject all
plaintext. Verify full certificate identity and the security model for the
target environment. The [original database notes](https://github.com/PoolPooer/wetlab-operations/blob/6146d2f/manifests/maas/wetlab-3.5/POSTGRESQL.md)
include historical TLS checks and limitations.
