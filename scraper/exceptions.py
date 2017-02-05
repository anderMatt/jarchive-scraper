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

class DatabaseOperationalError(Exception):
     """Generic catchall to indicate a database problem. Raised from an error specific for the database currently in use."""
     pass

