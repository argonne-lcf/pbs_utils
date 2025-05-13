#!/usr/bin/env python
# Copyright (C) 2025 J. Taylor Childers
# License MIT [https://opensource.org/licenses/MIT]
import argparse,logging
import pbs
from tabulate import tabulate
logger = logging.getLogger(__name__)


def main():
   ''' Print summary information about nodes in a PBS system 

Prints summary of nodes and their current state.
   
'''
   logging_format = ''
   logging_datefmt = ''
   logging_level = logging.INFO
   
   parser = argparse.ArgumentParser(description='print summary information about nodes in a PBS system')

   parser.add_argument('-a','--all-states', default=True, action='store_false', help="By default nodes are grouped into [in-reservation, in-use, offline, free], set this flag to print full node state information")
   
   parser.add_argument('--debug', default=False, action='store_true', help="Set Logger to DEBUG")
   parser.add_argument('--error', default=False, action='store_true', help="Set Logger to ERROR")
   parser.add_argument('--warning', default=False, action='store_true', help="Set Logger to ERROR")
   parser.add_argument('--logfilename', default=None, help='if set, logging information will go to file')

   args = parser.parse_args()

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

   pbsnodes_data = pbs.pbsnodes()
   pbs.print_nodes_in_state(pbsnodes_data, summarize=args.all_states)


if __name__ == "__main__":
   main() 