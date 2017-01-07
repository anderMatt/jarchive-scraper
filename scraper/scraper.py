#!/usr/bin/env python3
import bs4
import queue
import re
import requests
import threading
import queue
from functools import wraps
from .exceptions import MalformedRoundHTMLError, IncompleteClueError
from .parser import parse_jarchive_page


JARCHIVE_BASE_URL = "http://j-archive.com"
MAX_THREADS = 8

class JArchiveScraper:
    """
    Provides entry point to configure and begin scraping the j-archive website.

    Args:
        database: Object responsible for saving the data scraped from j-archive. Should expose a 
        'save' method that accepts a dictionary of category:[clues] parsed from the webpage.

    Attributes:
        url_queue (queue.Queue): Shared among worker threads and populated with j-archive page urls that
            are queued to be scraped.
        workers [ScraperWorker]: List of references to worker threads.
    """
    def __init__(self, database):
        self.database = database
        self.url_queue = queue.Queue()
        self.workers = []

    def init_workers(self):
        for i in range(MAX_THREADS):
            w = ScraperWorker(self.url_queue, self.database)
            w.daemon = True
            self.workers.append(w)
            w.start()

    def start(self, season=None):
        """Entry point for scraping j-archive.
        Args:
            season: Season to start scraping games from. Defaults to the current season.
        """
        if season is None:
            get_all_seasons = True
            season = get_current_season_number()  # TODO: unable.
            print("Scraping all seasons, starting at current season: {}".format(season))
        else:
            get_all_seasons = False
        self.init_workers()
        season = int(season)
        self.mainloop(season, get_all_seasons = get_all_seasons)

    def finished(self):
        print("Finished scraping JArchive")
        return
    
    def onerror(self):  # What type of args?
        pass
    
    def populate_url_queue(self, season):
        """Populate url queue with game urls for given season."""
        game_urls = get_season_game_urls(season)
        if not game_urls:
            print("Unable to get game urls for season {}".format(season))
            self.onerror()
        for url in game_urls:
            self.url_queue.put(url)
        return game_urls

    def mainloop(self, starting_season, get_all_seasons):
        curr_season = starting_season
        if get_all_seasons:
            while curr_season > 0: 
                self.populate_url_queue(curr_season)
                self.url_queue.join()
                curr_season -= 1
        else:
            print("Getting single season: {}".format(starting_season))
            self.populate_url_queue(curr_season)
            self.url_queue.join()

        self.finished()


class ScraperWorker(threading.Thread):
    """
    Thread that requests a j-archive webpage, passes a bs4.BeautifulSoup object of the page to the parsing
    functions, and passes the game data to the database interface for saving.
    """
    def __init__(self, url_queue, database):  # TODO: pass third param: threading.Event() for graceful termination.
        threading.Thread.__init__(self)
        self.queue = url_queue
        self.database = database

    def run(self):
        while True:
            game_url = self.queue.get()
            self.scrape_jarchive_page(game_url)

    def scrape_jarchive_page(self, url):
        print('Scraping game at {}'.format(url))
        game_page_soup = get_page_soup(url)
        if not game_page_soup:
            self.done()
            return
        categories_and_clues = parse_jarchive_page(game_page_soup)  # Dict of ALL cat:clues on the page.
        if not categories_and_clues:
            self.done()
            return
        self.save(categories_and_clues)
        self.done()

    def save(self, game_category_dict):  # Dict of {title:'', clues: [(v,q,a),...]}
        self.database.save(game_category_dict)

    def done(self):
        self.queue.task_done()

    def on_page_request_error(self):
        return


### Helpers ###

def get_page_soup(url):
    """Returns bs4.BeautifulSoup object of page at url."""

    try:
        req = requests.get(url)
        req.raise_for_status()
    except requests.exceptions.RequestException as err:
        print('Error getting page soup for <{}>: {}'.format(url, err))
        return None
        # return  # TODO: raise?
    page_soup = bs4.BeautifulSoup(req.text, "html.parser")
    return page_soup


def get_current_season_number():
    """Return season number of the current Jeopardy season on j-archive."""

    homepage_soup = get_page_soup(JARCHIVE_BASE_URL)  # TODO: unable to get homepage.
    try:
        current_season_href = homepage_soup.find("table", class_="fullpageheight").find("a")["href"]  # First href of homepage's content links to the current season.
        season_number = re.search(r'''showseason.php\?season=(\d{1,2})''', current_season_href).group(1)
    except (AttributeError, KeyError) as err:  # An href was not found, or it did not link to a season page.
        print("Error getting current season number from the JArchive homepage: {}".format(err))
        return
    return season_number


def get_season_game_urls(season):
    """Returns list of urls for every game of the given season.
    
    For every season, j-archive maintains a season page with links to every game of that season.
    """
    season_url = "{}/showseason.php?season={}".format(JARCHIVE_BASE_URL, season)
    season_page_soup = get_page_soup(season_url)
    if not season_page_soup:
        print("Unable to get game urls for season {}".format(season))
    game_hrefs = [td.find('a') for td in season_page_soup.find_all("td", {"align":"left", "valign":"top", "style":"width:140px"})]
    game_urls = [a["href"] for a in game_hrefs]
    return game_urls



