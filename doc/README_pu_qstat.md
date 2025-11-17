# pu_qstat - PBS Jobs Viewer

A self-contained Python program that displays PBS (Portable Batch System) job information in a formatted table with advanced filtering, sorting, and routing queue support.

## Features

- **Comprehensive Job Display**: Shows job ID, user, state, queue, nodes, score, walltime, runtime, submission time, project, and custom columns
- **Advanced Filtering**: Filter by state, queue, user, project, or specific job IDs
- **Routing Queue Support**: Automatically expands routing queues (e.g., `prod` → `small`, `medium`, `large`, `tiny`)
- **Flexible Sorting**: Sort by any field including score, nodes, runtime, walltime, submission time
- **Custom Columns**: Add extra columns from any PBS job attribute
- **Self-Contained**: Minimal dependencies - uses only Python standard library modules
- **Error Handling**: Robust handling of malformed JSON, missing fields, and network issues

## Requirements

- Python 3.6 or higher
- PBS Pro system with `qstat` command available
- **No external Python packages required** (uses only standard library)

## Installation

No installation needed! The script is self-contained and can be run directly:

```bash
python pu_qstat.py [options]
```

### Making it Executable

For convenience, you can make the script executable and run it directly:

```bash
chmod +x pu_qstat.py
./pu_qstat.py [options]
```

### Creating a Symlink

To use the script from anywhere without typing the full path, create a symlink in your PATH:

```bash
# Create a symlink in your local bin directory
mkdir -p ~/bin
ln -s /full/path/to/pu_qstat.py ~/bin/pu_qstat

# Add ~/bin to your PATH (add this to ~/.bashrc or ~/.bash_profile)
export PATH="$HOME/bin:$PATH"

# Now you can run it from anywhere:
pu_qstat [options]
```

If using on Aurora/Polaris via `/home/zippy/pu_qstat`, it's already available and ready to use.

## Usage

### Basic Usage

Display all jobs (default shows Running, Queued, and Held jobs):
```bash
python pu_qstat.py
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--sort FIELD` | Sort by field: `score`, `state`, `nodes`, `user`, `queue`, `jobid`, `project`, `walltime`, `runtime`, `submitted` |
| `--reverse` | Sort in descending order (default: ascending) |
| `--state STATES` | Filter by job state(s). Use single letter (e.g., `R`) or multiple (e.g., `RQH`). Use `all` for all states. Default: `RQH` |
| `--queue QUEUE` | Filter by queue name (supports routing queues) |
| `--user USER` | Filter by username (partial match) |
| `--project PROJECT` | Filter by project name (partial match) |
| `--jobid JOBIDS` | Filter by comma-separated job IDs (e.g., `12345,67890`) |
| `--limit N` | Limit output to first N jobs |
| `--extraCols COLS` | Add custom columns (comma-separated, format: `field.path` or `field.path:DisplayName`) |

### Job States

- `Q` = Queued
- `R` = Running
- `H` = Held
- `W` = Waiting
- `T` = Transit
- `E` = Exiting
- `B` = Begun
- `S` = Suspended
- `C` = Completed
- `F` = Finished

Default filter: `RQH` (Running, Queued, Held)

## Examples

### Basic Queries

Show all running jobs:
```bash
python pu_qstat.py --state R
```

Show all jobs (not just RQH):
```bash
python pu_qstat.py --state all
```

Show your own jobs:
```bash
python pu_qstat.py --user $USER
```

Show specific job IDs:
```bash
python pu_qstat.py --jobid 12345,67890
```

### Sorting

Sort by number of nodes (largest first):
```bash
python pu_qstat.py --sort nodes --reverse --limit 10
```

Sort by job score (highest priority first):
```bash
python pu_qstat.py --sort score --reverse
```

Sort running jobs by elapsed runtime:
```bash
python pu_qstat.py --state R --sort runtime --reverse
```

Sort queued jobs by submission time (newest first):
```bash
python pu_qstat.py --state Q --sort submitted --reverse
```

### Advanced Filtering

Filter by queue (automatically includes routing destinations):
```bash
python pu_qstat.py --queue prod
# Shows jobs in prod routing queue AND its destinations (small, medium, large, tiny)
```

Filter by project:
```bash
python pu_qstat.py --project E3SM
```

Combine multiple filters:
```bash
python pu_qstat.py --user zippy --state R --queue large --sort runtime
```

### Custom Columns

Add project type column:
```bash
python pu_qstat.py --extraCols Resource_List.award_category:ProjType
```

Add multiple custom columns:
```bash
python pu_qstat.py --extraCols Resource_List.award_category:ProjType,Variable_List.PBS_O_HOST:Host
```

## Example Output

```
$ python pu_qstat.py --sort nodes --reverse --limit 10
Fetching PBS job information...
Received 65927317 characters from qstat
Found 10 jobs:
Job ID     :                 User :      State :                Queue :      Nodes :      Score :   Walltime :    Runtime :    Submitted :                  Project
4905472    :                 mmin :          H :       backfill-large :      10000 :       0.89 :   04:00:00 :         -- :  05/20 17:24 :               EnergyApps
8116200    :             anishtal :          Q :                large :       9216 :      51.58 :   01:00:00 :         -- :  10/30 12:55 :          Intel-Punchlist
8116201    :             anishtal :          Q :                large :       9216 :      51.58 :   01:00:00 :         -- :  10/30 12:55 :          Intel-Punchlist
8116202    :             anishtal :          Q :                large :       9216 :      51.58 :   01:00:00 :         -- :  10/30 12:55 :          Intel-Punchlist
7748835    :              knomura :          Q :                large :       8192 :  108739.04 :   24:00:00 :         -- :  10/05 21:08 :         QuantMatManufact
7748836    :              knomura :          Q :                large :       8192 :  108738.73 :   24:00:00 :         -- :  10/05 21:08 :         QuantMatManufact
7748837    :              knomura :          Q :                large :       8192 :  108738.63 :   24:00:00 :         -- :  10/05 21:08 :         QuantMatManufact
7748838    :              knomura :          Q :                large :       8192 :  108725.99 :   24:00:00 :         -- :  10/05 21:10 :         QuantMatManufact
7748839    :              knomura :          Q :                large :       8192 :  108725.89 :   24:00:00 :         -- :  10/05 21:10 :         QuantMatManufact
7748840    :              knomura :          Q :                large :       8192 :  108725.79 :   24:00:00 :         -- :  10/05 21:10 :         QuantMatManufact
```

## Features in Detail

### Routing Queue Expansion

The program dynamically detects routing queues in your PBS system using `qstat -Q`. When you filter by a routing queue, it automatically includes all destination queues.

Example: If `prod` routes to `small`, `medium`, `large`, and `tiny`, then:
```bash
python pu_qstat.py --queue prod
```
Will show jobs in all four destination queues.

### Time Calculations

- **Runtime**: For running jobs, shows elapsed time since start. For completed jobs, shows total runtime.
- **Walltime**: Shows requested walltime from job submission.
- **Submitted**: Shows submission date/time in compact format (MM/DD HH:MM).

### Job Scoring

The program retrieves the PBS job sort formula from the server and calculates job scores, which determine scheduling priority. Higher scores = higher priority.

## Error Handling

The program includes robust error handling for:
- Missing `qstat` command
- Malformed JSON responses from PBS (with automatic repair attempts)
- Network timeouts
- Missing job data fields
- Invalid filter values
- Formula evaluation errors

## Troubleshooting

1. **"qstat command not found"**: Ensure PBS is installed and `qstat` is in your PATH
2. **Permission errors**: Make sure you have permission to run `qstat` commands
3. **No jobs displayed**: Check your filter settings; default shows only RQH states
4. **Slow performance**: The program fetches all job data; on busy systems with thousands of jobs, this may take 10-30 seconds

## Technical Details

- Uses `qstat -t -x -f -F json` for job data
- Uses `qstat -B -f -F json` for server configuration
- Uses `qstat -Q -f -F json` for queue routing information
- Automatically repairs common PBS JSON formatting issues
- No external dependencies beyond Python standard library

## License

Copyright (C) 2025 Timothy J. Williams and Taylor Childers  
SPDX-License-Identifier: MIT
