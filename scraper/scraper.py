#!/usr/bin/env python3
import bs4
import queue
import re
import requests
import sys
import threading
import queue
from functools import wraps
from .exceptions import MalformedRoundHTMLError, IncompleteClueError
from .parser import parse_jarchive_page


JARCHIVE_BASE_URL = "http://j-archive.com"
MAX_THREADS = 8
URL_SENTINEL = "FINISHED"

class JArchiveScraper:
    """
    Provides entry point to configure and begin scraping the j-archive website.

    Args:
        database: Object responsible for saving the data scraped from j-archive. Should expose a 
        'save' method that accepts a dictionary of category:[clues] parsed from the webpage.

    Attributes:
        url_queue (queue.Queue): Shared among worker threads and populated with j-archive page urls that
            are queued to be scraped.

        game_data_queue (queue.Queue): Populated with game data dicts created by ScraperWorker threads, for entry into database.

        workers [ScraperWorker]: List of references to worker threads.

        url_worker (threading.Thread): Responsible for populating the url_queue for ScraperWorkers threads to consume.
    """

    def __init__(self, database):
        self.database = database
        self.url_queue = queue.Queue()
        self.game_data_queue = queue.Queue()

        self.url_worker = None;  # TODO: more than one?
        self.workers = []

        self.finished = False

    def init_workers(self):
        for i in range(MAX_THREADS-1):
            w = ScraperWorker(self.url_queue, self.game_data_queue)
            w.daemon = True
            self.workers.append(w)
            w.start()

        self.url_worker = UrlWorker(self.url_queue)
        self.url_worker.daemon = True
        self.url_worker.start()


    def start(self, season=None):
        """Entry point for scraping j-archive.
        Args:
            season: Season to start scraping games from. Defaults to the current season.
        """
        self.init_workers()
        self.database.init_connection()  # TODO: "wait" for connection response.
        # connection_success = self._wait_for_db_connection()
        if not connection_success:
            print("DB CONNECTION ERROR: <put error here>")
            sys.exit(1)
        
        print("DB successfully connected! Startin scraper mainloop.")
        self.mainloop()

    def _wait_for_db_connection(self):
        for attempt in range (30):
            connection_status = self.database.get_connection_status()  #TODO: get err message, to return.
            if connection_status == DB.WAITING:
                sleep(1)
                continue

            elif connection_status == DB.SUCCESS:
                return True

            elif connection_status == DB.FAILURE:
                return False

        return False  # Attempt timeout.

    def on_finished(self):
        print("Finished scraping JArchive")
        return
    
    def onerror(self):  # What type of args?
        pass

    def on_url_queue_fail(self):
        print("Scraper unable to find urls to any more games, exiting.")
        self.exit(error = False)
        return
    

    def mainloop(self):
        while not self.finished:
            try:
                data = self.game_data_queue.get(timeout=1)
            except queue.Empty:
                self._handle_empty_data_queue()
                continue
            try:
                self.database.save(data)
            except Exception as e:
                self._handle_database_exception(e)  # TODO: implement this method!

        self.on_finished()



    def _handle_empty_data_queue(self):
        if(threading.active_count() > 1): 
            return  # No data in queue right now, but workers are still working. Data will come eventually.
        else:
            self.finished = True
            # No more workers are processing data. Once data queue is empty, we're finished.
    
    def _handle_database_exception(e):
        print("Inside handle DB exception: {}".format(e))

    def exit(self, error=False):
        if error:
            sys.exit(1)
            #  TODO: stacktrace.
        else:
            sys.exit(0)


class ScraperWorker(threading.Thread):
    """
    Thread that requests a j-archive webpage, passes a bs4.BeautifulSoup object of the page to the parsing
    functions, and passes the game data to the database interface for saving.
    """
    def __init__(self, url_queue, out_queue): 
        threading.Thread.__init__(self)
        self.url_queue = url_queue
        self.out_queue = out_queue

    def run(self):
        while True:
            game_url = self.url_queue.get()
            if game_url == URL_SENTINEL:  # No more urls are coming
                self.url_queue.put(URL_SENTINEL)  # For next worker to get
                return

            categories_and_clues = self.scrape_jarchive_page(game_url)
            if categories_and_clues:
                self.out_queue.put(categories_and_clues)
            self.done()

    def scrape_jarchive_page(self, url):
        print('Scraping game at {}'.format(url))
        game_page_soup = get_page_soup(url)
        if not game_page_soup:
            return None
        categories_and_clues = parse_jarchive_page(game_page_soup)  # Dict of ALL cat:clues on the page.
        return categories_and_clues

    def done(self):
        self.url_queue.task_done()

    def on_page_request_error(self):
        return


class UrlWorker(threading.Thread):  # Responsible for populating game urls for the workers to process.

    def __init__(self, url_queue):
        threading.Thread.__init__(self)
        self.url_queue = url_queue
        self.urls_exhausted = False

    def start(self, starting_season = None):
        if starting_season is None:
            curr_season = get_current_season_number()  # TODO: class method. 
            while (curr_season > 0) and not self.urls_exhausted:
                self.populate_url_queue(curr_season)
                curr_season -= 1
        else:  # Only a single season
            self.populate_url_queue(curr_season)
            self.finished()

    
    def populate_url_queue(self, season):
        """Populate url queue with game urls for workers to process.
        
        Sets "finished" flag to True if no more game urls are found.
        """
        game_urls = get_season_game_urls(season)  # TODO: class method
        if not game_urls:
            print("Unable to get game urls for season {}".format(season))
            self.finished()

        for url in game_urls:
            self.url_queue.put(url)

    def finished(self):
        self.url_queue.put(URL_SENTINEL)
        self.finished = True


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
    return int(season_number)


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



