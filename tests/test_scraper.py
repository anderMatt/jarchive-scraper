#!/usr/bin/env python3

#generic imports
import os
import bs4
import unittest
import mock

#test imports
from scraper.scraper import (get_jeopardy_rounds,
        get_round_categories,
        parse_clue_value,
        parse_clue_question,
        parse_clue_answer,
        serialize_clue_node,
        IncompleteClueError)

TEST_HTML_PAGE = "test_page.html" # File containing markup of a JArchive page to test scraper against.

current_dir = os.path.dirname(os.path.realpath(__file__))
test_html_page_path = "{}/{}".format(current_dir, TEST_HTML_PAGE)

@unittest.skipIf(not os.path.isfile(test_html_page_path), 'Test html page not in directory.')
class TestScraper(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(test_html_page_path, 'r') as markup:
            cls.page_soup = bs4.BeautifulSoup(markup, "html.parser")
        clue_nodes = cls.page_soup.find_all("td", class_="clue")
        cls.clue_node = clue_nodes[3]
        cls.daily_double_clue_node = clue_nodes[19]


    def test_get_jeopardy_rounds(self):
        rounds = get_jeopardy_rounds(self.page_soup)
        expected_number_rounds = 2
        self.assertEqual(len(rounds), expected_number_rounds)

    def test_get_round_categories(self):
        game_round = get_jeopardy_rounds(self.page_soup)[0]
        titles = get_round_categories(game_round)
        self.assertEqual(len(titles), 6)
        expected_titles = [
                "MUCH BIGGER THAN A BREADBOX",
                "LITERARY LINES",
                "THE BROADWAY MUSICAL'S CHARACTERS",
                "REPRESENTIN'",
                "TREES",
                'A TIME FOR "US"'
                ]
        for title, expected_title in zip(titles, expected_titles):
            self.assertEqual(title, expected_title)

    def test_parse_clue_value(self):
        expected_value = "200"
        value = parse_clue_value(self.clue_node)
        self.assertEqual(value, expected_value)

    def test_parse_clue_value_daily_double(self):
        value = parse_clue_value(self.daily_double_clue_node)
        expected_value = "daily_double"
        self.assertEqual(value, expected_value)

    def test_parse_clue_question(self):
        question = parse_clue_question(self.clue_node)
        expected_question = 'This Speaker of the House helped draft the "Contract With America"'
        self.assertEqual(question, expected_question)

    def test_parse_clue_answer(self):
        answer = parse_clue_answer(self.clue_node)
        expected_answer = "Newt Gingrich"
        self.assertEqual(answer, expected_answer)
    
    @mock.patch('scraper.scraper.parse_clue_value')
    def test_serialize_clue_node_raises_error_when_value_missing(self, mock_value):
        mock_value.return_value = None
        with self.assertRaises(IncompleteClueError):
            serialize_clue_node(self.clue_node)
    
    @mock.patch('scraper.scraper.parse_clue_question')
    def test_raises_when_clue_question_missing(self, mock_value):
        mock_value.return_value = None
        with self.assertRaises(IncompleteClueError):
            serialize_clue_node(self.clue_node)
    
    @mock.patch('scraper.scraper.parse_clue_value')
    def test_raises_when_clue_answer_missing(self, mock_value):
        mock_value.return_value = None
        with self.assertRaises(IncompleteClueError):
            serialize_clue_node(self.clue_node)






