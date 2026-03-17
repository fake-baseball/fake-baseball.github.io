"""Generate the players index page (docs/players/index.html)."""
from pathlib import Path

from dominate.tags import *

from util import player_link, make_doc


def generate_players_index(players_list):
    """
    players_list - list of (first_name, last_name) tuples, sorted by last name
    """
    doc = make_doc("All Players")
    with doc:
        h1("All Players")
        for c in range(ord('A'), ord('Z') + 1):
            letter = chr(c)
            span(a(letter, href=f"#{letter}"))
            span(" ")
        current_letter = ''
        for first, last in players_list:
            if last[0].upper() != current_letter:
                current_letter = last[0].upper()
                h2(current_letter, id=current_letter)
            p(player_link(first, last, prefix='', label=f"{last}, {first}"))
    Path("docs/players/index.html").write_text(str(doc))
