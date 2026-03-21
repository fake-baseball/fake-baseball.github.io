"""Calculate batting and pitching triple crown winners by season."""
from constants import SEASON_RANGE, BAT_SEASON_MIN_PA, PIT_SEASON_MIN_IP
import leaders as ld
from data import teams as teams_data


def _names(df):
    return set(zip(df['First Name'], df['Last Name']))


def batting_triple_crown():
    """Return list of dicts for each batting triple crown winner.

    Keys: season, first, last, AVG, HR, RBI
    """
    winners = []
    for season in SEASON_RANGE:
        avg_rows = ld.get_batting_leaders('AVG', season=season, num=1)
        hr_rows  = ld.get_batting_leaders('HR',  season=season, num=1)
        rbi_rows = ld.get_batting_leaders('RBI', season=season, num=1)
        crown = _names(avg_rows) & _names(hr_rows) & _names(rbi_rows)
        for first, last in crown:
            mask = (avg_rows['First Name'] == first) & (avg_rows['Last Name'] == last)
            winners.append({
                'season': season,
                'first':  first,
                'last':   last,
                'AVG':    avg_rows.loc[mask].iloc[0]['AVG'],
                'HR':     int(hr_rows.loc[(hr_rows['First Name'] == first) & (hr_rows['Last Name'] == last)].iloc[0]['HR']),
                'RBI':    int(rbi_rows.loc[(rbi_rows['First Name'] == first) & (rbi_rows['Last Name'] == last)].iloc[0]['RBI']),
            })
    return sorted(winners, key=lambda w: w['season'])


def _conf_abbrs(conference):
    return set(teams_data.teams[teams_data.teams['conference_name'] == conference]['abbr'])


def batting_triple_crown_conf(conference):
    """Return batting triple crown winners restricted to teams in the given conference."""
    abbrs = _conf_abbrs(conference)
    winners = []
    for season in SEASON_RANGE:
        avg_rows = ld.get_batting_leaders('AVG', season=season, num=1, teams=abbrs)
        hr_rows  = ld.get_batting_leaders('HR',  season=season, num=1, teams=abbrs)
        rbi_rows = ld.get_batting_leaders('RBI', season=season, num=1, teams=abbrs)
        crown = _names(avg_rows) & _names(hr_rows) & _names(rbi_rows)
        for first, last in crown:
            mask = (avg_rows['First Name'] == first) & (avg_rows['Last Name'] == last)
            winners.append({
                'season': season,
                'first':  first,
                'last':   last,
                'AVG':    avg_rows.loc[mask].iloc[0]['AVG'],
                'HR':     int(hr_rows.loc[(hr_rows['First Name'] == first) & (hr_rows['Last Name'] == last)].iloc[0]['HR']),
                'RBI':    int(rbi_rows.loc[(rbi_rows['First Name'] == first) & (rbi_rows['Last Name'] == last)].iloc[0]['RBI']),
            })
    return sorted(winners, key=lambda w: w['season'])


def pitching_triple_crown_conf(conference):
    """Return pitching triple crown winners restricted to teams in the given conference."""
    abbrs = _conf_abbrs(conference)
    winners = []
    for season in SEASON_RANGE:
        w_rows   = ld.get_pitching_leaders('W',   season=season, num=1, teams=abbrs)
        era_rows = ld.get_pitching_leaders('ERA', season=season, num=1, teams=abbrs)
        k_rows   = ld.get_pitching_leaders('K',   season=season, num=1, teams=abbrs)
        crown = _names(w_rows) & _names(era_rows) & _names(k_rows)
        for first, last in crown:
            winners.append({
                'season': season,
                'first':  first,
                'last':   last,
                'W':   int(w_rows.loc[(w_rows['First Name'] == first) & (w_rows['Last Name'] == last)].iloc[0]['W']),
                'ERA': era_rows.loc[(era_rows['First Name'] == first) & (era_rows['Last Name'] == last)].iloc[0]['ERA'],
                'K':   int(k_rows.loc[(k_rows['First Name'] == first) & (k_rows['Last Name'] == last)].iloc[0]['K']),
            })
    return sorted(winners, key=lambda w: w['season'])


def batting_title(conference=None):
    """Return one dict per season for the batting title winner(s).

    Keys: season, first, last, AVG, PA, unqualified
    unqualified=True means the player won via the hitless-AB adjustment rule.
    conference filters to teams in that conference only.
    """
    import batting as bat_module
    abbrs = _conf_abbrs(conference) if conference else None
    winners = []

    for season in SEASON_RANGE:
        df = bat_module.stats[
            (bat_module.stats['Season'] == season) &
            (bat_module.stats['stat_type'] == 'season')
        ].copy()
        if abbrs is not None:
            df = df[df['Team'].isin(abbrs)]
        if df.empty:
            continue

        qualified   = df[df['PA'] >= BAT_SEASON_MIN_PA]
        unqualified = df[df['PA'] < BAT_SEASON_MIN_PA]

        best_qual_avg = qualified['AVG'].max() if not qualified.empty else -1.0

        candidates = []
        for _, row in qualified.iterrows():
            candidates.append((row['AVG'], row, False))
        for _, row in unqualified.iterrows():
            extra     = int(BAT_SEASON_MIN_PA - row['PA'])
            adj_avg   = row['H'] / (row['AB'] + extra)
            if adj_avg > best_qual_avg:
                candidates.append((adj_avg, row, True))

        if not candidates:
            continue

        best = max(c[0] for c in candidates)
        for avg, row, unqual in candidates:
            if avg == best:
                winners.append({
                    'season':      season,
                    'first':       row['First Name'],
                    'last':        row['Last Name'],
                    'AVG':         row['AVG'],
                    'PA':          int(row['PA']),
                    'unqualified': unqual,
                })

    return sorted(winners, key=lambda w: w['season'])


def era_title(conference=None):
    """Return one dict per season for the ERA title winner(s).

    Keys: season, first, last, ERA, IP_true
    Only qualified pitchers (IP_true >= PIT_SEASON_MIN_IP) are eligible.
    conference filters to teams in that conference only.
    """
    import pitching as pit_module
    abbrs = _conf_abbrs(conference) if conference else None
    winners = []

    for season in SEASON_RANGE:
        df = pit_module.stats[
            (pit_module.stats['Season'] == season) &
            (pit_module.stats['stat_type'] == 'season') &
            (pit_module.stats['IP_true'] >= PIT_SEASON_MIN_IP)
        ].copy()
        if abbrs is not None:
            df = df[df['Team'].isin(abbrs)]
        if df.empty:
            continue

        best = df['ERA'].min()
        for _, row in df[df['ERA'] == best].iterrows():
            winners.append({
                'season':  season,
                'first':   row['First Name'],
                'last':    row['Last Name'],
                'ERA':     row['ERA'],
                'IP_true': row['IP_true'],
            })

    return sorted(winners, key=lambda w: w['season'])


def hr_sb_club(threshold):
    """Return all season rows where HR >= threshold and SB >= threshold, sorted by season then HR desc.

    Keys: season, first, last, HR, SB, AVG, team
    """
    import batting as bat_module
    df = bat_module.stats[bat_module.stats['stat_type'] == 'season'].copy()
    df = df[(df['HR'] >= threshold) & (df['SB'] >= threshold)]
    results = []
    for _, row in df.iterrows():
        results.append({
            'season': row['Season'],
            'first':  row['First Name'],
            'last':   row['Last Name'],
            'HR':     int(row['HR']),
            'SB':     int(row['SB']),
            'AVG':    row['AVG'],
            'team':   row['Team'],
        })
    return sorted(results, key=lambda r: (r['season'], -r['HR']))


def pitching_triple_crown():
    """Return list of dicts for each pitching triple crown winner.

    Keys: season, first, last, W, ERA, K
    """
    winners = []
    for season in SEASON_RANGE:
        w_rows   = ld.get_pitching_leaders('W',   season=season, num=1)
        era_rows = ld.get_pitching_leaders('ERA', season=season, num=1)
        k_rows   = ld.get_pitching_leaders('K',   season=season, num=1)
        crown = _names(w_rows) & _names(era_rows) & _names(k_rows)
        for first, last in crown:
            winners.append({
                'season': season,
                'first':  first,
                'last':   last,
                'W':   int(w_rows.loc[(w_rows['First Name'] == first) & (w_rows['Last Name'] == last)].iloc[0]['W']),
                'ERA': era_rows.loc[(era_rows['First Name'] == first) & (era_rows['Last Name'] == last)].iloc[0]['ERA'],
                'K':   int(k_rows.loc[(k_rows['First Name'] == first) & (k_rows['Last Name'] == last)].iloc[0]['K']),
            })
    return sorted(winners, key=lambda w: w['season'])
