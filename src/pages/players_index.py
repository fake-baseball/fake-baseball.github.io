"""Generate the players index page (docs/players/index.html)."""
from pathlib import Path

from dominate.tags import *

import batting
import pitching
from util import convert_name, make_doc


def generate_players_index():
    names = set()
    names.update(batting.stats[['First Name', 'Last Name']].drop_duplicates().itertuples(index=False))
    names.update(pitching.stats[['First Name', 'Last Name']].drop_duplicates().itertuples(index=False))
    players_list = sorted(names, key=lambda x: x[1].lower())

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
            p(a(f"{last}, {first}", href=f"{convert_name(first, last)}.html"))
    Path("docs/players/index.html").write_text(str(doc))
