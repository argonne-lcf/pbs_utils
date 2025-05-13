#!/usr/bin/env python
# Copyright (C) 2025 J. Taylor Childers
# License MIT [https://opensource.org/licenses/MIT]

import argparse
import logging
from tabulate import tabulate
import pbs

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def generate_node_hours_summary(jobs, category='project'):
    """
    Generate a summary of node hours for queued jobs, grouped by either project or user.
    
    Args:
        jobs: List of PBS jobs
        category (str): Either 'project' or 'user' to group by
    
    Returns:
        None: Prints the summary table
    """
    job_df = pbs.convert_jobs_to_dataframe(jobs, pbs.qstat_server())
    
    # Filter for only "Queued" jobs (job_state == 'Q')
    job_df = job_df[job_df['state'] == 'Q']
    
    # Summarize node-hours by the selected category
    if category == 'project':
        summary_df = job_df.groupby('project').agg({'node_hours': 'sum', 'jobid': 'count'})
    elif category == 'user':
        summary_df = job_df.groupby('user').agg({'node_hours': 'sum', 'jobid': 'count'})
    
    # Rename the 'jobid' column to 'job_count'
    summary_df = summary_df.rename(columns={'jobid': 'job_count'})
    
    # Sort by node-hours in descending order
    summary_df = summary_df.sort_values(by='node_hours', ascending=False)
    
    # Reset index to prepare for tabulate formatting
    summary_df = summary_df.reset_index()
    
    # Print the summary in tabular form
    table = tabulate(summary_df, headers='keys', tablefmt='pretty', colalign=('left', 'right', 'right'), showindex=False)
    print(table)
    
def main():
    parser = argparse.ArgumentParser(description='Generate PBS node hours summary for queued jobs')
    parser.add_argument('-c','--category', choices=['project', 'user'], default='project',
                      help='Group summary by project or user (default: project)')
    args = parser.parse_args()
    
    # Get PBS jobs
    jobs = pbs.qstat_jobs()
    
    # Generate and display summary
    generate_node_hours_summary(jobs, args.category)

if __name__ == '__main__':
    main() 