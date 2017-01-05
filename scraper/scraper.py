#!/usr/bin/env python3
import bs4
import queue
import re
import requests
import threading
import queue
from collections import namedtuple
from .exceptions import MalformedRoundHTMLError, IncompleteClueError
from .parser import parse_jarchive_page


JARCHIVE_BASE_URL = "http://j-archive.com"
MAX_THREADS = 8

class JArchiveScraper:
    def __init__(self, database):
        self.database = database
        self.url_queue = queue.Queue()
        self.workers = []

    def init_workers(self):
        for i in range(MAX_THREADS):
            w = ScraperWorker(self.url_queue, self.database)
            w.daemon = True
            w.start()
            self.workers.append(w)

    def start(self, season=None):
        if season is None:
            season = get_current_season_number()  # TODO: unable.
            print("Starting at current season: {}".format(season))
        self.init_workers()
        season = int(season)
        while season > 0:  # TODO: threading.Event for worker communication.
            print('Scraping season {}'.format(season))
            game_urls = get_season_game_urls(season)
            for url in game_urls:
                self.url_queue.put(url)
            self.url_queue.join()
            season -= 1
        self.finished()
        return

    def finished(self):
        print("Finished scraping JArchive")
        return
    
    def onerror(self):
        pass


class ScraperWorker(threading.Thread):
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
        categories_and_clues = parse_jarchive_page(game_page_soup)  # Dict of ALL cat:clues on the page.
        self.save(categories_and_clues)
        self.done()

    def save(self, game_category_dict):  # Dict of {title:'', clues: [(v,q,a),...]}
        self.database.save(game_category_dict)

    def done(self):
        self.queue.task_done()




def get_page_soup(url):
    """Returns bs4.BeautifulSoup object of page at url."""

    try:
        req = requests.get(url)
        req.raise_for_status()
    except requests.exceptions.RequestException as err:
        print('Error getting page soup for <{}>: {}'.format(url, err))
        return  # TODO: raise?
    page_soup = bs4.BeautifulSoup(req.text, "html.parser")
    return page_soup


def get_current_season_number():
    """Return season number of the current season."""
    homepage_soup = get_page_soup(JARCHIVE_BASE_URL)  # TODO: unable to get homepage.
    try:
        current_season_href = homepage_soup.find("table", class_="fullpageheight").find("a")["href"]  # First href of homepage's content links to the current season.
        season_number = re.search(r'''showseason.php\?season=(\d{1,2})''', current_season_href).group(1)
    except (AttributeError, KeyError) as err:  # An href was not found, or it did not link to a season page.
        print("Error getting current season number from the JArchive homepage: {}".format(err))
        return
    return season_number


def get_season_game_urls(season):
    """Returns list of urls for every game of the given season"""
    season_url = "{}/showseason.php?season={}".format(JARCHIVE_BASE_URL, season)
    season_page_soup = get_page_soup(season_url)
    game_hrefs = [td.find('a') for td in season_page_soup.find_all("td", {"align":"left", "valign":"top", "style":"width:140px"})]
    game_urls = [a["href"] for a in game_hrefs]
    return game_urls



