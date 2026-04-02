"""Generate the Cy Young Predictor page (docs/cy_young.html)."""
from pathlib import Path

from dominate.tags import *

from constants import SEASON_RANGE
from data import teams as teams_data
from leaders import get_pitching_leaders
from util import make_doc, render_table


_STAT_COLS = ['p_cyp', 'p_gp', 'p_gs', 'p_ip', 'p_er', 'p_k',
              'p_sv', 'p_sho', 'p_w', 'p_l', 'p_era', 'p_vb']


def generate_cy_young():
    teams = teams_data.teams
    conferences = list(dict.fromkeys(teams['conference_name']))
    abbr_by_conf = teams.groupby('conference_name')['abbr'].apply(list).to_dict()

    doc = make_doc("Cy Young Predictor", depth=0)
    with doc:
        h1("Cy Young Predictor")
        p("Formula: CYP = ((5 x IP / 9) - ER) + (K / 12) + (SV x 2.5) + SHO + ((W x 6) - (L x 2)) + (VB x 12)")
        p("VB (Victory Bonus) = 1 if the pitcher's team won their division that season.")

        for season_num in reversed(SEASON_RANGE):
            h2(f"Season {season_num}")
            for conf in conferences:
                df = get_pitching_leaders('p_cyp', season=season_num, num=10,
                                          teams=abbr_by_conf[conf])
                if df.empty:
                    continue
                h3(conf)
                df = df.reset_index(names='rank')
                df['player'] = ''
                render_table(df[['rank', 'First Name', 'Last Name', 'player', 'team'] + _STAT_COLS],
                             depth=0)

    Path("docs/cy_young.html").write_text(str(doc))
