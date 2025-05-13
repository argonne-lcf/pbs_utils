#!/usr/bin/env python
# Copyright (C) 2025 J. Taylor Childers
# License MIT [https://opensource.org/licenses/MIT]
import argparse
import logging
from pbs import pbsqstat, pbsnodes
from tabulate import tabulate

logger = logging.getLogger(__name__)

def main():
    '''Print top jobs sorted by job score with filtering options'''
    logging_format = ''
    logging_datefmt = ''
    logging_level = logging.INFO
    
    parser = argparse.ArgumentParser(description='Print top jobs sorted by job score with filtering options')
    
    # Number of jobs to display
    parser.add_argument('-n', '--num-jobs', type=int, default=10,
                      help='Number of top jobs to display (default: 10)')
    
    # Filtering options
    parser.add_argument('-s', '--state', choices=['Q', 'R', 'H', 'W', 'E', 'B'],
                      help='Filter jobs by state (Q=Queued, R=Running, H=Held, W=Waiting, E=Exiting, B=Begun)')
    parser.add_argument('-q', '--queue', help='Filter jobs by queue name')
    parser.add_argument('-u', '--user', help='Filter jobs by username')
    parser.add_argument('-p', '--project', help='Filter jobs by project/account')
    parser.add_argument('-j', '--job-name', help='Filter jobs by job name')
    parser.add_argument('-a', '--award', help='Filter jobs by award category (e.g., ALCC, INCITE)')
    
    # Logging options
    parser.add_argument('--debug', default=False, action='store_true',
                      help='Set Logger to DEBUG')
    parser.add_argument('--error', default=False, action='store_true',
                      help='Set Logger to ERROR')
    parser.add_argument('--warning', default=False, action='store_true',
                      help='Set Logger to WARNING')
    parser.add_argument('--logfilename', default=None,
                      help='If set, logging information will go to file')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug and not args.error and not args.warning:
        logging_level = logging.DEBUG
    elif not args.debug and args.error and not args.warning:
        logging_level = logging.ERROR
    elif not args.debug and not args.error and args.warning:
        logging_level = logging.WARNING
    
    logging.basicConfig(level=logging_level,
                       format=logging_format,
                       datefmt=logging_datefmt,
                       filename=args.logfilename)
    
    # Get job data
    jobs_data = pbsqstat.qstat_jobs()
    server_data = pbsqstat.qstat_server()
    job_df = pbsqstat.convert_jobs_to_dataframe(jobs_data, server_data)
    
    # Apply filters
    if args.state:
        job_df = job_df[job_df['state'] == args.state]
    if args.queue:
        job_df = job_df[job_df['queue'] == args.queue]
    if args.user:
        job_df = job_df[job_df['user'] == args.user]
    if args.project:
        job_df = job_df[job_df['project'] == args.project]
    if args.job_name:
        job_df = job_df[job_df['name'] == args.job_name]
    if args.award:
        job_df = job_df[job_df['award_category'] == args.award]
    
    # Sort by score and get top N jobs
    job_df = job_df.sort_values('score', ascending=False).head(args.num_jobs)
    
    # Format score to one decimal place
    job_df['score'] = job_df['score'].round(1)
    
    # Select and rename columns for display
    display_df = job_df[['jobid', 'user', 'state', 'queue', 'name', 'project', 'award_category', 'nodes', 'score']]
    display_df = display_df.rename(columns={
        'jobid': 'Job ID',
        'user': 'User',
        'state': 'State',
        'queue': 'Queue',
        'name': 'Job Name',
        'project': 'Project',
        'award_category': 'Award Type',
        'nodes': 'Nodes',
        'score': 'Score'
    })
    
    # Print the table
    table = tabulate(display_df, headers='keys', tablefmt='pretty', showindex=False)
    logger.info(f"\nTop {args.num_jobs} Jobs by Score:\n{table}")

if __name__ == "__main__":
    main() 