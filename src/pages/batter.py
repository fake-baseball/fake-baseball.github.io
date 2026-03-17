"""Generate an HTML page for a single position player."""
from pathlib import Path

from dominate.tags import *
from dominate.util import raw

from constants import BAT_SEASON_MIN_PA
from leaders import BAT_COLUMNS, BAT_QUAL_COLUMNS
from util import fmt_df, convert_name, make_doc


def generate_batter_page(first_name, last_name, *,
                          data_batters, player_info, retired_batters,
                          max_batters, max_qual_batters):
    if (first_name, last_name) in player_info.index:
        active        = True
        pi            = player_info.loc[(first_name, last_name)]
        team_name     = pi['team_name']
        jersey_number = pi['jersey']
        bat_hand      = pi['bats']
        throw_hand    = pi['throws']
        primary_pos   = pi['ppos']
        secondary_pos = pi['spos']
        age           = pi['age']
        salary        = pi['salary']
    else:
        active      = False
        mask        = (data_batters['Last Name'] == last_name) & (data_batters['First Name'] == first_name)
        primary_pos   = data_batters.loc[mask, 'PP'].iloc[0]
        secondary_pos = data_batters.loc[mask, '2P'].iloc[0]
        try:
            ret_mask          = (retired_batters['Last Name'] == last_name) & (retired_batters['First Name'] == first_name)
            retirement_season = retired_batters.loc[ret_mask, 'Retirement Season'].iloc[0]
            retirement_age    = retired_batters.loc[ret_mask, 'Age'].iloc[0]
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
            p(f"Bats: {bat_hand} - Throws: {throw_hand}")
            pos = f"Position: {primary_pos}"
            if secondary_pos:
                pos += f" (Secondary: {secondary_pos})"
            p(pos)
            p(f"Salary: {salary}")
        else:
            strong("Retired")
            pos = f"Position: {primary_pos}"
            if secondary_pos and secondary_pos != "None":
                pos += f" (Secondary: {secondary_pos})"
            p(pos)
            p(f"Retirement Season: {retirement_season}")
            p(f"Retirement Age: {retirement_age}")

        hr()
        h2("Stats")

        stats = data_batters[
            (data_batters['First Name'] == first_name) &
            (data_batters['Last Name']  == last_name)
        ].copy()

        h3("Standard Batting")
        standard_batting = stats[[
            'Season', 'Age', 'Team', 'WAR',
            'GB', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'RBI',
            'SB', 'CS', 'BB', 'K', 'AVG', 'OBP', 'SLG', 'OPS', 'OPS+',
            'TB', 'HBP', 'SH', 'SF', 'stat_type',
        ]]
        _render_table(standard_batting, max_batters, max_qual_batters)

        h3("Advanced Batting")
        raw(fmt_df(stats[['Season', 'Age', 'Team', 'PA',
                    'wOBA', 'wRC', 'wRC+', 'BIP', 'BABIP',
                    'ISO', 'XBH', 'XBH%', 'HR%', 'K%', 'BB%']]).to_html(border=0, index=False))

        h3("Baserunning")
        raw(fmt_df(stats[['Season', 'Age', 'Team', 'PA',
                    'SB', 'CS', 'SB%', 'SbAtt%', 'RS%', 'RC%']]).to_html(border=0, index=False))

        h3("Fielding")
        raw(fmt_df(stats[['Season', 'Age', 'Team', 'PP', '2P',
                    'GB', 'GF', 'E', 'E/GF', 'PB', 'PB/GF']]).to_html(border=0, index=False))

        h3("Value")
        batter_value = stats[[
            'Season', 'Age', 'Team', 'GB', 'PA',
            'Rbat', 'Rbr', 'Rdef', 'Rpos', 'Rcorr', 'Rrep', 'RAA', 'RAR', 'WAA', 'WAR',
        ]]
        raw(fmt_df(batter_value).to_html(border=0, index=False))

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))


def _render_table(df, max_batters, max_qual_batters):
    """Render a stat table, bolding season-leader values.
    Compares raw numeric values for bolding, then displays formatted values via fmt_df.
    """
    display = fmt_df(df)
    with table():
        with thead():
            with tr():
                for col in df.columns:
                    if col == 'stat_type':
                        continue
                    th(col)
        with tbody():
            for (_, raw_row), (_, disp_row) in zip(df.iterrows(), display.iterrows()):
                with tr():
                    if raw_row['stat_type'] == 'S':
                        season     = raw_row['Season']
                        season_max = max_batters.loc[season]
                        qual_max   = max_qual_batters.loc[season]
                        pas        = raw_row['PA']
                        for key in df.columns:
                            if key == 'stat_type':
                                continue
                            raw_val  = raw_row[key]
                            disp_val = disp_row[key]
                            if key in BAT_COLUMNS and float(raw_val) >= float(season_max[key]):
                                td(b(disp_val))
                            elif (key in BAT_QUAL_COLUMNS and pas >= BAT_SEASON_MIN_PA
                                  and float(raw_val) >= float(qual_max[key])):
                                td(b(disp_val))
                            else:
                                td(disp_val)
                    else:
                        for key in df.columns:
                            if key == 'stat_type':
                                continue
                            td(disp_row[key])
