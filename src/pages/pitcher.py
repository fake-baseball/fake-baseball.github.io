"""Generate an HTML page for a single pitcher."""
from pathlib import Path

from dominate.tags import *
from dominate.util import raw

import pitching
import leaders
from data import players
from leaders import SEASON_THRESHOLDS
from stats_meta import PITCHING_STATS
from util import fmt_df, convert_name, make_doc


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
        _render_table(standard_pitching)

        h3("Advanced Pitching")
        raw(fmt_df(stats[[
            'Season', 'Age', 'Team', 'IP',
            'ERA', 'FIP', 'RA9', 'BAA', 'OBPA', 'BIP', 'BABIP',
            'H/9', 'HR/9', 'K/9', 'BB/9', 'K/BB', 'K%', 'BB%',
            'P/GP', 'P/IP', 'P/PA',
        ]]).to_html(border=0, index=False))

        h3("Value Pitching")
        raw(fmt_df(stats[[
            'Season', 'Age', 'Team', 'IP', 'GP', 'GS',
            'RA', 'Rdef', 'RA9', 'RA9def', 'Rlev', 'Rcorr',
            'RAA', 'RAAlev', 'WAA', 'Rrep', 'RAR', 'WAR',
        ]]).to_html(border=0, index=False))

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))


def _render_table(df):
    season_leaders = leaders.pitching_leaders
    """Render a stat table, bolding season-leader values.
    Compares raw numeric values for bolding, then displays formatted values via fmt_df.
    stat_type and IP_true columns are used for logic only and are not displayed.
    IP is displayed as a string but compared via the hidden IP_true column.
    """
    _HIDDEN = {'stat_type', 'IP_true'}
    display = fmt_df(df)
    with table():
        with thead():
            with tr():
                for col in df.columns:
                    if col in _HIDDEN:
                        continue
                    th(col)
        with tbody():
            for (_, raw_row), (_, disp_row) in zip(df.iterrows(), display.iterrows()):
                with tr():
                    if raw_row['stat_type'] == 'S':
                        season = raw_row['Season']
                        bests  = season_leaders.loc[season]
                        for key in df.columns:
                            if key in _HIDDEN:
                                continue
                            disp_val = disp_row[key]
                            cmp_key  = 'IP_true' if key == 'IP' else key
                            cmp_val  = raw_row['IP_true'] if key == 'IP' else raw_row[key]
                            if cmp_key in bests.index and cmp_key in PITCHING_STATS:
                                meta = PITCHING_STATS[cmp_key]
                                qualifies = not meta['qualified'] or raw_row[meta['qual_col']] >= SEASON_THRESHOLDS[meta['qual_col']]
                                best    = float(bests[cmp_key])
                                is_best = qualifies and ((float(cmp_val) <= best) if meta['lowest'] else (float(cmp_val) >= best))
                                td(b(disp_val)) if is_best else td(disp_val)
                            else:
                                td(disp_val)
                    else:
                        for key in df.columns:
                            if key in _HIDDEN:
                                continue
                            td(disp_row[key])
