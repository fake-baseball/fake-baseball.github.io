"""
List of all statistics tracked in BFBL.

Each entry describes a computed stat column.

Name stuff:
  key         - abbreviation for the stat
  name        - full name of the stat
  description - description for the stat (e.g. how it's calculated)

Comparison stuff:
  qualified - minimum playing time (e.g. PA, IP) required for leaders (default: False)
  lowest    - if True, lower is better (default: False)

Display stuff:
  decimal_places - digits after the decimal point when formatting; default 0
  leading_zero   - show or strip leading zero, e.g. .247 instead of 0.247 (default: True)
  display_col    - override display column name, e.g. IP_true -> IP (default: None)
  percentage     - multiply by 100 before formatting (default: False)

Leaders pages:
  slug       - URL slug for the best leaders page
  slug_worst - if True, also generate a worst-version leaders page
"""

# -- Batting (hitting) ----------------------------------------------------------

BATTING_STATS = {
    # -- Value ------------------------------------------------------------------
    'WAR':   {
        'name': 'WAR for Position Players',
        'description': '',
        'decimal_places': 1,
        'slug': 'war_batters',
    },
    # -- Counting ---------------------------------------------------------------
    'GP':    {
        'name': 'Games Played',
        'description': '',
    },
    'GB':    {
        'name': 'Games Batted',
        'description': '',
        'slug': 'gb',
    },
    'PA':    {
        'name': 'Plate Appearances',
        'description': '',
        'slug': 'pa',
    },
    'AB':    {
        'name': 'At Bats',
        'description': '',
        'slug': 'ab',
    },
    'H':     {
        'name': 'Hits',
        'description': '',
        'slug': 'h',
    },
    '1B':    {
        'name': 'Singles',
        'description': '',
        'slug': '1b',
    },
    '2B':    {
        'name': 'Doubles',
        'description': '',
        'slug': '2b',
    },
    '3B':    {
        'name': 'Triples',
        'description': '',
        'slug': '3b',
    },
    'HR':    {
        'name': 'Home Runs',
        'description': '',
        'slug': 'hr',
    },
    'R':     {
        'name': 'Runs Scored',
        'description': '',
        'slug': 'r',
    },
    'RBI':   {
        'name': 'Runs Batted In',
        'description': '',
        'slug': 'rbi',
    },
    'BB':    {
        'name': 'Walks',
        'description': '',
        'slug': 'bb',
    },
    'K':     {
        'name': 'Strikeouts',
        'description': '',
        'slug': 'k',
    },
    'SH':    {
        'name': 'Sacrifice Hits',
        'description': '',
        'slug': 'sh',
    },
    'SF':    {
        'name': 'Sacrifice Flies',
        'description': '',
        'slug': 'sf',
    },
    'HBP':   {
        'name': 'Hit By Pitch',
        'description': '',
        'slug': 'hbp',
    },
    'TB':    {
        'name': 'Total Bases',
        'description': '',
        'slug': 'tb',
    },
    'XBH':   {
        'name': 'Extra Base Hits',
        'description': '',
        'slug': 'xbh',
    },
    'BIP':   {
        'name': 'Balls in Play',
        'description': '',
    },
    # -- Rate -------------------------------------------------------------------
    'AVG':   {
        'name': 'Batting Average',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'avg', 'slug_worst': True
    },
    'OBP':   {
        'name': 'On-Base Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'obp', 'slug_worst': True
    },
    'SLG':   {
        'name': 'Slugging Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'slg', 'slug_worst': True
    },
    'OPS':   {
        'name': 'On-Base Plus Slugging',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'ops', 'slug_worst': True
    },
    'OPS+':  {
        'name': 'OPS+',
        'description': '',
        'qualified': True,
        'slug': 'ops_plus',
    },
    'ISO':   {
        'name': 'Isolated Power',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'iso',
    },
    'BABIP': {
        'name': 'Batting Average on Balls in Play',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'babip',
    },
    'wOBA':  {
        'name': 'Weighted On-Base Average',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'woba',
    },
    'wRC':   {
        'name': 'Weighted Runs Created',
        'description': '',
        'decimal_places': 1,
    },
    'wRC+':  {
        'name': 'wRC+',
        'description': '',
        'qualified': True,
        'slug': 'wrc_plus',
    },
    # -- Rate (%) / per --------------------------------------------------------
    'HR%':   {
        'name': 'Home Run Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'hrb_pct', 'slug_worst': True,
    },
    'K%':    {
        'name': 'Strikeout Rate',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'kb_pct', 'slug_worst': True,
    },
    'BB%':   {
        'name': 'Walk Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'bbb_pct', 'slug_worst': True,
    },
    'PA/HR': {
        'name': 'Plate Appearances per Home Run',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'slug': 'pa_per_hr',
    },
    'R/G':   {
        'name': 'Runs per Game',
        'description': '',
        'decimal_places': 2,
    },
    'PA/GB': {
        'name': 'Plate Appearances per Games Batted',
        'description': '',
        'qualified': True,
        'decimal_places': 2,
        'slug': 'pa_per_gb',
    },
    'XBH%':  {
        'name': 'Extra Base Hit Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'xbh_pct',
    },
    'RS%':   {
        'name': 'Run Scored Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'rs_pct',
    },
    'RC%':   {
        'name': 'Run Created Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'rc_pct',
    },
    # -- Value ------------------------------------------------------------------
    'Rbat':  {
        'name': 'Batting Runs',
        'description': '',
        'decimal_places': 1,
    },
    'Rbr':   {
        'name': 'Baserunning Runs',
        'description': '',
        'decimal_places': 1,
    },
    'Rdef':  {
        'name': 'Defensive Runs',
        'description': '',
        'decimal_places': 1,
    },
    'Rpos':  {
        'name': 'Positional Adjustment Runs',
        'description': '',
        'decimal_places': 1,
    },
    'Rcorr': {
        'name': 'Correction Runs',
        'description': '',
        'decimal_places': 1,
    },
    'RAA':   {
        'name': 'Runs Above Average',
        'description': '',
        'decimal_places': 1,
    },
    'WAA':   {
        'name': 'Wins Above Average',
        'description': '',
        'decimal_places': 1,
    },
    'RAR':   {
        'name': 'Runs Above Replacement',
        'description': '',
        'decimal_places': 1,
    },
    'Rrep':  {
        'name': 'Replacement Run Credit',
        'description': '',
        'decimal_places': 1,
    },
}

# -- Baserunning ----------------------------------------------------------------

BASERUNNING_STATS = {
    # -- Counting ---------------------------------------------------------------
    'SB':     {
        'name': 'Stolen Bases',
        'description': '',
        'slug': 'sb',
    },
    'CS':     {
        'name': 'Caught Stealing',
        'description': '',
        'slug': 'cs',
    },
    'SBatt':  {
        'name': 'Stolen Base Attempts',
        'description': '',
        'slug': 'sbatt',
    },
    # -- Rate -------------------------------------------------------------------
    'SB%':    {
        'name': 'Stolen Base Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'sb_pct', 'slug_worst': True
    },
    'SbAtt%': {
        'name': 'Stolen Base Attempt Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'sbatt_pct',
    },
}

# -- Fielding (position players) ------------------------------------------------

FIELDING_STATS = {
    # -- Counting ---------------------------------------------------------------
    'E':      {
        'name': 'Errors',
        'description': '',
        'slug': 'e',
    },
    'PB':     {
        'name': 'Passed Balls',
        'description': '',
        'slug': 'pb',
    },
    'GF':     {
        'name': 'Fielding Games',
        'description': '',
        'decimal_places': 1,
    },
    # -- Rate -------------------------------------------------------------------
    'E/GF':   {
        'name': 'Errors per Fielding Game',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
    },
    'PB/GF':  {
        'name': 'Passed Balls per Fielding Game',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
    },
}

# -- Pitching -------------------------------------------------------------------

PITCHING_STATS = {
    # -- Counting ---------------------------------------------------------------
    'WAR':    {
        'name': 'WAR for Pitchers',
        'description': '',
        'decimal_places': 1,
        'slug': 'war_pitchers',
    },
    'W':      {
        'name': 'Wins',
        'description': '',
        'slug': 'p_w',
    },
    'L':      {
        'name': 'Losses',
        'description': '',
        'slug': 'p_l',
    },
    'GP':     {
        'name': 'Games Pitched',
        'description': '',
        'slug': 'p_gp',
    },
    'GS':     {
        'name': 'Games Started',
        'description': '',
        'slug': 'p_gs',
    },
    'GR':     {
        'name': 'Games in Relief',
        'description': '',
    },
    'IP_true': {
        'name': 'Innings Pitched',
        'description': '',
        'decimal_places': 1,
        'display_col': 'IP', 'slug': 'p_ip',
    },
    'CG':     {
        'name': 'Complete Games',
        'description': '',
        'slug': 'p_cg',
    },
    'SHO':    {
        'name': 'Shutouts',
        'description': '',
        'slug': 'p_sho',
    },
    'SV':     {
        'name': 'Saves',
        'description': '',
        'slug': 'p_sv',
    },
    'K':      {
        'name': 'Strikeouts',
        'description': '',
        'slug': 'p_k',
    },
    'BB':     {
        'name': 'Walks',
        'description': '',
        'slug': 'p_bb',
    },
    'H':      {
        'name': 'Hits Allowed',
        'description': '',
        'slug': 'p_h',
    },
    'ER':     {
        'name': 'Earned Runs Allowed',
        'description': '',
        'slug': 'p_er',
    },
    'HR':     {
        'name': 'Home Runs Allowed',
        'description': '',
        'slug': 'p_hr',
    },
    'HBP':    {
        'name': 'Hit Batters',
        'description': '',
        'slug': 'p_hbp',
    },
    'TP':     {
        'name': 'Total Pitches',
        'description': '',
        'slug': 'p_tp',
    },
    'BF':     {
        'name': 'Batters Faced',
        'description': '',
        'slug': 'p_bf',
    },
    'RA':     {
        'name': 'Runs Allowed',
        'description': '',
        'slug': 'p_ra',
    },
    'WP':     {
        'name': 'Wild Pitches',
        'description': '',
        'slug': 'p_wp',
    },
    'BIP':    {
        'name': 'Balls in Play Against',
        'description': '',
    },
    # -- Rate -------------------------------------------------------------------
    'ERA':    {
        'name': 'Earned Run Average',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'slug': 'p_era', 'slug_worst': True,
    },
    'ERA-':   {
        'name': 'ERA-',
        'description': '',
        'qualified': True, 'lowest': True,
        'slug': 'p_era_minus',
    },
    'RA9':    {
        'name': 'Runs Allowed per 9 Innings',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'slug': 'p_ra9',
    },
    'RA9def': {
        'name': 'Defense-Adjusted RA9',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'slug': 'p_ra9def',
    },
    'WHIP':   {
        'name': 'Walks and Hits per Inning',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'slug': 'p_whip',
    },
    'FIP':    {
        'name': 'Fielding Independent Pitching',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'slug': 'p_fip',
    },
    'BAA':    {
        'name': 'Batting Average Against',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'p_baa',
    },
    'OBPA':   {
        'name': 'On-Base Percentage Against',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'p_obpa',
    },
    'BABIP':  {
        'name': 'BABIP Against',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
        'slug': 'p_babip', 'slug_worst': True,
    },
    'WIN%':   {
        'name': 'Win Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'p_win_pct', 'slug_worst': True,
    },
    'SV%':    {
        'name': 'Save Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'p_sv_pct',
    },
    'K/9':    {
        'name': 'Strikeouts per 9 Innings',
        'description': '',
        'qualified': True,
        'decimal_places': 1,
        'slug': 'p_k9', 'slug_worst': True,
    },
    'H/9':    {
        'name': 'Hits per 9 Innings',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'slug': 'p_h9', 'slug_worst': True,
    },
    'HR/9':   {
        'name': 'Home Runs per 9 Innings',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'slug': 'p_hr9', 'slug_worst': True,
    },
    'BB/9':   {
        'name': 'Walks per 9 Innings',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'slug': 'p_bb9', 'slug_worst': True,
    },
    'K/BB':   {
        'name': 'Strikeout-to-Walk Ratio',
        'description': '',
        'qualified': True,
        'decimal_places': 2,
        'slug': 'p_kbb',
    },
    'K%':     {
        'name': 'Strikeout Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'p_k_pctb', 'slug_worst': True,
    },
    'BB%':    {
        'name': 'Walk Rate',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1, 'percentage': True,
        'slug': 'p_bb_pctb', 'slug_worst': True,
    },
    'HR%':    {
        'name': 'Home Run Rate',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1, 'percentage': True,
    },
    'P/GP':   {
        'name': 'Pitches per Game',
        'description': '',
        'qualified': True,
        'decimal_places': 1,
        'slug': 'p_pgp',
    },
    'P/IP':   {
        'name': 'Pitches per Inning',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'slug': 'p_pip',
    },
    'P/PA':   {
        'name': 'Pitches per Plate Appearance',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'slug': 'p_ppa',
    },
    'IP/GP':  {
        'name': 'Innings per Game',
        'description': '',
        'qualified': True,
        'decimal_places': 1,
        'slug': 'p_ipgp',
    },
    # -- Value ------------------------------------------------------------------
    'Rdef':   {
        'name': 'Defense Adjustment',
        'description': '',
        'decimal_places': 1,
    },
    'RAA':    {
        'name': 'Runs Above Average',
        'description': '',
        'decimal_places': 1,
    },
    'Rlev':   {
        'name': 'Leverage Runs',
        'description': '',
        'decimal_places': 1,
    },
    'RAAlev': {
        'name': 'Leverage-Adjusted Runs Above Average',
        'description': '',
        'decimal_places': 1,
    },
    'WAA':    {
        'name': 'Wins Above Average',
        'description': '',
        'decimal_places': 1,
    },
    'Rrep':   {
        'name': 'Replacement Run Credit',
        'description': '',
        'decimal_places': 1,
    },
    'RAR':    {
        'name': 'Runs Above Replacement',
        'description': '',
        'decimal_places': 1,
    },
    'Rcorr':   {
        'name': 'Correction Runs',
        'description': '',
        'decimal_places': 1,
    },
}

# -- Fill in defaults -----------------------------------------------------------

_DEFAULTS = {
    'qualified':      False,
    'lowest':         False,
    'decimal_places': 0,
    'leading_zero':   True,
    'display_col':    None,
    'slug':           None,
    'slug_worst':     False,
    'percentage':     False,
}

for _stat_dict in (BATTING_STATS, BASERUNNING_STATS, FIELDING_STATS, PITCHING_STATS):
    for _meta in _stat_dict.values():
        for _key, _val in _DEFAULTS.items():
            _meta.setdefault(_key, _val)

for _meta in BATTING_STATS.values():     _meta.setdefault('qual_col', 'PA')
for _meta in BASERUNNING_STATS.values(): _meta.setdefault('qual_col', 'SBatt')
for _meta in FIELDING_STATS.values():    _meta.setdefault('qual_col', 'GF')
for _meta in PITCHING_STATS.values():    _meta.setdefault('qual_col', 'IP_true')
