"""Generate the players index page (docs/players/index.html)."""
from pathlib import Path

from dominate.tags import *

import batting
import pitching
from data import players as players_data
from pages.page_utils import make_doc


def generate_players_index():
    pids = set(batting.stats['player_id'].unique())
    pids.update(pitching.stats['player_id'].unique())
    pi = players_data.player_info
    players_list = sorted(pids, key=lambda pid: pi.loc[pid, 'last_name'].lower())

    doc = make_doc("All Players")
    with doc:
        h1("All Players")
        for c in range(ord('A'), ord('Z') + 1):
            letter = chr(c)
            span(a(letter, href=f"#{letter}"))
            span(" ")
        current_letter = ''
        for pid in players_list:
            first = pi.loc[pid, 'first_name']
            last  = pi.loc[pid, 'last_name']
            if last[0].upper() != current_letter:
                current_letter = last[0].upper()
                h2(current_letter, id=current_letter)
            p(a(f"{last}, {first}", href=f"{pid}.html"))
    Path("docs/players/index.html").write_text(str(doc))
