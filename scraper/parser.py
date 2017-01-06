import re
from .exceptions import MalformedRoundHTMLError, IncompleteClueError

"""This module contains functions to parse clue answers and question from j-archive HTML.
"""


CLUE_ANSWER_REGEX = re.compile(r'''<em class="correct_response">(.+)</em>''')
"""
Clue answers on j-archive are not the string content of an HTML element (like questions are), but instead are part of a string that
inline JavaScript writes to the document when a user hovers over a clue box. Regex is used to parse the answer from this string.
Instead of recompiling the regex with every call to _parse_clue_answer, we initialize it here as a global variable.
"""

def _remove_html_tags(string):
    return re.sub(r'''(<.*?>|\\)''', '', string)


def parse_jarchive_page(page_soup):
    """
    Public function scraper.ScraperWorkers objects use to parse clues after requesting a j-archive page and converting it
    to a bs4.BeautifulSoup object.

    Returns:
        Dictionary serialization of all valid categories on the j-archive page. Keys are category titles, with values of a list of serialized clue dictionaries. Example: {"Famous People": ["question": "First president of the United States", "answer":"George Washington"...]}.
    """

    all_categories_and_clues = {}
    jeopardy_rounds = _get_jeopardy_rounds(page_soup)
    for j_round in jeopardy_rounds:
        try:
            round_categories_and_clues = _serialize_jeopardy_round(j_round)
            all_categories_and_clues.update(round_categories_and_clues)
        except MalformedRoundHTMLError:
            continue
    return all_categories_and_clues

def _parse_clue_question(clue_node):
    question_node = clue_node.find("td", class_="clue_text")
    if question_node is None:
        return None
    question = _remove_html_tags(question_node.text)
    return question


def _parse_clue_answer(clue_node):
    answer_node = clue_node.find('div')
    try:
        answer = CLUE_ANSWER_REGEX.search(answer_node['onmouseover']).group(1)
    except AttributeError:  # Could not parse answer
        return None
    answer = _remove_html_tags(answer)
    return answer


def _serialize_clue_node(clue_node):
    """Returns dict of clue question and answer parsed from clue_node.
    
        Raises:
            IncompleteClueError is a question and/or answer cannot be parsed.
    """

    question = _parse_clue_question(clue_node)
    if not question:
        raise IncompleteClueError
    answer = _parse_clue_answer(clue_node)
    if not answer:
        raise IncompleteClueError
    return {"question": question, "answer": answer}


def _get_jeopardy_rounds(page_soup):
    return page_soup.find_all("table", class_="round")


def _get_round_categories(round_soup):
    """Returns a list of the round's categories.

    The list must contain six elements, or else clues will be associated with the wrong category in serialize_jeopardy_round(). 'Padding' the list with None
    when a title string is missing for a category ensures len=6.
    """

    category_title_nodes = round_soup.find_all("td", class_="category_name")
    category_titles = [c.text for c in category_title_nodes or None]
    return category_titles


def _get_round_clue_nodes(round_soup):
    return round_soup.find_all("td", class_="clue")


def _serialize_jeopardy_round(round_soup):
    """
    Returns:
        Dictionary with key,value pairs of category names mapping to a list of clue dictionaries for every category of the
        given round.
    
    Raises:
        MalformedRoundHTMLError: If Beautiful Soup cannot parse 6 category nodes and/or 30 clue nodes from round_soup. This indicates
        the HTML is not structured as the parsing functions expect.
    """

    categories_and_clues = {}
    categories = _get_round_categories(round_soup)
    all_clue_nodes = _get_round_clue_nodes(round_soup) 
    if not (len(categories) == 6 and len(all_clue_nodes) == 30):
        raise MalformedRoundHTMLError
    for (category_index, category) in enumerate(categories):
        category_clue_nodes = [all_clue_nodes[i] for i in range(category_index,30,6)]
        try:
            clues = [_serialize_clue_node(node) for node in category_clue_nodes]
        except IncompleteClueError:
            continue  # Category contains an incomplete clue; move on the the next category of the round.
        categories_and_clues[category] = clues
    return categories_and_clues




