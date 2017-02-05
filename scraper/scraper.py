#!/usr/bin/env python3
import atexit
import queue
import sys
import threading
import queue
from functools import wraps
from time import sleep
from .exceptions import MalformedRoundHTMLError, IncompleteClueError, DatabaseOperationalError
from .parser import get_page_soup, parse_jarchive_page, get_current_season_number, get_season_game_urls
from .database_status_codes import DATABASE_STATUS_CODES


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

    def __init__(self, database, starting_season=None, get_single_season=False):
        self.database = database
        self.url_queue = queue.Queue()
        self.game_data_queue = queue.Queue()
        self.starting_season = starting_season
        self.get_single_season = get_single_season
        self.finished = False

        self.url_worker = None;  # TODO: more than one?
        self.workers = []

        atexit.register(self.cleanup)

    def init_workers(self):
        for i in range(MAX_THREADS-1):
            w = ScraperWorker(self.url_queue, self.game_data_queue)
            w.daemon = True
            self.workers.append(w)
            w.name = "Worker Thread {}".format(i)
            w.start()

        self.url_worker = UrlWorker(self.url_queue)
        self.url_worker.daemon = True
        self.url_worker.name = "URL Worker Thread"
        self.url_worker.start(starting_season = self.starting_season, get_single_season = self.get_single_season)

    def start(self):
        """Entry point for scraping j-archive.
        Args:
            season: Season to start scraping games from. Defaults to the current season.
        """

        self.database.init_connection()

        connection_success = self._wait_for_db_connection()
        if not connection_success:
            print("DB CONNECTION ERROR: <put error here>")
            sys.exit(0)
        
        self.init_workers()
        self.mainloop()

    def _wait_for_db_connection(self):
        for attempt in range(10):  # 10 second timeout window.
            connection_status = self.database.get_connection_status()  #TODO: get err message, to return.
            if connection_status == DATABASE_STATUS_CODES["not connected"]:
                sleep(1)
                continue

            elif connection_status == DATABASE_STATUS_CODES["success"]:
                return True

            elif connection_status == DATABASE_STATUS_CODES["failure"]:
                return False

        return False  # Attempt timeout.


    def on_finished(self):
        print("Finished scraping JArchive")
        print("{:,} categories and {:,} clues were collected!".format(self.database.category_count, self.database.category_count * 5))
        return
    

    def onerror(self):  # What type of args?
        pass


    def mainloop(self):
        while not self.finished:
            try:
                data = self.game_data_queue.get(timeout=1)
            except queue.Empty:
                self._handle_empty_data_queue()
                continue
            try:
                self.database.save(data)
            except DatabaseOperationalError as e:
                self._handle_database_exception(e)  # TODO: implement this method!

        self.on_finished()


    def _handle_empty_data_queue(self):
        print('Empty data queue. Active threads: ')
        for t in threading.enumerate():
            print(t.name)
        print('****************************************')
        if any(t.is_alive() for t in self.workers):
            return  # No data in queue right now, but workers are still working. Data will come eventually.
        else:
            self.finished = True
            # No more workers are processing data. Once data queue is empty, we're finished.
    
    def _handle_database_exception(self, e):
        print("Inside handle DB exception: {}".format(e))

    def exit(self, error=False):
        if error:
            sys.exit(1)
            #  TODO: stacktrace.
        else:
            sys.exit(0)

    def cleanup(self):
        self.database.cleanup()


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
            else:
                print("{} was unable to get categories_and_clues".format(self.name))
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

        self.starting_season = None
        self.get_single_season = False

    def start(self, starting_season, get_single_season):
        self.starting_season = starting_season or get_current_season_number()
        self.get_single_season = get_single_season

        if self.starting_season is None:
            print("Unable to retrieve current season game URLs!")
            self.finished()

        else:
            super().start()
    

    def run(self):
        if self.get_single_season:
            self.populate_url_queue(self.starting_season)
            self.finished()
        else:
            curr_season = self.starting_season
            while (curr_season > 0) and not self.urls_exhausted:
                self.populate_url_queue(curr_season)
                curr_season -= 1
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
        self.urls_exhaused = True
        self.url_queue.put(URL_SENTINEL)

