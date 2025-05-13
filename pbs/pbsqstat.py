# Copyright (C) 2025 J. Taylor Childers
# License MIT [https://opensource.org/licenses/MIT]
import subprocess as sp
import pandas as pd
import dateutil,datetime
import json
import logging
from tabulate import tabulate
from .pbs_states import get_full_state_name,get_state_code
logger = logging.getLogger(__name__)

def qstat_queues(exec: str = '/opt/pbs/bin/qstat',
                 args: list = ['-Q','-f','-F','json']) -> dict:
   """
   Retrieves information about PBS queues in JSON format.
   
   Args:
       exec (str): Path to qstat executable
       args (list): Command line arguments for qstat
   
   Returns:
       dict: JSON formatted queue information containing queue states, resources, and configurations
   
   Raises:
       Exception: If qstat command fails

   Example output from qstat -Q -f -F json:
   {
       "timestamp": 1699630815,
       "pbs_version": "2022.1.1.20220926110806",
       "pbs_server": "polaris-pbs-01.hsn.cm.polaris.alcf.anl.gov",
       "Queue": {
           "debug": {
               "queue_type": "Execution",
               "state_count": "Transit:0 Queued:0 Held:0 Waiting:0 Running:0 Exiting:0 Begun:0",
               "resources_assigned": {
                   "mem": "0kb",
                   "ncpus": 0,
                   "nodect": 0
               },
               "resources_available": {
                   "mem": "527672488kb",
                   "ncpus": 64,
                   "nodect": 1
               }
           },
           "debug-scaling": {
               "queue_type": "Execution",
               "state_count": "Transit:0 Queued:0 Held:0 Waiting:0 Running:0 Exiting:0 Begun:0",
               "resources_assigned": {
                   "mem": "0kb",
                   "ncpus": 0,
                   "nodect": 0
               },
               "resources_available": {
                   "mem": "527672488kb",
                   "ncpus": 64,
                   "nodect": 1
               }
           }
       }
   }
   """
   cmd = exec + ' ' + ' '.join(args)
   completed_process = sp.run(cmd.split(' '),stdout=sp.PIPE,stderr=sp.PIPE)
   if completed_process.returncode != 0:
      raise Exception(completed_process.stderr.decode('utf-8'))
   return json.loads(completed_process.stdout.decode('utf-8'))

def get_queued_jobs_states(queue_data):
   """
   Extracts job state counts from queue data.
   
   Args:
       queue_data (dict): Queue information from qstat_queues()
   
   Returns:
       dict: Dictionary mapping queue names to dictionaries of state counts
             Format: {'queue_name': {'state': count, ...}, ...}
   """
   queues = queue_data['Queue']
   output = {}
   for queue in queues:
      output[queue] = {}
      if 'state_count' in queues[queue]:
         for state_count in queues[queue]['state_count'].split():
            state,state_count = state_count.split(':')
            state_count = int(state_count)
            output[queue][state] = state_count
   
   return output

def get_job_node_hours(job):
   """
   Calculates the total node-hours requested by a job.
   
   Args:
       job (dict): Job information dictionary
   
   Returns:
       int: Total node-hours (nodes * walltime in hours)
   """
   walltime = job['Resource_List'].get('walltime', '00:00:00')
   nodes = job['Resource_List'].get('nodect', 0)
   return int(string_time_to_hours(walltime) * nodes)

def get_node_hours(jobs_data):
   """
   Calculates total node-hours for all jobs grouped by queue and state.
   
   Args:
       jobs_data (dict): Job information from qstat_jobs()
   
   Returns:
       dict: Dictionary mapping queue names to dictionaries of state node-hours
             Format: {'queue_name': {'state': hours, ...}, ...}
   """
   jobs = jobs_data['Jobs']
   output = {} # will be {'queue_name': {'stateA': hours, 'stateB': hours}}
   
   for job_id,job_data in jobs.items():
      job_state = job_data['job_state']
      job_node_hours = get_job_node_hours(job_data)
      job_queue = job_data['queue']

      if job_queue not in output:
         output[job_queue] = {}
      if job_state not in output[job_queue]:
         output[job_queue][job_state] = 0
      output[job_queue][job_state] += job_node_hours

   return output

def print_queued_jobs_states(job_data: dict, summarize: bool = False):
   """
   Prints a summary of job states across queues, including counts and node-hours.
   
   Args:
       job_data (dict): Job information from qstat_jobs()
       summarize (bool): If True, filters job states by Running/Queued only
   """
   job_df = convert_jobs_to_dataframe(job_data, qstat_server())

   if summarize:
      # Filter for only Running and Queued states
      job_df = job_df[job_df['state'].isin(['Q', 'R'])]
      job_df['state'] = job_df['state'].replace({'Q': 'Queued', 'R': 'Running'})
      summary_df = job_df.groupby(['queue', 'state']).agg({'jobid': 'count', 'node_hours': 'sum', 'nodes': 'sum'}).unstack(fill_value=0)
      
      summary_df.columns = ['Queued Count', 'Running Count', 'Queued Node Hours',  'Running Node Hours',  'Queued Nodes',  'Running Nodes']
   else:
      # Create pivot tables for counts and node hours
      summary_df = job_df.pivot_table(index='queue', columns='state', values='jobid', aggfunc='count', fill_value=0).join(
         job_df.pivot_table(index='queue', columns='state', values='node_hours', aggfunc='sum', fill_value=0),
         rsuffix=' Node Hours'
      )

   summary_df = summary_df.reset_index()
   summary_df.columns.name = None  # Remove the column index name

   # Calculate totals
   totals = summary_df.sum(numeric_only=True)
   totals['queue'] = 'Totals'

   # Append totals row to the DataFrame
   summary_df = pd.concat([summary_df, totals.to_frame().T], ignore_index=True)

   table = tabulate(summary_df.to_records(index=False), headers='keys', tablefmt='pretty',colalign=['left'] + ['right'] * (summary_df.shape[1] - 1))
   logger.info("\n" + table)

def convert_jobs_to_dataframe(job_data: dict,server_data: dict) -> pd.DataFrame:
   """
   Converts job information into a pandas DataFrame for easier analysis.
   
   Args:
       job_data (dict): Job information from qstat_jobs()
       server_data (dict): Server information from qstat_server()
   
   Returns:
       pd.DataFrame: DataFrame containing job information with columns:
                    - jobid, user, state, queue, nodes, score, runtime
                    - timing info (qtime, ctime, etime, mtime, stime, obittime)
                    - resource info (project, name, award_category, filesystems)
                    - allocation info (total_allocation, current_allocation)
                    - directory info (jobdir, workdir)
                    - node_hours
   """
   jd = job_data['Jobs']
   job_data = []
   for jobid,job in jd.items():
      score = execute_job_sort_formula(server_data,job) 
      jobid = jobid.split('.')[0]
      row = {
         'jobid':jobid,
         'user':job['Variable_List'].get('PBS_O_LOGNAME',''),
         'state':job['job_state'],
         'queue':job['queue'],
         'nodes':job['Resource_List'].get('nodect',0),
         'score':score,
         'runtime':string_time_to_minutes(job['Resource_List']['walltime']),
         'qtime':job.get('qtime',''), # "Fri Nov 10 11:34:29 2023"
         'ctime':job.get('ctime',''), # "Fri Nov 10 11:34:29 2023"
         'etime':job.get('etime',''), # "Fri Nov 10 11:34:29 2023"
         'mtime':job.get('mtime',''), # "Fri Nov 10 11:34:29 2023"
         'stime':job.get('stime',''), # "Fri Nov 10 11:34:29 2023"
         'obittime':job.get('obittime',''), # "Fri Nov 10 11:34:29 2023"
         'eligible_time':string_time_to_minutes(job.get('eligible_time','0:0:0')), # "42:53:26"
         'project':job.get('project',''),
         'name':job.get('Job_Name',''),
         'award_category': job['Resource_List'].get('award_category',''),
         'filesystems':job['Resource_List'].get('filesystems',''),
         'total_allocation':job['Resource_List'].get('total_allocation',''),
         'current_allocation':job['Resource_List'].get('current_allocation',''),
         'jobdir':job['Resource_List'].get('jobdir',''),
         'workdir':job['Variable_List'].get('PBS_O_WORKDIR',''),
         'node_hours': int(job['Resource_List'].get('nodect',0) * string_time_to_hours(job['Resource_List']['walltime'])),
      }

      # Calculate run time if job has started and finished
      if 'stime' in job and 'obittime' in job:
         stime = dateutil.parser.parse(row['stime'])
         obittime = dateutil.parser.parse(row['obittime'])
         row['run_time'] = (obittime - stime).total_seconds()/60
      else:
         row['run_time'] = 0

      # Calculate queued time if job has queue time
      if 'qtime' in job:
         qtime = dateutil.parser.parse(row['qtime'])
         row['queued_time'] = (datetime.datetime.now() - qtime).total_seconds()/60

      job_data.append(row)
   
   # Convert DataFrame and parse datetime columns
   df = pd.DataFrame(job_data)
   df['qtime'] = pd.to_datetime(df['qtime'])
   df['ctime'] = pd.to_datetime(df['ctime'])
   df['etime'] = pd.to_datetime(df['etime'])
   df['mtime'] = pd.to_datetime(df['mtime'])
   df['stime'] = pd.to_datetime(df['stime'])
   df['obittime'] = pd.to_datetime(df['obittime'])

   return df

def print_jobs(job_data: dict,server_data: dict = None) -> None:
   """
   Prints a simple summary of jobs showing ID, user, state, queue, nodes, and score.
   
   Args:
       job_data (dict): Job information from qstat_jobs()
       server_data (dict, optional): Server information from qstat_server()
   """
   if server_data is None:
      server_data = qstat_server()
   jd = job_data['Jobs']
   logger.info(f"{'Job ID':<10s}: {'User':>20s} {'State':>10s} {'Queue':>20s} {'Nodes':>10s} {'Score':>10s}")
   for jobid,job in jd.items():
      score = execute_job_sort_formula(server_data,job) 
      jobid = jobid.split('.')[0]
      logger.info(f"{jobid:<10s}: {job['Variable_List']['PBS_O_LOGNAME']:>20s} {job['job_state']:>10s} {job['queue']:>20s} {job['Resource_List']['nodect']:>10d} {score:10.2f}")

def print_top_jobs(job_df: pd.DataFrame, 
                   top_n: int = 10,
                   state_filter = ['R','Q'],
                   queue_filter = ['debug','debug-scaling','small','medium','large','preemptable']) -> None:
   """
   Prints the top N jobs by score for each queue.
   
   Args:
       job_df (pd.DataFrame): DataFrame of job information
       top_n (int): Number of top jobs to show per queue
       state_filter (list): List of job states to include
       queue_filter (list): List of queues to include
   """
   tmpdf = job_df[job_df['state'].isin(state_filter)]
   tmpdf = tmpdf[tmpdf['queue'].isin(queue_filter)]
   pd.set_option('display.float_format', '{:10.0f}'.format)
   ordered_df = tmpdf.sort_values('score',ascending=False)
   grouped_df = ordered_df.groupby('queue')
   for name,group in grouped_df:
      group = group.head(top_n)
      logger.info(f"Top {top_n} out of {group.shape[0]} jobs in queue {name}:\n{group[['jobid','user','project','state','queue','nodes','score','filesystems']]}")

def qstat_server(exec='/opt/pbs/bin/qstat',
                 args=['-B','-f','-F','json']) -> dict:
   """
   Retrieves PBS server information in JSON format.
   
   Args:
       exec (str): Path to qstat executable
       args (list): Command line arguments for qstat
   
   Returns:
       dict: JSON formatted server information
   
   Raises:
       Exception: If qstat command fails

   Example output from qstat -B -f -F json:
   {
       "timestamp": 1699630815,
       "pbs_version": "2022.1.1.20220926110806",
       "pbs_server": "polaris-pbs-01.hsn.cm.polaris.alcf.anl.gov",
       "Server": {
           "acl_host_enable": "True",
           "acl_host_sloppy": "False",
           "acl_users_enable": "True",
           "allow_node_submit": "True",
           "checkpoint_min": 0,
           "default_node": "False",
           "default_queue": "workq",
           "flatuid": "False",
           "job_history_enable": "True",
           "job_history_duration": 336,
           "max_array_size": 10000,
           "max_concurrent_provision": 5,
           "max_job_sequence_id": 999999,
           "max_queued": 0,
           "max_queued_res": 0,
           "max_run": 0,
           "max_run_res": 0,
           "max_user_run": 0,
           "next_job_number": 1147580,
           "node_pack": "False",
           "operating_mode": 15035,
           "query_other_jobs": "True",
           "resources_default": {
               "ncpus": 1,
               "nodect": 1,
               "walltime": "01:00:00"
           },
           "scheduling": "True",
           "state_count": "Transit:0 Queued:0 Held:0 Waiting:0 Running:0 Exiting:0 Begun:0",
           "total_jobs": 0
       }
   }
   """
   cmd = exec + ' ' + ' '.join(args)
   completed_process = sp.run(cmd.split(' '),stdout=sp.PIPE,stderr=sp.PIPE)
   if completed_process.returncode != 0:
      raise Exception(completed_process.stderr.decode('utf-8'))
   return json.loads(completed_process.stdout.decode('utf-8'))

def execute_job_sort_formula(server_data: dict, job_data: dict) -> float:
   """
   Calculates job score using the PBS job sort formula.
   
   Args:
       server_data (dict): Server information from qstat_server()
       job_data (dict): Job information
   
   Returns:
       float: Calculated job score
   """
   server_dict = server_data['Server']
   first_server = server_dict[list(server_dict.keys())[0]]
   formula_str = first_server['job_sort_formula']

   rl = job_data['Resource_List']
   base_score        = float(rl['base_score'])
   score_boost       = float(rl['score_boost'])
   enable_wfp        = float(rl['enable_wfp'])
   wfp_factor        = float(rl['wfp_factor'])
   eligible_time     = float(string_time_to_seconds(job_data['eligible_time']))
   walltime          = float(string_time_to_seconds(rl['walltime']))
   project_priority  = float(rl['project_priority'])
   nodect            = float(rl['nodect'])
   total_cpus        = float(rl['total_cpus'])
   enable_backfill   = float(rl['enable_backfill'])
   backfill_max      = float(rl['backfill_max'])
   backfill_factor   = float(rl['backfill_factor'])
   enable_fifo       = float(rl['enable_fifo'])
   fifo_factor       = float(rl['fifo_factor'])

   return eval(formula_str)

def get_integers(stringtime):
   """
   Converts time string in HH:MM:SS format to integers.
   
   Args:
       stringtime (str): Time string in HH:MM:SS format
   
   Returns:
       tuple: (hours, minutes, seconds) as integers
   """
   hr,min,sec = stringtime.split(':')
   hr,min,sec = int(hr),int(min),int(sec)
   return hr,min,sec

def string_time_to_seconds(stringtime):
   """
   Converts time string to total seconds.
   
   Args:
       stringtime (str): Time string in HH:MM:SS format
   
   Returns:
       int: Total seconds
   """
   hr,min,sec = get_integers(stringtime)
   return hr * 60 * 60 + min * 60 + sec

def string_time_to_minutes(stringtime):
   """
   Converts time string to total minutes.
   
   Args:
       stringtime (str): Time string in HH:MM:SS format
   
   Returns:
       int: Total minutes
   """
   hr,min,sec = get_integers(stringtime)
   return hr * 60 + min

def string_time_to_hours(stringtime):
   """
   Converts time string to total hours as a float.
   
   Args:
       stringtime (str): Time string in HH:MM:SS format
   
   Returns:
       float: Total hours including fractional parts
   """
   hr,min,sec = get_integers(stringtime)
   return float(hr) + float(min)/60. + float(sec/60./60.)

def walltime_to_hours(walltime):
   """
   Converts walltime string to hours.
   
   Args:
       walltime (str): Walltime string in HH:MM:SS format
   
   Returns:
       float: Total hours
   """
   return string_time_to_hours(walltime)

def qstat_jobs(exec: str = '/opt/pbs/bin/qstat',
               args: list = ['-t','-f','-F','json']) -> dict:
   """
   Retrieves information about PBS jobs in JSON format.
   
   Args:
       exec (str): Path to qstat executable
       args (list): Command line arguments for qstat
   
   Returns:
       dict: JSON formatted job information containing job states, resources, and configurations
   
   Raises:
       Exception: If qstat command fails

   Example output from qstat -t -f -F json:
   {
       "timestamp": 1699630815,
       "pbs_version": "2022.1.1.20220926110806",
       "pbs_server": "polaris-pbs-01.hsn.cm.polaris.alcf.anl.gov",
       "Jobs": {
           "1147579.polaris-pbs-01": {
               "Job_Name": "test_job",
               "Job_Owner": "user@host",
               "job_state": "R",
               "queue": "debug",
               "server": "polaris-pbs-01",
               "Checkpoint": "u",
               "ctime": "Fri Nov 10 11:34:29 2023",
               "Error_Path": "host:/path/to/error",
               "Hold_Types": "n",
               "Join_Path": "n",
               "Keep_Files": "n",
               "Mail_Points": "a",
               "mtime": "Fri Nov 10 11:34:29 2023",
               "Output_Path": "host:/path/to/output",
               "Priority": 0,
               "qtime": "Fri Nov 10 11:34:29 2023",
               "Rerunable": "True",
               "Resource_List": {
                   "nodect": 1,
                   "walltime": "01:00:00"
               },
               "Variable_List": {
                   "PBS_O_LOGNAME": "user",
                   "PBS_O_HOST": "host",
                   "PBS_O_WORKDIR": "/path/to/workdir"
               },
               "comment": "Job started on host",
               "etime": "Fri Nov 10 11:34:29 2023",
               "stime": "Fri Nov 10 11:34:29 2023"
           }
       }
   }
   """
   cmd = exec + ' ' + ' '.join(args)
   completed_process = sp.run(cmd.split(' '),stdout=sp.PIPE,stderr=sp.PIPE)
   if completed_process.returncode != 0:
      raise Exception(completed_process.stderr.decode('utf-8'))
   return json.loads(completed_process.stdout.decode('utf-8'))
