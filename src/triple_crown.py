"""Calculate batting and pitching triple crown winners by season."""
from constants import SEASON_RANGE, BAT_SEASON_MIN_PA, PIT_SEASON_MIN_IP
import leaders as ld
from data import teams as teams_data


def _pids(df):
    return set(df['player_id'])


def batting_triple_crown():
    """Return list of dicts for each batting triple crown winner.

    Keys: season, player_id, avg, hr, rbi
    """
    winners = []
    for season in SEASON_RANGE:
        avg_rows = ld.get_leaders('avg', season=season, num=1)
        hr_rows  = ld.get_leaders('hr',  season=season, num=1)
        rbi_rows = ld.get_leaders('rbi', season=season, num=1)
        crown = _pids(avg_rows) & _pids(hr_rows) & _pids(rbi_rows)
        avg_idx = avg_rows.set_index('player_id')
        hr_idx  = hr_rows.set_index('player_id')
        rbi_idx = rbi_rows.set_index('player_id')
        for pid in crown:
            winners.append({
                'season':    season,
                'player_id': pid,
                'avg': avg_idx.loc[pid, 'avg'],
                'hr':  hr_idx.loc[pid, 'hr'],
                'rbi': rbi_idx.loc[pid, 'rbi'],
            })
    return sorted(winners, key=lambda w: w['season'])


def _conf_abbrs(conference):
    return set(teams_data.teams[teams_data.teams['conference_name'] == conference]['abbr'])


def batting_triple_crown_conf(conference):
    """Return batting triple crown winners restricted to teams in the given conference."""
    abbrs = _conf_abbrs(conference)
    winners = []
    for season in SEASON_RANGE:
        avg_rows = ld.get_leaders('avg', season=season, num=1, teams=abbrs)
        hr_rows  = ld.get_leaders('hr',  season=season, num=1, teams=abbrs)
        rbi_rows = ld.get_leaders('rbi', season=season, num=1, teams=abbrs)
        crown = _pids(avg_rows) & _pids(hr_rows) & _pids(rbi_rows)
        avg_idx = avg_rows.set_index('player_id')
        hr_idx  = hr_rows.set_index('player_id')
        rbi_idx = rbi_rows.set_index('player_id')
        for pid in crown:
            winners.append({
                'season':    season,
                'player_id': pid,
                'avg': avg_idx.loc[pid, 'avg'],
                'hr':  hr_idx.loc[pid, 'hr'],
                'rbi': rbi_idx.loc[pid, 'rbi'],
            })
    return sorted(winners, key=lambda w: w['season'])


def pitching_triple_crown_conf(conference):
    """Return pitching triple crown winners restricted to teams in the given conference."""
    abbrs = _conf_abbrs(conference)
    winners = []
    for season in SEASON_RANGE:
        w_rows   = ld.get_leaders('p_w',   season=season, num=1, teams=abbrs)
        era_rows = ld.get_leaders('p_era', season=season, num=1, teams=abbrs)
        k_rows   = ld.get_leaders('p_k',   season=season, num=1, teams=abbrs)
        crown = _pids(w_rows) & _pids(era_rows) & _pids(k_rows)
        w_idx   = w_rows.set_index('player_id')
        era_idx = era_rows.set_index('player_id')
        k_idx   = k_rows.set_index('player_id')
        for pid in crown:
            winners.append({
                'season':    season,
                'player_id': pid,
                'p_w':   w_idx.loc[pid, 'p_w'],
                'p_era': era_idx.loc[pid, 'p_era'],
                'p_k':   k_idx.loc[pid, 'p_k'],
            })
    return sorted(winners, key=lambda w: w['season'])


def batting_title(conference=None):
    """Return one dict per season for the batting title winner(s).

    Keys: season, player_id, avg, pa, unqualified
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
            extra     = BAT_SEASON_MIN_PA - row['pa']
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
                    'player_id':   row['player_id'],
                    'avg':         row['avg'],
                    'pa':          row['pa'],
                    'unqualified': unqual,
                })

    return sorted(winners, key=lambda w: w['season'])


def era_title(conference=None):
    """Return one dict per season for the ERA title winner(s).

    Keys: season, player_id, p_era, p_ip
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
                'season':    season,
                'player_id': row['player_id'],
                'p_era':     row['p_era'],
                'p_ip':      row['p_ip'],
            })

    return sorted(winners, key=lambda w: w['season'])


def hr_sb_club(threshold):
    """Return all season rows where HR >= threshold and SB >= threshold, sorted by season then HR desc.

    Keys: season, player_id, hr, sb, avg, team
    """
    import batting as bat_module
    df = bat_module.stats[bat_module.stats['stat_type'] == 'season'].copy()
    df = df[(df['hr'] >= threshold) & (df['sb'] >= threshold)]
    results = []
    for _, row in df.iterrows():
        results.append({
            'season':    row['season'],
            'player_id': row['player_id'],
            'hr':        row['hr'],
            'sb':        row['sb'],
            'avg':       row['avg'],
            'team':      row['team'],
        })
    return sorted(results, key=lambda r: (r['season'], -r['hr']))


def pitching_triple_crown():
    """Return list of dicts for each pitching triple crown winner.

    Keys: season, player_id, p_w, p_era, p_k
    """
    winners = []
    for season in SEASON_RANGE:
        w_rows   = ld.get_leaders('p_w',   season=season, num=1)
        era_rows = ld.get_leaders('p_era', season=season, num=1)
        k_rows   = ld.get_leaders('p_k',   season=season, num=1)
        crown = _pids(w_rows) & _pids(era_rows) & _pids(k_rows)
        w_idx   = w_rows.set_index('player_id')
        era_idx = era_rows.set_index('player_id')
        k_idx   = k_rows.set_index('player_id')
        for pid in crown:
            winners.append({
                'season':    season,
                'player_id': pid,
                'p_w':   w_idx.loc[pid, 'p_w'],
                'p_era': era_idx.loc[pid, 'p_era'],
                'p_k':   k_idx.loc[pid, 'p_k'],
            })
    return sorted(winners, key=lambda w: w['season'])
