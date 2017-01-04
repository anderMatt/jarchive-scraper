#!/usr/bin/env python3

import sys
import argparse
from scraper import JArchiveScraper, Database, DatabaseConnectionError

def arg_positive_int(value):
    if not value.isdigit():
        raise argparse.ArgumentTypeError("Season must be a positive integer")
    val = int(value)
    if val <= 0:
        raise argparse.ArgumentTypeError("Season number must be greater than zero".format(value))
    return val


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=arg_positive_int, nargs="?", help="season to begin scraper. Defaults to the current season.")
    args = parser.parse_args()

    database = Database()
    try:
        database.init_connection()
    except DatabaseConnectionError as e:
        # print(sys.exc_info()[1])
        print(e)
        print("Unable to initialize database connection. Aborting...")
        sys.exit(1)
    scraper = JArchiveScraper(database)
    scraper.start(args.season)

if __name__ == "__main__":
    main()



