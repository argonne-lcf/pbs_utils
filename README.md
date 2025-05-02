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

All headers: `JobId`, `User`, `Account`, `Score`, `WallTime`, `QueuedTime`, `EstStart`, `RunTime`, `TimeRemaining`, `Nodes`, `State`, `Queue`, `JobName`, `Location/Comments`.

Note: view the displayed table with `less -S`.

### Examples
- Show jobs on a rack: `pbsq -f x4305 | less -S`
- Sort by queued time only: `pbsq -s QueuedTime,r | less -S`
- Select columns: `pbsq -H JobId:State:TimeRemaining:Nodes`
- Show past jobs by a user: `qstat -xfwu username | pbsq | less -S`
