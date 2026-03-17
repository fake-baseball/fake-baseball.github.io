"""Generate an HTML page for a single pitcher."""
from pathlib import Path

from dominate.tags import *
from dominate.util import raw

from constants import PIT_SEASON_MIN_IP
from leaders import PIT_COLUMNS, PIT_QUAL_COLUMNS, PIT_QUAL_LOW_COLUMNS
from util import fmt_df, convert_name, make_doc


def generate_pitcher_page(first_name, last_name, *,
                           data_pitchers, player_info, retired_pitchers,
                           max_pitchers, max_qual_pitchers, min_qual_pitchers):
    if (first_name, last_name) in player_info.index:
        active          = True
        pi              = player_info.loc[(first_name, last_name)]
        team_name       = pi['team_name']
        jersey_number   = pi['jersey']
        throw_hand      = pi['throws']
        pitcher_role    = pi['role']
        pitcher_arsenal = pi['pitchTypes']
        age             = pi['age']
        salary          = pi['salary']
    else:
        active = False
        mask   = (data_pitchers['Last Name'] == last_name) & (data_pitchers['First Name'] == first_name)
        pitcher_role = data_pitchers.loc[mask, 'Role'].iloc[0]
        try:
            ret_mask         = (retired_pitchers['Last Name'] == last_name) & (retired_pitchers['First Name'] == first_name)
            retirement_season = retired_pitchers.loc[ret_mask, 'Retirement Season'].iloc[0]
            retirement_age    = retired_pitchers.loc[ret_mask, 'Age'].iloc[0]
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

        stats = data_pitchers[
            (data_pitchers['Last Name']  == last_name) &
            (data_pitchers['First Name'] == first_name)
        ].copy()

        h3("Standard Pitching")
        standard_pitching = stats[[
            'Season', 'Age', 'Team', 'WAR',
            'W', 'L', 'WIN%', 'ERA', 'GP', 'GS', 'CG', 'SHO', 'SV', 'IP',
            'H', 'RA', 'ER', 'HR', 'BB', 'K', 'HBP', 'WP', 'BF', 'ERA-', 'FIP', 'WHIP',
            'stat_type', 'IP_true',
        ]]
        _render_table(standard_pitching, max_pitchers, max_qual_pitchers, min_qual_pitchers)

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


def _render_table(df, max_pitchers, max_qual_pitchers, min_qual_pitchers):
    """Render a stat table, bolding season-leader values.
    Compares raw numeric values for bolding, then displays formatted values via fmt_df.
    stat_type and IP_true columns are used for logic only and are not displayed.
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
                        season     = raw_row['Season']
                        ip         = raw_row['IP_true']
                        season_max = max_pitchers.loc[season]
                        qual_max   = max_qual_pitchers.loc[season]
                        qual_min   = min_qual_pitchers.loc[season]
                        for key in df.columns:
                            if key in _HIDDEN:
                                continue
                            raw_val  = raw_row[key]
                            disp_val = disp_row[key]
                            # IP displays as a string; use IP_true for numeric comparison
                            cmp_key  = 'IP_true' if key == 'IP' else key
                            cmp_val  = ip if key == 'IP' else raw_val
                            if cmp_key in PIT_COLUMNS and float(cmp_val) >= float(season_max[cmp_key]):
                                td(b(disp_val))
                            elif (key in PIT_QUAL_COLUMNS and ip >= PIT_SEASON_MIN_IP
                                  and float(raw_val) >= float(qual_max[key])):
                                td(b(disp_val))
                            elif (key in PIT_QUAL_LOW_COLUMNS and ip >= PIT_SEASON_MIN_IP
                                  and float(raw_val) <= float(qual_min[key])):
                                td(b(disp_val))
                            else:
                                td(disp_val)
                    else:
                        for key in df.columns:
                            if key in _HIDDEN:
                                continue
                            td(disp_row[key])
