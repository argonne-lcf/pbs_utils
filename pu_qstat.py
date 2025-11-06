#!/usr/bin/env python3
# Copyright (C) 2025 Timothy J. Williams and Taylor Childers
# SPDX-License-Identifier: MIT
"""
Self-contained PBS Jobs Viewer

This program displays jobs in a PBS Pro system such as Aurora or Polaris, with options for 
filtering and sorting. It uses as few module dependencies as possible, so a non-Python user
can use it with only the system-default modules loaded.

Usage:
    python pbs_jobs_viewer.py [options]

Options:
    --sort FIELD     Sort by field (score, state, nodes, user, queue, jobid, project)
    --reverse        Sort in descending order (default: ascending)
    --state STATES   Filter by job state(s) (e.g., R, RQC, QF)
    --queue QUEUE    Filter by queue name
    --user USER      Filter by username
    --project PROJECT Filter by project name
    --limit N        Limit output to N jobs
    --extraCols COLS Comma-separated list of extra columns to include
    --help           Show this help message

Requirements:
    - PBS system with qstat command available
    - See also doc/README_pu_qstat.md for more information
"""

import subprocess as sp
import json
import logging
import re
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# PBS time parsing without dateutil
PBS_TIME_FORMATS = [
    "%a %b %d %H:%M:%S %Y",       # Fri Nov 10 11:34:29 2023
    "%a %b %d %H:%M:%S %Z %Y",   # Fri Nov 10 11:34:29 UTC 2023 (if TZ present)
]

def parse_pbs_time(timestr: str) -> datetime:
    if not timestr:
        raise ValueError("Empty time string")
    for fmt in PBS_TIME_FORMATS:
        try:
            return datetime.strptime(timestr, fmt)
        except ValueError:
            pass
    # Fallback: unix epoch seconds as string
    try:
        return datetime.fromtimestamp(int(timestr))
    except Exception as e:
        raise ValueError(f"Unrecognized PBS time format: {timestr}") from e

# PBS Job State Mapping
JOB_STATE_MAP = {
    "Q": "Queued",
    "R": "Running",
    "H": "Held",
    "W": "Waiting",
    "T": "Transit",
    "E": "Exiting",
    "B": "Begun",
    "S": "Suspended",
    "C": "Completed",
    "F": "Finished",
}

# Award category mapping
AWARD_CATEGORY_MAP = {
    'INCITE': 'INCITE',
    'ALCC': 'ALCC', 
    'Discretionary': 'DD'
}

def get_full_state_name(state_code):
    """Convert a single-letter PBS job state code to its full name."""
    return JOB_STATE_MAP.get(state_code, "Unknown")

def get_state_code(full_state_name):
    """Convert a full PBS job state name to its single-letter code."""
    for code, name in JOB_STATE_MAP.items():
        if name.lower() == full_state_name.lower():
            return code
    return "Unknown"

def repair_qstat_json(json_text):
    """
    Attempts to repair malformed JSON output from PBS qstat -F json using a state machine.
    
    Args:
        json_text (str): Raw JSON text from qstat command
    
    Returns:
        str: Repaired JSON text
    """
    lines = json_text.split('\n')
    repaired_lines = []
    fix_count = 0
    
    # State machine states
    OUTSIDE_JOBS = 0
    INSIDE_JOBS = 1
    INSIDE_JOB = 2
    
    state = OUTSIDE_JOBS
    job_brace_level = 0  # Track braces within current job
    
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        
        # Detect start of Jobs dict
        if re.match(r'^"Jobs"\s*:\s*{', stripped_line):
            state = INSIDE_JOBS
            job_brace_level = 0
            repaired_lines.append(line)
            continue
        
        # Detect end of Jobs dict
        if state == INSIDE_JOBS and stripped_line == '}':
            state = OUTSIDE_JOBS
            repaired_lines.append(line)
            continue
        
        # Detect start of a new job entry
        if state == INSIDE_JOBS and re.match(r'^"[0-9]+\.', stripped_line):
            # If we were inside a job and it wasn't properly closed, add closing brace
            if state == INSIDE_JOB and job_brace_level > 0:
                repaired_lines.append('        },')
                fix_count += 1
            
            # Start new job
            state = INSIDE_JOB
            job_brace_level = 0
            repaired_lines.append(line)
            continue
        
        # Count braces within current job
        if state == INSIDE_JOB:
            job_brace_level += line.count('{') - line.count('}')
            
            # If job is properly closed (brace level = 0), check if we need a comma
            if job_brace_level == 0:
                # Look ahead to see if there's another job entry
                next_job_found = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if re.match(r'^\s*"[0-9]+\.', lines[j].strip()):
                        next_job_found = True
                        break
                    elif lines[j].strip() == '}':  # End of Jobs dict
                        break
                
                # If there's a next job and current line doesn't end with comma, add it
                if next_job_found and not re.search(r',\s*$', line):
                    repaired_lines.append(line.rstrip() + ',')
                    fix_count += 1
                else:
                    repaired_lines.append(line)
                
                state = INSIDE_JOBS
                continue
        
        repaired_lines.append(line)
    
    if fix_count > 0:
        logger.info(f"Applied {fix_count} JSON repairs to qstat output")
    
    repaired_text = '\n'.join(repaired_lines)
    
    # Additional fixes for common JSON issues
    # Fix missing quotes around string values (like commit hashes, IDs, etc.)
    repaired_text = re.sub(r':([0-9a-f]{32,})', r':"\1"', repaired_text)  # Long hex strings
    repaired_text = re.sub(r':([0-9]{10,})', r':"\1"', repaired_text)     # Long numeric strings
    
    # Fix trailing commas before closing braces
    repaired_text = re.sub(r',(\s*[}\]])', r'\1', repaired_text)
    
    return repaired_text

def qstat_server(exec_path='/opt/pbs/bin/qstat',
                 args=['-x','-B','-f','-F','json']) -> dict:
    """
    Retrieves PBS server information in JSON format.
    
    Args:
        exec_path (str): Path to qstat executable
        args (list): Command line arguments for qstat
    
    Returns:
        dict: JSON formatted server information
    
    Raises:
        Exception: If qstat command fails
    """
    try:
        cmd = exec_path + ' ' + ' '.join(args)
        completed_process = sp.run(cmd.split(' '), stdout=sp.PIPE, stderr=sp.PIPE, timeout=30)
        if completed_process.returncode != 0:
            raise Exception(completed_process.stderr.decode('utf-8'))
        return json.loads(completed_process.stdout.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse server JSON: {e}")
        return {"Server": {}}
    except sp.TimeoutExpired:
        logger.warning("qstat server command timed out")
        return {"Server": {}}

def qstat_jobs(exec_path='/opt/pbs/bin/qstat',
               args=['-t','-x','-f','-F','json']) -> dict:
    """
    Retrieves information about PBS jobs in JSON format.
    
    Args:
        exec_path (str): Path to qstat executable
        args (list): Command line arguments for qstat
    
    Returns:
        dict: JSON formatted job information
    
    Raises:
        Exception: If qstat command fails
    """
    try:
        cmd = exec_path + ' ' + ' '.join(args)
        completed_process = sp.run(cmd.split(' '), stdout=sp.PIPE, stderr=sp.PIPE, timeout=60)
        if completed_process.returncode != 0:
            raise Exception(completed_process.stderr.decode('utf-8'))
        
        output = completed_process.stdout.decode('utf-8')
        logger.info(f"Received {len(output)} characters from qstat")
        
        # Try to parse JSON
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            logger.info("Attempting to repair malformed JSON...")
            
            # Apply JSON repair
            repaired_output = repair_qstat_json(output)
            
            try:
                return json.loads(repaired_output)
            except json.JSONDecodeError as e2:
                logger.warning(f"JSON repair failed: {e2}")
                
                # Debug: Show the problematic area
                try:
                    error_line = int(str(e2).split('line ')[1].split()[0])
                    error_col = int(str(e2).split('column ')[1].split()[0])
                    logger.info(f"Error at line {error_line}, column {error_col}")
                    
                    # Show context around the error
                    repaired_lines = repaired_output.split('\n')
                    start_line = max(0, error_line - 3)
                    end_line = min(len(repaired_lines), error_line + 2)
                    
                    logger.info("Context around error:")
                    for i in range(start_line, end_line):
                        marker = ">>> " if i == error_line - 1 else "    "
                        logger.info(f"{marker}{i+1:5d}: {repaired_lines[i]}")
                        
                except:
                    pass
                
                logger.info("Attempting to extract job count from raw output...")
                
                # Fallback: try to get basic job information
                return {"Jobs": {}, "error": "JSON parsing failed even after repair"}
            
    except sp.TimeoutExpired:
        logger.error("qstat command timed out")
        return {"Jobs": {}, "error": "Command timeout"}

def qstat_queues(exec_path='/opt/pbs/bin/qstat',
                 args=['-Q','-f','-F','json']) -> dict:
    """
    Retrieves PBS queue information in JSON format.
    
    Returns a dictionary as parsed from qstat JSON, or an empty structure on error.
    """
    try:
        cmd = exec_path + ' ' + ' '.join(args)
        completed_process = sp.run(cmd.split(' '), stdout=sp.PIPE, stderr=sp.PIPE, timeout=30)
        if completed_process.returncode != 0:
            raise Exception(completed_process.stderr.decode('utf-8'))
        return json.loads(completed_process.stdout.decode('utf-8'))
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to get/parse queue JSON: {e}")
        return {"Queue": {}}
    except sp.TimeoutExpired:
        logger.warning("qstat queues command timed out")
        return {"Queue": {}}

def build_routing_map(queues_data: dict) -> dict:
    """
    Build a routing map of routing queues to their destination queues.
    
    Returns a dict: routing_queue_name -> list of destination queue names.
    """
    routing_map = {}
    queues = queues_data.get('Queue', {}) or {}
    for qname, qinfo in queues.items():
        # Normalize to plain name (strip any server suffix if present in data)
        name = qname.split('@')[0]
        qtype = (qinfo.get('queue_type') or qinfo.get('queue_type[]') or '').strip()
        # Routing queues usually have queue_type == 'Route'
        if qtype.lower() == 'route':
            # route_destinations might be a comma-separated string or list
            dests = qinfo.get('route_destinations')
            if isinstance(dests, str):
                dest_list = [d.strip().split('@')[0] for d in dests.split(',') if d.strip()]
            elif isinstance(dests, list):
                dest_list = [str(d).strip().split('@')[0] for d in dests if str(d).strip()]
            else:
                dest_list = []
            routing_map[name] = dest_list
    return routing_map

def expand_routed_queues(root_queue: str, routing_map: dict) -> set:
    """
    Return a set of queues including root_queue and all transitive destinations if it is a routing queue.
    """
    root = (root_queue or '').split('@')[0].lower()
    if not root:
        return set()
    # Build lowercase map
    lower_map = {k.lower(): [d.lower() for d in v] for k, v in routing_map.items()}
    visited = set()
    stack = [root]
    while stack:
        q = stack.pop()
        if q in visited:
            continue
        visited.add(q)
        for nxt in lower_map.get(q, []):
            if nxt not in visited:
                stack.append(nxt)
    return visited

def get_integers(stringtime):
    """Converts time string in HH:MM:SS format to integers."""
    hr, min, sec = stringtime.split(':')
    hr, min, sec = int(hr), int(min), int(sec)
    return hr, min, sec

def string_time_to_seconds(stringtime):
    """Converts time string to total seconds."""
    hr, min, sec = get_integers(stringtime)
    return hr * 60 * 60 + min * 60 + sec

def string_time_to_minutes(stringtime):
    """Converts time string to total minutes."""
    hr, min, sec = get_integers(stringtime)
    return hr * 60 + min

def string_time_to_hours(stringtime):
    """Converts time string to total hours as a float."""
    hr, min, sec = get_integers(stringtime)
    return float(hr) + float(min)/60. + float(sec/60./60.)

def format_time_display(time_str):
    """Format time string for display (HH:MM:SS)."""
    if not time_str or time_str == '0:0:0':
        return '--'
    return time_str

def format_datetime_compact(datetime_str):
    """
    Format any datetime string in compact MM/DD HH:MM format.
    
    Args:
        datetime_str (str): A datetime string in PBS format or other recognizable format
        
    Returns:
        str: Formatted datetime as MM/DD HH:MM, or '--' if invalid
    """
    if not datetime_str or datetime_str == '--':
        return '--'
    try:
        # Parse the PBS time format without dateutil
        dt = parse_pbs_time(datetime_str)
        # Format as MM/DD HH:MM for compact display (24-hour format)
        return dt.strftime('%m/%d %H:%M')
    except Exception:
        # If parsing fails, return the original string truncated
        return datetime_str[:15] if len(datetime_str) > 15 else datetime_str

def format_submitted_time(qtime_str):
    """Format submitted time (qtime) for display."""
    return format_datetime_compact(qtime_str)

def calculate_elapsed_runtime(job):
    """
    Calculate elapsed runtime for a job.
    
    Args:
        job (dict): Job information dictionary
    
    Returns:
        str: Formatted runtime string or '--' for queued jobs
    """
    state = job.get('job_state', '')
    
    # For queued jobs, no runtime yet
    if state == 'Q':
        return '--'
    
    try:
        stime = job.get('stime', '')
        if not stime:
            return '--'
        
        # Parse start time
        start_time = parse_pbs_time(stime)
        
        if state == 'R':
            # For running jobs, calculate time since start
            current_time = datetime.now()
            elapsed = current_time - start_time
        else:
            # For completed jobs, use obittime if available
            obittime = job.get('obittime', '')
            if not obittime:
                return '--'
            end_time = parse_pbs_time(obittime)
            elapsed = end_time - start_time
        
        # Convert to HH:MM:SS format
        total_seconds = int(elapsed.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    except (ValueError, TypeError, AttributeError):
        return '--'

def execute_job_sort_formula(server_data: dict, job_data: dict) -> float:
    """
    Calculates job score using the PBS job sort formula.
    
    Args:
        server_data (dict): Server information from qstat_server()
        job_data (dict): Job information
    
    Returns:
        float: Calculated job score
    """
    try:
        server_dict = server_data.get('Server', {})
        if not server_dict:
            return 0.0
            
        first_server = server_dict[list(server_dict.keys())[0]]
        formula_str = first_server.get('job_sort_formula', '0')
        
        rl = job_data.get('Resource_List', {})
        base_score        = float(rl.get('base_score', 0))
        score_boost       = float(rl.get('score_boost', 0))
        enable_wfp        = float(rl.get('enable_wfp', 0))
        wfp_factor        = float(rl.get('wfp_factor', 0))
        eligible_time     = float(string_time_to_seconds(job_data.get('eligible_time', '0:0:0')))
        walltime          = float(string_time_to_seconds(rl.get('walltime', '0:0:0')))
        project_priority  = float(rl.get('project_priority', 0))
        nodect            = float(rl.get('nodect', 0))
        total_cpus        = float(rl.get('total_cpus', 0))
        enable_backfill   = float(rl.get('enable_backfill', 0))
        backfill_max      = float(rl.get('backfill_max', 0))
        backfill_factor   = float(rl.get('backfill_factor', 0))
        enable_fifo       = float(rl.get('enable_fifo', 0))
        fifo_factor       = float(rl.get('fifo_factor', 0))

        return eval(formula_str)
    except (KeyError, ValueError, TypeError, ZeroDivisionError, IndexError) as e:
        # Return a default score if formula evaluation fails
        return 0.0

def get_award_category_display(award_category):
    """
    Convert award category to display format.
    
    Args:
        award_category (str): Raw award category from PBS
        
    Returns:
        str: Display format for award category
    """
    if not award_category:
        return '--'
    return AWARD_CATEGORY_MAP.get(award_category, award_category)

def detect_value_type(value):
    """
    Detect the type of a value for intelligent sorting.
    
    Args:
        value: The value to analyze
        
    Returns:
        str: Type identifier ('time', 'datetime', 'numeric', 'string')
    """
    if value is None or value == '--' or value == '':
        return 'empty'
    
    str_value = str(value).strip()
    
    # Check for HH:MM:SS time format
    if re.match(r'^\d+:\d{2}:\d{2}$', str_value):
        return 'time'
    
    # Check for PBS datetime formats
    for fmt in PBS_TIME_FORMATS:
        try:
            parse_pbs_time(str_value)
            return 'datetime'
        except (ValueError, TypeError):
            continue
    
    # Check for MM/DD HH:MM format (from format_submitted_time)
    if re.match(r'^\d{2}/\d{2}\s+\d{2}:\d{2}$', str_value):
        return 'submitted_time'
    
    # Check for numeric (int or float)
    try:
        float(str_value)
        return 'numeric'
    except (ValueError, TypeError):
        pass
    
    return 'string'

def convert_value_for_sorting(value, value_type=None, reverse=False):
    """
    Convert a value to a sortable form based on its detected type.
    
    Rows with empty/missing values are automatically sorted to the end,
    regardless of sort direction.
    
    Args:
        value: The value to convert
        value_type (str, optional): Pre-detected type, or None to auto-detect
        reverse (bool): Whether the sort is in reverse order
        
    Returns:
        Comparable value for sorting (tuple where first element indicates validity)
    """
    if value_type is None:
        value_type = detect_value_type(value)
    
    # Determine the validity flag based on sort direction
    # For ascending (reverse=False): valid=0, empty=1 (empty sorts last)
    # For descending (reverse=True): valid=1, empty=0 (when reversed, empty still sorts last)
    valid_flag = 1 if reverse else 0
    empty_flag = 0 if reverse else 1
    
    if value_type == 'empty':
        # Return appropriate flag so empty fields always sort last
        return (empty_flag, 0)
    
    str_value = str(value).strip()
    
    try:
        if value_type == 'time':
            # Convert HH:MM:SS to seconds
            return (valid_flag, string_time_to_seconds(str_value))
        elif value_type == 'datetime':
            # Parse as PBS datetime
            dt = parse_pbs_time(str_value)
            return (valid_flag, dt.timestamp())
        elif value_type == 'submitted_time':
            # Parse MM/DD HH:MM format
            current_year = datetime.now().year
            dt = datetime.strptime(f"{current_year} {str_value}", "%Y %m/%d %H:%M")
            return (valid_flag, dt.timestamp())
        elif value_type == 'numeric':
            return (valid_flag, float(str_value))
        else:  # 'string'
            return (valid_flag, str_value.lower())
    except (ValueError, TypeError, AttributeError):
        # If conversion fails, treat as empty (sort to end)
        return (empty_flag, 0)

def extract_extra_column_value(job, column_spec):
    """
    Extract value for an extra column based on column specification.
    
    Args:
        job (dict): Job data dictionary
        column_spec (str): Column specification in format 'path.to.field' or 'path.to.field:display_name'
        
    Returns:
        tuple: (column_name, column_value)
    """
    # Parse column specification
    if ':' in column_spec:
        field_path, display_name = column_spec.split(':', 1)
    else:
        field_path = column_spec
        # Generate display name from field path
        display_name = field_path.split('.')[-1]
    
    # Navigate through nested dictionary
    value = job
    for key in field_path.split('.'):
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            value = '--'
            break
    
    # If final value is still a dict, it means the path was incomplete
    # Convert to a string representation or mark as invalid
    if isinstance(value, dict):
        # Check if it's a non-empty dict that should have been navigated further
        if value and value != {}:
            logger.warning(f"Column '{column_spec}': path '{field_path}' points to a dict with keys: {list(value.keys())[:5]}. Did you mean to access a sub-field?")
        value = '--'
    
    # Apply special transformations
    if field_path == 'Resource_List.award_category':
        value = get_award_category_display(value)
    
    # Auto-format datetime values in compact format
    if value and value != '--':
        value_type = detect_value_type(value)
        if value_type == 'datetime':
            value = format_datetime_compact(value)
    
    return display_name, value

def get_extra_columns_data(job, extra_columns):
    """
    Extract data for all extra columns for a job.
    
    Args:
        job (dict): Job data dictionary
        extra_columns (list): List of column specifications
        
    Returns:
        dict: Dictionary mapping column names to values
    """
    extra_data = {}
    for column_spec in extra_columns:
        try:
            column_name, column_value = extract_extra_column_value(job, column_spec)
            extra_data[column_name] = column_value
        except Exception as e:
            logger.warning(f"Error extracting column {column_spec}: {e}")
            extra_data[column_name] = '--'
    return extra_data

def print_jobs(job_data: dict, server_data: dict = None, 
               sort_by: str = None, reverse: bool = False,
               state_filter: str = None, queue_filter: str = None, 
               user_filter: str = None, project_filter: str = None, 
               jobid_filter: str = None, limit: int = None,
               extra_columns: list = None) -> None:
    """
    Prints a simple summary of jobs showing ID, user, state, queue, nodes, score, project, walltime, runtime, and submitted time.
    
    Args:
        job_data (dict): Job information from qstat_jobs()
        server_data (dict, optional): Server information from qstat_server()
        sort_by (str, optional): Field to sort by (score, state, nodes, user, queue, jobid, project, walltime, runtime, submitted)
        reverse (bool): Sort in descending order if True
        state_filter (str, optional): Filter by job state
        queue_filter (str, optional): Filter by queue name
        user_filter (str, optional): Filter by username
        project_filter (str, optional): Filter by project name
        jobid_filter (str, optional): Filter by comma-separated job IDs
        limit (int, optional): Limit output to N jobs
        extra_columns (list, optional): List of extra column specifications to include
    """
    if server_data is None:
        try:
            server_data = qstat_server()
        except Exception as e:
            logger.warning(f"Could not get server data: {e}")
            server_data = {}
    
    jobs = job_data.get('Jobs', {})
    if not jobs:
        logger.info("No jobs found in the PBS system.")
        return
    
    # Prepare routing-aware queue filter (expand routing queues dynamically once)
    expanded_queue_set = None
    if queue_filter:
        try:
            queues_data = qstat_queues()
            routing_map = build_routing_map(queues_data)
            expanded = expand_routed_queues(queue_filter, routing_map)
            if expanded:
                expanded_queue_set = expanded
        except Exception:
            expanded_queue_set = None

    # Parse jobid filter into a set for efficient lookup
    jobid_set = None
    if jobid_filter:
        jobid_set = set(jid.strip() for jid in jobid_filter.split(',') if jid.strip())

    # Convert jobs to list for sorting and filtering
    job_list = []
    for jobid, job in jobs.items():
        try:
            score = execute_job_sort_formula(server_data, job)
            jobid_short = jobid.split('.')[0]
            user = job.get('Variable_List', {}).get('PBS_O_LOGNAME', 'Unknown')
            state = job.get('job_state', 'Unknown')
            queue = job.get('queue', 'Unknown')
            nodes = job.get('Resource_List', {}).get('nodect', 0)
            project = job.get('project', 'Unknown')
            walltime = format_time_display(job.get('Resource_List', {}).get('walltime', '--'))
            runtime = calculate_elapsed_runtime(job)
            submitted = format_submitted_time(job.get('qtime', ''))
            
            # Apply filters
            if jobid_set and jobid_short not in jobid_set:
                continue
            if state_filter and state_filter.lower() != 'all':
                # Parse state filter - can be single state or multiple states
                valid_states = set(state_filter.upper())
                if state not in valid_states:
                    continue
            if queue_filter:
                if expanded_queue_set is not None:
                    if queue.lower() not in expanded_queue_set:
                        continue
                else:
                    if queue_filter.lower() not in queue.lower():
                        continue
            if user_filter and user_filter.lower() not in user.lower():
                continue
            if project_filter and project_filter.lower() not in project.lower():
                continue
            
            job_dict = {
                'jobid': jobid_short,
                'user': user,
                'state': state,
                'queue': queue,
                'nodes': nodes,
                'score': score,
                'project': project,
                'walltime': walltime,
                'runtime': runtime,
                'submitted': submitted
            }
            
            # Add extra columns if specified
            if extra_columns:
                extra_data = get_extra_columns_data(job, extra_columns)
                job_dict.update(extra_data)
            
            job_list.append(job_dict)
        except Exception as e:
            logger.warning(f"Error processing job {jobid}: {e}")
    
    # Sort jobs
    if sort_by:
        reverse_order = reverse
        
        # Check if it's an extra column
        extra_column_names = []
        if extra_columns:
            for column_spec in extra_columns:
                if ':' in column_spec:
                    _, display_name = column_spec.split(':', 1)
                else:
                    display_name = column_spec.split('.')[-1]
                extra_column_names.append(display_name)
        
        if sort_by in extra_column_names:
            # Sort by extra column using intelligent type detection
            job_list.sort(key=lambda x: convert_value_for_sorting(x.get(sort_by, '--'), reverse=reverse_order), reverse=reverse_order)
        elif sort_by == 'score':
            job_list.sort(key=lambda x: x['score'], reverse=reverse_order)
        elif sort_by == 'state':
            job_list.sort(key=lambda x: x['state'], reverse=reverse_order)
        elif sort_by == 'nodes':
            job_list.sort(key=lambda x: x['nodes'], reverse=reverse_order)
        elif sort_by == 'user':
            job_list.sort(key=lambda x: x['user'].lower(), reverse=reverse_order)
        elif sort_by == 'queue':
            job_list.sort(key=lambda x: x['queue'].lower(), reverse=reverse_order)
        elif sort_by == 'project':
            job_list.sort(key=lambda x: x['project'].lower(), reverse=reverse_order)
        elif sort_by == 'jobid':
            job_list.sort(key=lambda x: int(x['jobid']), reverse=reverse_order)
        elif sort_by == 'walltime':
            # Use intelligent type-aware sorting
            job_list.sort(key=lambda x: convert_value_for_sorting(x['walltime'], reverse=reverse_order), reverse=reverse_order)
        elif sort_by == 'runtime':
            # Use intelligent type-aware sorting
            job_list.sort(key=lambda x: convert_value_for_sorting(x['runtime'], reverse=reverse_order), reverse=reverse_order)
        elif sort_by == 'submitted':
            # Use intelligent type-aware sorting
            job_list.sort(key=lambda x: convert_value_for_sorting(x['submitted'], reverse=reverse_order), reverse=reverse_order)
        else:
            logger.warning(f"Unknown sort field: {sort_by}. Using default order.")
    
    # Apply limit
    if limit and limit > 0:
        job_list = job_list[:limit]
    
    if not job_list:
        logger.info("No jobs match the specified filters.")
        return
    
    # Build header and format string dynamically
    base_columns = ['Job ID', 'User', 'State', 'Queue', 'Nodes', 'Score', 'Walltime', 'Runtime', 'Submitted']
    extra_column_names = []
    
    if extra_columns:
        for column_spec in extra_columns:
            if ':' in column_spec:
                _, display_name = column_spec.split(':', 1)
            else:
                display_name = column_spec.split('.')[-1]
            extra_column_names.append(display_name)
    
    # Column order: base columns, Project (fixed width), then extra columns at the far right
    all_columns = base_columns + ['Project'] + extra_column_names
    
    # Build format string
    format_parts = []
    format_parts.append("{jobid:<10s}")
    format_parts.append("{user:>14s}")
    format_parts.append("{state:>10s}")
    format_parts.append("{queue:>20s}")
    format_parts.append("{nodes:>10d}")
    format_parts.append("{score:10.2f}")
    format_parts.append("{walltime:>10s}")
    format_parts.append("{runtime:>10s}")
    format_parts.append("{submitted:>12s}")
    format_parts.append("{project:>24s}")  # Fixed width project column
    for col_name in extra_column_names:
        format_parts.append(f"{{{col_name}:>15s}}")  # Extra columns get slightly wider width
    format_string = " : ".join(format_parts)
    
    # Build header string
    header_parts = []
    header_parts.append(f"{'Job ID':<10s}")
    header_parts.append(f"{'User':>14s}")
    header_parts.append(f"{'State':>10s}")
    header_parts.append(f"{'Queue':>20s}")
    header_parts.append(f"{'Nodes':>10s}")
    header_parts.append(f"{'Score':>10s}")
    header_parts.append(f"{'Walltime':>10s}")
    header_parts.append(f"{'Runtime':>10s}")
    header_parts.append(f"{'Submitted':>12s}")
    header_parts.append(f"{'Project':>24s}")  # Fixed width project column
    for col_name in extra_column_names:
        header_parts.append(f"{col_name:>15s}")  # Extra columns get slightly wider width
    header_string = " : ".join(header_parts)
    
    logger.info(f"Found {len(job_list)} jobs:")
    logger.info(header_string)
    
    for job in job_list:
        logger.info(format_string.format(**job))

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='PBS Jobs Viewer - Display and filter PBS job information\n'+
            'Requirements: PBS system with qstat command available\n'+
            'See also README.md for more information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pbs_jobs_viewer.py                           # Show all jobs
  python pbs_jobs_viewer.py --sort score --reverse    # Sort by score (highest first)
  python pbs_jobs_viewer.py --sort nodes --limit 10   # Top 10 jobs by node count
  python pbs_jobs_viewer.py --state R                 # Show only running jobs
  python pbs_jobs_viewer.py --state RQC               # Show running, queued, and completed jobs
  python pbs_jobs_viewer.py --queue debug             # Show only debug queue jobs
  python pbs_jobs_viewer.py --user zippy              # Show only zippy's jobs
  python pbs_jobs_viewer.py --project E3SM            # Show only E3SM project jobs
  python pbs_jobs_viewer.py --sort project --state Q  # Sort queued jobs by project
  python pbs_jobs_viewer.py --sort walltime --reverse # Sort by requested walltime (longest first)
  python pbs_jobs_viewer.py --sort runtime --state R  # Sort running jobs by elapsed runtime
  python pbs_jobs_viewer.py --sort submitted --reverse # Sort by submission time (newest first)
  python pbs_jobs_viewer.py --jobid 12345,67890       # Show only jobs with IDs 12345 and 67890
  python pbs_jobs_viewer.py --extraCols estimated.start_time  # Add estimated start time column (auto-formatted as MM/DD HH:MM)
  python pbs_jobs_viewer.py --extraCols stime:Start  # Add job start time (datetimes auto-formatted compactly)
  python pbs_jobs_viewer.py --extraCols Resource_List.award_category:ProjType  # Add project type column with custom name
  python pbs_jobs_viewer.py --extraCols estimated.start_time:ETA,Resource_List.award_category:Type  # Add multiple columns
        """
    )
    
    parser.add_argument('--sort', type=str,
                       help='Sort by field (default: no sorting). Can be any standard field or extra column name. Sorting is type-aware and handles dates, times (HH:MM:SS), and numeric values automatically.')
    parser.add_argument('--reverse', action='store_true',
                       help='Sort in descending order (default: ascending)')
    parser.add_argument('--state', type=str, default='RQH',
                       help='Filter by job state(s). Can be a single state (e.g., R) or multiple states (e.g., RQH). Use \"all\" to include all states. Valid states: Q,R,H,W,T,E,B,S,C,F. Default: RQH')
    parser.add_argument('--queue', type=str,
                       help='Filter by queue name (partial match)')
    parser.add_argument('--user', type=str,
                       help='Filter by username (partial match)')
    parser.add_argument('--project', type=str,
                       help='Filter by project name (partial match)')
    parser.add_argument('--jobid', type=str,
                       help='Filter by comma-separated job IDs (e.g., 12345,67890). Only jobs matching these IDs will be shown.')
    parser.add_argument('--limit', type=int,
                       help='Limit output to N jobs')
    parser.add_argument('--extraCols', type=str,
                       help='Comma-separated list of extra columns to include. Format: field.path (use dots for nested fields) or field.path:DisplayName (colon for custom display name). Datetime values are automatically formatted as MM/DD HH:MM. Example: estimated.start_time or stime:Start')
    
    return parser.parse_args()

def main():
    """Main function to run the PBS jobs viewer."""
    args = parse_arguments()
    
    try:
        logger.info("Fetching PBS job information...")
        job_data = qstat_jobs()
        
        if 'error' in job_data:
            logger.error(f"Failed to get job data: {job_data['error']}")
            return
        
        jobs = job_data.get('Jobs', {})
        if not jobs:
            logger.info("No jobs found in the PBS system.")
            return
        
        # Parse extra columns
        extra_columns = None
        if args.extraCols:
            extra_columns = [col.strip() for col in args.extraCols.split(',')]
        
        # Print jobs with filters and sorting
        print_jobs(job_data, 
                  sort_by=args.sort,
                  reverse=args.reverse,
                  state_filter=args.state,
                  queue_filter=args.queue,
                  user_filter=args.user,
                  project_filter=args.project,
                  jobid_filter=args.jobid,
                  limit=args.limit,
                  extra_columns=extra_columns)
        
    except FileNotFoundError:
        logger.error("qstat command not found. Please ensure PBS is installed and qstat is in your PATH.")
    except Exception as e:
        logger.error(f"Error running PBS jobs viewer: {e}")

if __name__ == "__main__":
    main() 
