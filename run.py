#!/usr/bin/env python3
""" JArchive Scraper entry points.

This module contains the CLI to begin scraping j-archive.com. Two options may be passed via the command line:

    --db <DB connection parameter>: Database to use for saving data. Defaults to MongoDB running at "mongodb://localhost:27017:jtrivia".

        This scraper currently supports MongoDB and SQLite interfaces. If the connection parameter is a file path ending in a .db
        extension, an SQLite file will be created. Data will be stored in "categories" and "clues" tables.

        If the connection parameter is a URI beginning with mongodb://, the scraper will attempt to connect to this database.

    --season <season integer>: Scrape a single season of games from j-archive. If not specified, scraper will begin scraping games from
        the most current season, and will continue until all games have been scraped.

    Examples:
        
        $python3 run.py 
            
            Scraper will scrape all j-archive games, and save to MongoDB running at :mongodb://localhost:27017:jtrivia".

        $python3 run.py --db jtrivia.db --season 4

            Scraper will scrape only season 4 games, and save to the SQLite file "jtrivia.db".

"""
import sys
import argparse
from scraper import JArchiveScraper, Database 

def arg_positive_int(value):
    """argparse helper to valid season number passed via command line.
    """

    if not value.isdigit():
        raise argparse.ArgumentTypeError("Season must be a positive integer")
    val = int(value)
    if val <= 0:
        raise argparse.ArgumentTypeError("Season number must be greater than zero".format(value))
    return val


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=arg_positive_int, nargs="?", help="Scrape a single season of games on j-archive.")
    parser.add_argument("--db", type=str, nargs="?", help="Enter database connection param.", default="mongodb://localhost:27017/THETEST" ) # default="mongodb://localhost:27017/jarchive"
    parser.add_argument("--singleSeason", help="Scrape only a single season.", action="store_true")
    args = parser.parse_args()

    database = Database.factory(args.db)
    scraper = JArchiveScraper(database, args.season, get_single_season=args.singleSeason)
    scraper.start()

if __name__ == "__main__":
    main()



