# pbs_utils
Scripts to help make PBSPro useful to ALCF users.


## pu_nodeStat
Queries various status fields across all Aurora nodes, or all nodes in a specified "partition." The partitions are associated with general or specialized queues. Now that Aurora is in production, almost all nodes are in one partition, still named `lustre_scaling` for historical reasons. The `prod` routing queue, `prod-large` queue, and various `debug*` queues are in the `lustre_scaling` partition. If no partition is specified on the `pu_nodeStat` command line, it reports for all partitions.
Results are summarized in a table with each row showing the number of nodes in a specific status (`free`, `down`, etc.).

_Currently Aurora-only._

## pu-reservationList
Produces a table of reservations with more useful set of information than default available PBS commands. Displays results in a table  with user-friendly column headings such as "Reservation", "queue", "nodes", "start", and "end"


## `pbsn`: PBS Nodes Filter

`pbsn` filters and categorizes PBS nodes based on their states and attributes.

### Usage
```bash
pbsn [-h] [-q AT_QUEUE]
```

- `-h` : Display help information.
- `-q AT_QUEUE` : Filter nodes by `resources_available.at_queue`.

### Example Commands
- Filter by queue `lustre_scaling`: `pbsn -q lustre_scaling`
- Process some nodes with your own filter: `pbsnodes -a | your_filter_script | pbsn`

### Output
- **Summary:** Total nodes and counts by state (e.g., free, down, reserved).
- **Details:** Node-specific attributes (state, broken, validation, comment).


## `pbsq`: PBS Qstat Filter

`pbsq` filters, sorts, and formats PBS `qstat` job data.

### Usage
```bash
pbsq [-h] [-f FILTER] [-s HEADER1[,OPT]:HEADER2[,OPT]:..] [-H HEADER1:HEADER2:...]
```

- `-h`: Show help.
- `-f FILTER`: Filter jobs that matches the displayed lines. The filter is a regex supported by awk(1).
- `-s HEADER1[,OPT]:HEADER2[,OPT]:..`: Sort by headers (e.g., `TimeRemaining,r` for reverse). OPT is one or more single letter ordering options supported in sort(1). Headers not displayed are ignored.
- `-H HEADER1:HEADER2:...`: Display selected headers (e.g., `JobId:User:State`).

All headers: `JobId`, `User`, `Account`, `Score`, `WallTime`, `QueuedTime`, `EstStart`, `RunTime`, `TimeRemaining`, `Nodes`, `State`, `Queue`, `JobName`, `Location/Comments`, `WorkDir`.

Note: view the displayed table with `less -S`.

### Examples
- Show jobs on a rack: `pbsq -f x4305 | less -S`
- Sort by queued time only: `pbsq -s QueuedTime,r | less -S`
- Select columns: `pbsq -H JobId:State:TimeRemaining:Nodes`
- Show past jobs by a user: `qstat -xfwu username | pbsq | less -S`


# Python PBS Scripts

## Requirements-free Scripts

### pu_qstat.py

A self-contained Python program that displays PBS (Portable Batch System) job information in a formatted table with advanced filtering, sorting, and routing queue support. See [doc/README_pu_qstat.md](doc/README_pu_qstat.md) for more.

## Other Python Scripts

The user will need an evironment that provides a recent version of python and contains the requirements:
* tabulate
* pandas
* numpy
* chardet

### `pbs/` module
This module provides interfaces to running pbs commands and getting output via JSON format and is used to create the utility scripts below.

### `pbs_node_summary.py`
Run this script to print a summary of current node status. For Example:

```shell
+----------------+-------+
| Node State     | Count |
+----------------+-------+
| free           |  1661 |
| in-use         |  8802 |
| offline        |   122 |
| in-reservation |    38 |
| Total nodes    | 10624 |
+----------------+-------+
```

### `pbs_nodehour_summary.py`
Run this script to print a summary of the node-hours queued on the local system, sorted by largest to smallest. Organized by Project, can also organize by user. For Example:
```shell
+---------------------+------------+-----------+
| project             | node_hours | job_count |
+---------------------+------------+-----------+
| Project-A           |     203333 |         5 |
| Project-B           |        602 |         4 |
| Project-C           |         44 |        11 |
| Project-D           |         32 |         1 |
| Project-E           |          4 |         1 |
| Project-F           |          1 |         1 |
+---------------------+------------+-----------+
```

### `pbs_queue_summary.py`
Run this script to print a summary of the queues and how many node-hours or jobs are on each queue. For Example:
```shell
+---------------+--------------+---------------+-------------------+--------------------+--------------+---------------+
| queue         | Queued Count | Running Count | Queued Node Hours | Running Node Hours | Queued Nodes | Running Nodes |
+---------------+--------------+---------------+-------------------+--------------------+--------------+---------------+
| R4674464      |            0 |             3 |                 0 |                336 |            0 |            36 |
| R4775834      |            1 |             0 |                 1 |                  0 |            1 |             0 |
| backfill-tiny |            1 |             5 |               768 |               7776 |          256 |          1296 |
| debug         |            0 |            12 |                 0 |                 14 |            0 |            16 |
| debug-scaling |            0 |             2 |                 0 |                  3 |            0 |             3 |
| gpu_hack_prio |            0 |             1 |                 0 |                  1 |            0 |             1 |
| intel_maint   |            4 |             5 |               602 |                208 |           19 |            10 |
| large         |            5 |             0 |            203333 |                  0 |        50000 |             0 |
| medium        |            0 |             1 |                 0 |              24576 |            0 |          2048 |
| nre-priority  |            0 |            11 |                 0 |                266 |            0 |           138 |
| prod          |           13 |             0 |                80 |                  0 |           28 |             0 |
| small         |            0 |             3 |                 0 |              18528 |            0 |          2056 |
| tiny          |            0 |            48 |                 0 |              18600 |            0 |          3766 |
| validation    |            0 |             1 |                 0 |                  2 |            0 |             2 |
| Totals        |           24 |            92 |            204784 |              70310 |        50304 |          9372 |
+---------------+--------------+---------------+-------------------+--------------------+--------------+---------------+
```

### `pbs_top_jobs.py`
Run this script to print a summary of the top jobs by score in the queue. There are command line flags to filter based on job parameters. For Example:
```shell
+------------+-----------+-------+--------------+-----------------+------------------+---------------+-------+-----------+
|   Job ID   |   User    | State |    Queue     |    Job Name     |     Project      |  Award Type   | Nodes |   Score   |
+------------+-----------+-------+--------------+-----------------+------------------+---------------+-------+-----------+
|  4256058   |  user1    |   Q   |    large     |    apr-1-dbu    | QuantMatManufact |    INCITE     | 10000 | 2086336.2 |
|  4256086   |  user1    |   Q   |    large     |    dec-1-dbu    | QuantMatManufact |    INCITE     | 10000 | 2085696.7 |
|  4671183   |  user2    |   Q   |    large     |    submit.sh    | QuantMatManufact |    INCITE     | 10000 | 1131868.5 |
|  4671184   |  user2    |   Q   |    large     |    submit.sh    | QuantMatManufact |    INCITE     | 10000 | 1131867.4 |
|  4671185   |  user2    |   Q   |    large     |    submit.sh    | QuantMatManufact |    INCITE     | 10000 | 1131863.6 |
|  4349862   |  user3    |   H   | alcf_kmd_val |      STDIN      |   Intel-Aurora   | Discretionary |   1   |  1049.1   |
|  4683812   |  user4    |   Q   | intel_maint  |      STDIN      | Intel-Punchlist  | Discretionary |   1   |   246.6   |
|  4775256   |  user5    |   R   |    medium    | nekRS_G0p1_5000 |    RBC_Conv_2    |    INCITE     | 2048  |   79.0    |
| 4775047[0] |  user6    |   Q   |     prod     |       tst       |                  |    INCITE     |   1   |   56.8    |
| 4775047[1] |  user6    |   Q   |     prod     |       tst       |                  |    INCITE     |   1   |   56.8    |
+------------+-----------+-------+--------------+-----------------+------------------+---------------+-------+-----------+
```
