#!/usr/bin/env python3

#generic imports
import os
import unittest
import bs4

#test imports
from scraper.scraper import (get_jeopardy_rounds,
        get_category_titles)

TEST_HTML_PAGE = "test_page.html" # File containing markup of a JArchive page to test scraper against.

current_dir = os.path.dirname(os.path.realpath(__file__))
test_html_page_path = "{}/{}".format(current_dir, TEST_HTML_PAGE)

@unittest.skipIf(not os.path.isfile(test_html_page_path), 'Test html page not in directory.')
class TestScraper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(test_html_page_path, 'r') as markup:
            cls.page_soup = bs4.BeautifulSoup(markup, "html.parser")

    def test_get_jeopardy_rounds(self):
        rounds = get_jeopardy_rounds(self.page_soup)
        expected_number_rounds = 2
        self.assertEqual(len(rounds), expected_number_rounds)

    def test_get_category_titles(self):
        game_round = get_jeopardy_rounds(self.page_soup)[0]
        titles = get_category_titles(game_round)
        number_of_categories = 6
        self.assertEqual(len(titles), number_of_categories)






