"""Generate an HTML page for a single pitcher."""
from pathlib import Path

from dominate.tags import *
from dominate.util import raw

import pitching
import leaders
from data import players
from stats_meta import PITCHING_STATS
from util import fmt_df, render_stat_table, render_leaders_table, convert_name, make_doc


def generate_pitcher_page(first_name, last_name):
    if (first_name, last_name) in players.player_info.index:
        active          = True
        pi              = players.player_info.loc[(first_name, last_name)]
        team_name       = pi['team_name']
        jersey_number   = pi['jersey']
        throw_hand      = pi['throws']
        pitcher_role    = pi['role']
        pitcher_arsenal = pi['pitchTypes']
        age             = pi['age']
        salary          = pi['salary']
    else:
        active = False
        mask   = (pitching.stats['Last Name'] == last_name) & (pitching.stats['First Name'] == first_name)
        pitcher_role = pitching.stats.loc[mask, 'Role'].iloc[0]
        try:
            ret_mask          = (players.retired_pitchers['Last Name'] == last_name) & (players.retired_pitchers['First Name'] == first_name)
            retirement_season = players.retired_pitchers.loc[ret_mask, 'Retirement Season'].iloc[0]
            retirement_age    = players.retired_pitchers.loc[ret_mask, 'Age'].iloc[0]
        except (IndexError, KeyError):
            print("Unable to fetch retirement info for", first_name, last_name)
            retirement_season = "Unknown"
            retirement_age    = "Unknown"

    doc = make_doc(f"{first_name} {last_name}")

    with doc:
        img(src="current.jpeg", width=100)
        h1(f"{first_name} {last_name}")

        if active:
            strong(f"{team_name} #{jersey_number}")
            p(f"Age: {age}")
            p(f"Throws: {throw_hand}")
            p(f"Role: {pitcher_role}")
            p(f"Arsenal: {pitcher_arsenal}")
            p(f"Salary: {salary}")
        else:
            strong("Retired")
            p(f"Role: {pitcher_role}")
            p(f"Retirement Season: {retirement_season}")
            p(f"Retirement Age: {retirement_age}")

        hr()
        h2("Stats")

        stats = pitching.stats[
            (pitching.stats['Last Name']  == last_name) &
            (pitching.stats['First Name'] == first_name)
        ].copy()

        h3("Standard Pitching")
        standard_pitching = stats[[
            'Season', 'Age', 'Team', 'WAR',
            'W', 'L', 'WIN%', 'ERA', 'GP', 'GS', 'CG', 'SHO', 'SV', 'IP',
            'H', 'RA', 'ER', 'HR', 'BB', 'K', 'HBP', 'WP', 'BF', 'ERA-', 'FIP', 'WHIP',
            'stat_type', 'IP_true',
        ]]
        render_leaders_table(standard_pitching, leaders.pitching_leaders, PITCHING_STATS,
                             hidden={'stat_type', 'IP_true'}, col_aliases={'IP': 'IP_true'})

        h3("Advanced Pitching")
        render_stat_table(stats[[
            'Season', 'Age', 'Team', 'IP',
            'ERA', 'FIP', 'RA9', 'BAA', 'OBPA', 'BIP', 'BABIP',
            'H/9', 'HR/9', 'K/9', 'BB/9', 'K/BB', 'K%', 'BB%',
            'P/GP', 'P/IP', 'P/PA', 'stat_type',
        ]])

        h3("Value Pitching")
        render_stat_table(stats[[
            'Season', 'Age', 'Team', 'IP', 'GP', 'GS',
            'RA', 'Rdef', 'RA9', 'RA9def', 'Rlev', 'Rcorr',
            'RAA', 'RAAlev', 'WAA', 'Rrep', 'RAR', 'WAR', 'stat_type',
        ]])

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))


