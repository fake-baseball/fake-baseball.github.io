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
        avg_rows = ld.get_batting_leaders('avg', season=season, num=1)
        hr_rows  = ld.get_batting_leaders('hr',  season=season, num=1)
        rbi_rows = ld.get_batting_leaders('rbi', season=season, num=1)
        crown = _names(avg_rows) & _names(hr_rows) & _names(rbi_rows)
        for first, last in crown:
            mask = (avg_rows['First Name'] == first) & (avg_rows['Last Name'] == last)
            winners.append({
                'season': season,
                'first':  first,
                'last':   last,
                'avg':    avg_rows.loc[mask].iloc[0]['avg'],
                'hr':     int(hr_rows.loc[(hr_rows['First Name'] == first) & (hr_rows['Last Name'] == last)].iloc[0]['hr']),
                'rbi':    int(rbi_rows.loc[(rbi_rows['First Name'] == first) & (rbi_rows['Last Name'] == last)].iloc[0]['rbi']),
            })
    return sorted(winners, key=lambda w: w['season'])


def _conf_abbrs(conference):
    return set(teams_data.teams[teams_data.teams['conference_name'] == conference]['abbr'])


def batting_triple_crown_conf(conference):
    """Return batting triple crown winners restricted to teams in the given conference."""
    abbrs = _conf_abbrs(conference)
    winners = []
    for season in SEASON_RANGE:
        avg_rows = ld.get_batting_leaders('avg', season=season, num=1, teams=abbrs)
        hr_rows  = ld.get_batting_leaders('hr',  season=season, num=1, teams=abbrs)
        rbi_rows = ld.get_batting_leaders('rbi', season=season, num=1, teams=abbrs)
        crown = _names(avg_rows) & _names(hr_rows) & _names(rbi_rows)
        for first, last in crown:
            mask = (avg_rows['First Name'] == first) & (avg_rows['Last Name'] == last)
            winners.append({
                'season': season,
                'first':  first,
                'last':   last,
                'avg':    avg_rows.loc[mask].iloc[0]['avg'],
                'hr':     int(hr_rows.loc[(hr_rows['First Name'] == first) & (hr_rows['Last Name'] == last)].iloc[0]['hr']),
                'rbi':    int(rbi_rows.loc[(rbi_rows['First Name'] == first) & (rbi_rows['Last Name'] == last)].iloc[0]['rbi']),
            })
    return sorted(winners, key=lambda w: w['season'])


def pitching_triple_crown_conf(conference):
    """Return pitching triple crown winners restricted to teams in the given conference."""
    abbrs = _conf_abbrs(conference)
    winners = []
    for season in SEASON_RANGE:
        w_rows   = ld.get_pitching_leaders('p_w',   season=season, num=1, teams=abbrs)
        era_rows = ld.get_pitching_leaders('p_era', season=season, num=1, teams=abbrs)
        k_rows   = ld.get_pitching_leaders('p_k',   season=season, num=1, teams=abbrs)
        crown = _names(w_rows) & _names(era_rows) & _names(k_rows)
        for first, last in crown:
            winners.append({
                'season': season,
                'first':  first,
                'last':   last,
                'p_w':   int(w_rows.loc[(w_rows['First Name'] == first) & (w_rows['Last Name'] == last)].iloc[0]['p_w']),
                'p_era': era_rows.loc[(era_rows['First Name'] == first) & (era_rows['Last Name'] == last)].iloc[0]['p_era'],
                'p_k':   int(k_rows.loc[(k_rows['First Name'] == first) & (k_rows['Last Name'] == last)].iloc[0]['p_k']),
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
            (bat_module.stats['season'] == season) &
            (bat_module.stats['stat_type'] == 'season')
        ].copy()
        if abbrs is not None:
            df = df[df['team'].isin(abbrs)]
        if df.empty:
            continue

        qualified   = df[df['pa'] >= BAT_SEASON_MIN_PA]
        unqualified = df[df['pa'] < BAT_SEASON_MIN_PA]

        best_qual_avg = qualified['avg'].max() if not qualified.empty else -1.0

        candidates = []
        for _, row in qualified.iterrows():
            candidates.append((row['avg'], row, False))
        for _, row in unqualified.iterrows():
            extra     = int(BAT_SEASON_MIN_PA - row['pa'])
            adj_avg   = row['h'] / (row['ab'] + extra)
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
                    'AVG':         row['avg'],
                    'PA':          int(row['pa']),
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
            (pit_module.stats['season'] == season) &
            (pit_module.stats['stat_type'] == 'season') &
            (pit_module.stats['p_ip'] >= PIT_SEASON_MIN_IP)
        ].copy()
        if abbrs is not None:
            df = df[df['team'].isin(abbrs)]
        if df.empty:
            continue

        best = df['p_era'].min()
        for _, row in df[df['p_era'] == best].iterrows():
            winners.append({
                'season':  season,
                'first':   row['First Name'],
                'last':    row['Last Name'],
                'ERA':     row['p_era'],
                'IP_true': row['p_ip'],
            })

    return sorted(winners, key=lambda w: w['season'])


def hr_sb_club(threshold):
    """Return all season rows where HR >= threshold and SB >= threshold, sorted by season then HR desc.

    Keys: season, first, last, HR, SB, AVG, team
    """
    import batting as bat_module
    df = bat_module.stats[bat_module.stats['stat_type'] == 'season'].copy()
    df = df[(df['hr'] >= threshold) & (df['sb'] >= threshold)]
    results = []
    for _, row in df.iterrows():
        results.append({
            'season': row['season'],
            'first':  row['First Name'],
            'last':   row['Last Name'],
            'HR':     int(row['hr']),
            'SB':     int(row['sb']),
            'AVG':    row['avg'],
            'team':   row['team'],
        })
    return sorted(results, key=lambda r: (r['season'], -r['HR']))


def pitching_triple_crown():
    """Return list of dicts for each pitching triple crown winner.

    Keys: season, first, last, W, ERA, K
    """
    winners = []
    for season in SEASON_RANGE:
        w_rows   = ld.get_pitching_leaders('p_w',   season=season, num=1)
        era_rows = ld.get_pitching_leaders('p_era', season=season, num=1)
        k_rows   = ld.get_pitching_leaders('p_k',   season=season, num=1)
        crown = _names(w_rows) & _names(era_rows) & _names(k_rows)
        for first, last in crown:
            winners.append({
                'season': season,
                'first':  first,
                'last':   last,
                'p_w':   int(w_rows.loc[(w_rows['First Name'] == first) & (w_rows['Last Name'] == last)].iloc[0]['p_w']),
                'p_era': era_rows.loc[(era_rows['First Name'] == first) & (era_rows['Last Name'] == last)].iloc[0]['p_era'],
                'p_k':   int(k_rows.loc[(k_rows['First Name'] == first) & (k_rows['Last Name'] == last)].iloc[0]['p_k']),
            })
    return sorted(winners, key=lambda w: w['season'])
