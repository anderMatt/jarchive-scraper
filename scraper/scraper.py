#!/usr/bin/env python3
import bs4
import requests
import queue
import threading

def get_page_soup(url):
    """Returns bs4.BeautifulSoup object of page at url."""
    try:
        req = requests.get(url)
        req.raise_for_status()
    except requests.exceptions.RequestException as err:
        print('Error getting page soup for <{}>: {}'.format(url, err))
        return
    page_soup = bs4.BeautifulSoup(req.text, "html.parser")
    return page_soup

def get_jeopardy_rounds(page_soup):
    return page_soup.find_all("table", class_="round")

def get_category_titles(round_soup):
    category_title_nodes = round_soup.find_all("td", class_="category_name")
    category_titles = [c.text for c in category_title_nodes or None] # If list does not contain six elements, clues will be associated with the wrong category in <FUNCNAME>. 'Padding' the list with None when a title string does not exist ensures len=6. 



if __name__ == "__main__":
    pass
