"""Generate the Cy Young Predictor page (docs/cy_young.html)."""
from pathlib import Path

from dominate.tags import *

from constants import SEASON_RANGE
from data import teams as teams_data
from leaders import get_leaders, get_leaders_by_season
from pages.page_utils import make_doc, render_table


_STAT_COLS = ['p_cyp', 'p_cyp2', 'p_cyp3', 'p_war', 'p_vb', 'p_w', 'p_l', 'p_era', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv', 'p_ip', 'p_h', 'p_ra', 'p_er', 'p_bb', 'p_k', 'p_whip', 'p_baa', 'p_fip']


def generate_cy_young():
    teams = teams_data.teams
    conferences = list(dict.fromkeys(teams['conference_name']))
    abbr_by_conf = teams.groupby('conference_name')['abbr'].apply(list).to_dict()

    doc = make_doc("Cy Young Predictor", depth=0)
    with doc:
        h1("Cy Young Predictor")
        p("Formula: CYP = ((5 x IP / 9) - ER) + (K / 12) + (SV x 2.5) + SHO + ((W x 6) - (L x 2)) + (VB x 12)")
        p("VB (Victory Bonus) = 1 if the pitcher's team won their division that season.")
        p("A little exposition about the Cy Young voting in BFBL: Because games are seven innlings long, starters rarely make it to 5 IP to qualify for a win. That results in most starters, even with above average ERA, having losing records. The win then transfers to the relievers.")
        p("The CYP model tends to favor pitchers with great win-loss records. However, sabermetricians know that wins and losses are essentially a useless stat to measure pitcher performance. Additionally, the victory bonus reflects the fact that voters like players that play on good teams.")
        p("Over time, the reliance on wins, loses, and division titles has gone down, but not without a fight. The first major example of the pattern breaking was Felix Hernandez's 2010 AL Cy Young award with the Mariners, when he went 13-12 with the Mariners finishing 4th in the division. Despite pitching a far better season than the other finalists, he earned only 21 of 28 first-place votes. The other first-place vote getters were David Price (TBR won the division) and CC Sabathia (21-7, wins leader).")
        p("Since that point, voters have slowly turned against W-L and division titles in the presence of other dominant pitching seasons. In 2018, Jacob deGrom won the NL Cy Young despite pitching to a 10-9 record for a 4th place Mets team. He earned 29 out of 30 first-place votes. In 2025, Paul Skenes won the NL Cy Young with a 10-10 record on a last-place Pirates team.")

        h2("Cy Young Points leaders by season")
        for conf in conferences:
            h3(conf)
            df = get_leaders_by_season('p_cyp', teams=abbr_by_conf[conf])
            df['player'] = ''
            df['stat_type'] = 'season'
            render_table(df[['season', 'first_name', 'last_name', 'player', 'team', 'stat_type'] + _STAT_COLS], depth=0)

        for season_num in reversed(SEASON_RANGE):
            h2(f"Season {season_num}")
            for conf in conferences:
                df = get_leaders('p_cyp', season=season_num, num=10,
                                          teams=abbr_by_conf[conf])
                if df.empty:
                    continue
                h3(conf)
                df = df.reset_index(names='rank')
                df['player'] = ''
                df['stat_type'] = 'season'
                render_table(df[['rank', 'season', 'first_name', 'last_name', 'player', 'team', 'stat_type'] + _STAT_COLS],
                             depth=0, hidden='season')

    Path("docs/cy_young.html").write_text(str(doc))
