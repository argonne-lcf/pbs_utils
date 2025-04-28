# pbs_utils
Scripts to help make PBSPro useful to ALCF users.


## pu_nodeStat
Queries various status fields across all Aurora nodes, or all nodes in a specified "partition." The partitions are associated with general or specialized queues. Now that Aurora is in production, almost all nodes are in one partition, still named `lustre_scaling` for historical reasons. The `prod` routing queue, `prod-large` queue, and various `debug*` queues are in the `lustre_scaling` partition. If no partition is specified on the `pu_nodeStat` command line, it reports for all partitions.
Results are summarized in a table with each row showing the number of nodes in a specific status (`free`, `down`, etc.).

_Currently Aurora-only._

## pu-reservationList
Produces a table of reservations with more useful set of information than default available PBS commands. Displays results in a table  with user-friendly column headings such as "Reservation", "queue", "nodes", "start", and "end"

