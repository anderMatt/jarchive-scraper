#!/usr/bin/env python3
import bs4
import queue
import re
import requests
import threading
import queue
from collections import namedtuple
from database import Database

JARCHIVE_BASE_URL = "http://j-archive.com"
CLUE_ANSWER_REGEX = re.compile(r'''<em class="correct_response">(.+)</em>''')
MAX_THREADS = 8


class MalformedRoundHTMLError(Exception):
    """Raise when the HTML of a JArchive round is not properly formatted.

    The HTML of each jeopardy round should contain 6 category nodes and 30 clue nodes. The HTML of some gamerounds
    contains mismatched tags, usually involving nested <a> and <i> tags in the question text of a clue. Beautiful Soup
    cannot properly parse this invalid HTML, so the scraper is unable to serialize the round.
    """
    pass


class IncompleteClueError(Exception):
    """Raise when a question AND and answer cannot be parsed from a clue node.

    Many game clues on JArchive, especially for very recent games, are incomplete.
    """
    pass


class ScraperWorker(threading.Thread):
    def __init__(self, url_queue, database):  # TODO: pass third param: threading.Event() for graceful termination.
        threading.Thread.__init__(self)
        self.queue = url_queue
        self.database = database

    def run(self):
        while True:
            game_url = self.queue.get()
            print('Scraping game at {}'.format(game_url))
            game_page_soup = get_page_soup(game_url)  # TODO: returns None is err.
            if not game_page_soup:  # Problem getting page.
                self.done()
            jeopardy_rounds = get_jeopardy_rounds(game_page_soup)
            for jeopardy_round in jeopardy_rounds:
                try:
                    serialized_round = serialize_jeopardy_round(jeopardy_round)
                    self.save(serialized_round)
                except MalformedRoundHTMLError:
                    continue
            self.done()

    def save(self, game_category_dict):  # Dict of {title:'', clues: [(v,q,a),...]}
        self.database.save(game_category_dict)

    def done(self):
        self.queue.task_done()


def remove_html_tags(string):
    return re.sub(r'''(<.*?>|\\)''', '', string)

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


def get_jeopardy_rounds(page_soup):
    return page_soup.find_all("table", class_="round")


def get_round_categories(round_soup):
    """Returns a list of the round's categories.

    The list must contain six elements, or else clues will be associated with the wrong category in serialize_jeopardy_round(). 'Padding' the list with None
    when a title string is missing for a category ensures len=6.
    """

    category_title_nodes = round_soup.find_all("td", class_="category_name")
    category_titles = [c.text for c in category_title_nodes or None]
    return category_titles


def get_round_clue_nodes(round_soup):
    return round_soup.find_all("td", class_="clue")


def parse_clue_question(clue_node):
    question_node = clue_node.find("td", class_="clue_text")
    if question_node is None:
        return None
    # question = next(question_node.strings)
    question = remove_html_tags(question_node.text)
    return question


def parse_clue_answer(clue_node):
    answer_node = clue_node.find('div')
    try:
        answer = CLUE_ANSWER_REGEX.search(answer_node['onmouseover']).group(1)
    except AttributeError:  # Could not parse answer
        return None
    return answer


def serialize_clue_node(clue_node):
    """Returns dict of clue question and answer parsed from clue_node.
    
        Raises:
            IncompleteClueError is a question and/or answer is missing.
    """

    question = parse_clue_question(clue_node)
    if not question:
        raise IncompleteClueError
    answer = parse_clue_answer(clue_node)
    if not answer:
        raise IncompleteClueError
    # return Clue(question, answer)
    return {"question": question, "answer": answer}

def serialize_valid_clue_nodes(clue_nodes):
    serialized_clues = []
    for node in clue_nodes:
        try:
            clue = serialize_clue_node(node) 
            serialized_clues.append(clue)
        except IncompleteClueError:
            continue
    return serialized_clues


def serialize_jeopardy_round(round_soup):
    """
    Returns:
        A list of dictionaries that each represent a category of the given round. Each dictionary has the interface
        {'title': category_title_string, 'clues': list_of_serialized_clues}.
    
    Raises:
        MalformedRoundHTMLError: If Beautiful Soup cannot parse 6 category nodes and/or 30 clue nodes from round_soup.
    """

    round_dict = {}
    category_titles = get_round_categories(round_soup)
    round_clue_nodes = get_round_clue_nodes(round_soup) 
    if not (len(category_titles) == 6 and len(round_clue_nodes) == 30):
        raise MalformedRoundHTMLError
    for (category_index, category_title) in enumerate(category_titles):
        category_clue_nodes = [round_clue_nodes[i] for i in range(category_index,30,6)]
        serialized_category_clues = serialize_valid_clue_nodes(category_clue_nodes)
        round_dict[category_title] = list(serialized_category_clues)
    return round_dict


def init_workers(url_queue, database):
    for i in range(MAX_THREADS):
        worker = ScraperWorker(url_queue, database)
        worker.daemon = True
        worker.start()

def start_scraper(season_number):
    db = Database()
    q = queue.Queue()
    workers = init_workers(q, db)
    db.init_connection()
    while season_number > 32:
        print('Scraping season {}'.format(season_number))
        game_urls = get_season_game_urls(season_number)
        for url in game_urls:
            q.put(url)
        q.join()
        season_number -= 1
    return
if __name__ == "__main__":
    start_scraper(33)
