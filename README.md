J-Archive Scraper
=====================

This is a web scraper that collects trivia clues from [j-archive.com](https://j-archive.com), a fan maintained repository of [Jeopardy!](https://jeopardy.com) games.

## Installation

First, clone this repository.
    
    $ git clone https://github.com/anderMatt/jarchive-scraper.git jtrivia

Then, install dependencies

    $ pip3 install -r jtrivia/req.txt

Finally, run the script.

    $ ./jtrivia/run.py

## Saving Clues

Game clues can currently be saved to SQLite and MongoDB databases. The scraper will default to an SQLite database
named jtrivia.db in the directory the scraper run script was started in.

### Specifying a database

You may specify a database to use by passing a database URI with the --db option. The scraper will automatically determine the database engine from
the URI.

##### SQLITE

    $ ./jtrivia/run.py --db sqlite:///path/to/my/database.db

##### MongoDB
    
    $ ./jtrivia/run.py --db mongodb://localhost:27017/jarchive


## Scraping Games

The default behavior is to begin scraping games from the most recent game on j-archive, and continuing until every
game has been collected.

To begin at a different season, pass the season number to the --season argument.

    $ ./jtrivia/run.py --season 15

To scrape only a single season, set the --singleSeason flag
    
    $ ./jtrivia/run.py --singleSeason

## Development

Discover a bug, or want to suggest improvements? [Open an issue](https://github.com/anderMatt/jarchive-scraper) or 
clone the project and send a pull request with your changes!

### Running Tests

Unit tests may be run by executing `python3 -m unittest`
