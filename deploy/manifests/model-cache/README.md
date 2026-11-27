# Model-cache storage examples

These sanitized examples show the static node-local StorageClass, PVs and PVCs
used in the Wetlab investigation. They do **not** contain model weights,
create directories on nodes, reserve physical disk capacity or configure
backups. A local PV is tied to a node. Adapt node labels, paths, namespaces,
capacity, permissions and storage choices with the destination cluster owner.

| File | Purpose |
| --- | --- |
| `00-storageclass.yaml` | Static local StorageClass example. |
| `10-local-pvs.yaml` | Node-specific PersistentVolume examples. |
| `20-pvcs.yaml` | Matching PersistentVolumeClaim examples. |

Stage approved model weights separately using the cluster owner's approved
process. These templates do not authorize or perform model downloads.
