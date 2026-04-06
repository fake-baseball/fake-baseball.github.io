"""
List of all statistics tracked in BFBL.

Each entry describes a computed stat column.

Name stuff:
  key         - identifier key for the stat (Python-identifier-safe); used as URL slug
  name        - display header (e.g. 'K%', 'wRC+', 'OPS+'); defaults to key
  label       - full human-readable name (e.g. 'Strikeout Rate')
  description - description for the stat (e.g. how it's calculated)

Comparison stuff:
  qualified - minimum playing time (e.g. PA, IP) required for leaders (default: False)
  lowest    - if True, lower is better (default: False)

Display stuff:
  decimal_places - digits after the decimal point when formatting; default 0
  leading_zero   - show or strip leading zero, e.g. .247 instead of 0.247 (default: True)
  percentage     - multiply by 100 before formatting (default: False)

Leaders pages:
  leaders   - if True, generate a leaders page (key is used as URL slug)
  has_worst - if True, also generate a worst-version leaders page

Context:
  context - 'batting', 'baserunning', 'fielding', 'pitching', or 'meta'
"""

REGISTRY = {

    # =========================================================================
    # Batting (context: 'batting')
    # =========================================================================

    # -- Value -----------------------------------------------------------------
    'war': {
        'name': 'WAR',
        'label': 'Wins Above Replacement',
        'description': '',
        'decimal_places': 1,
        'leaders': True, 'has_worst': True,
        'context': 'batting',
    },
    # -- Counting --------------------------------------------------------------
    'b_gp': {
        'name': 'GP',
        'label': 'Games Rostered',
        'description': '',
        'context': 'batting',
    },
    'gb': {
        'name': 'G',
        'label': 'Games Appeared',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'pa': {
        'name': 'PA',
        'label': 'Plate Appearances',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'ab': {
        'name': 'AB',
        'label': 'At Bats',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'h': {
        'name': 'H',
        'label': 'Hits',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'b_1b': {
        'name': '1B',
        'label': 'Singles',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'b_2b': {
        'name': '2B',
        'label': 'Doubles',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'b_3b': {
        'name': '3B',
        'label': 'Triples',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'hr': {
        'name': 'HR',
        'label': 'Home Runs',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'r': {
        'name': 'R',
        'label': 'Runs Scored',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'rbi': {
        'name': 'RBI',
        'label': 'Runs Batted In',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'bb': {
        'name': 'BB',
        'label': 'Bases on Balls',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'k': {
        'name': 'K',
        'label': 'Strikeouts',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'sh': {
        'name': 'SH',
        'label': 'Sacrifice Hits',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'sf': {
        'name': 'SF',
        'label': 'Sacrifice Flies',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'hbp': {
        'name': 'HBP',
        'label': 'Hit By Pitch',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'tb': {
        'name': 'TB',
        'label': 'Total Bases',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'xbh': {
        'name': 'XBH',
        'label': 'Extra Base Hits',
        'description': '',
        'leaders': True,
        'context': 'batting',
    },
    'bip': {
        'name': 'BIP',
        'label': 'Balls in Play',
        'description': '',
        'context': 'batting',
    },
    # -- Rate ------------------------------------------------------------------
    'avg': {
        'name': 'AVG',
        'label': 'Batting Average',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True, 'has_worst': True,
        'context': 'batting',
    },
    'obp': {
        'name': 'OBP',
        'label': 'On-Base Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True, 'has_worst': True,
        'context': 'batting',
    },
    'slg': {
        'name': 'SLG',
        'label': 'Slugging Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True, 'has_worst': True,
        'context': 'batting',
    },
    'ops': {
        'name': 'OPS',
        'label': 'On-Base Plus Slugging',
        'description': 'OBP + SLG',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True, 'has_worst': True,
        'context': 'batting',
    },
    'ops_plus': {
        'name': 'OPS+',
        'label': 'Adjusted OPS',
        'description': 'Measures a player\'s OPS relative to league average, considering park factor. 100 = league average, higher is better.',
        'qualified': True,
        'leaders': True,
        'context': 'batting',
    },
    'iso': {
        'name': 'ISO',
        'label': 'Isolated Power',
        'description': 'SLG - AVG',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True,
        'context': 'batting',
    },
    'babip': {
        'name': 'BABIP',
        'label': 'Batting Average on Balls in Play',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True,
        'context': 'batting',
    },
    'woba': {
        'name': 'wOBA',
        'label': 'Weighted On-Base Average',
        'description': '',
        'qualified': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True,
        'context': 'batting',
    },
    'wrc': {
        'name': 'wRC',
        'label': 'Weighted Runs Created',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'wrc_plus': {
        'name': 'wRC+',
        'label': 'Adjusted Weighted Runs Created',
        'description': '',
        'qualified': True,
        'leaders': True,
        'context': 'batting',
    },
    # -- Rate (%) / per --------------------------------------------------------
    'hr_pct': {
        'name': 'HR%',
        'label': 'Home Run Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True, 'has_worst': True,
        'context': 'batting',
    },
    'k_pct': {
        'name': 'K%',
        'label': 'Strikeout Rate',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True, 'has_worst': True,
        'context': 'batting',
    },
    'bb_pct': {
        'name': 'BB%',
        'label': 'Walk Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True, 'has_worst': True,
        'context': 'batting',
    },
    'pa_per_hr': {
        'name': 'PA/HR',
        'label': 'Plate Appearances per Home Run',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'leaders': True,
        'context': 'batting',
    },
    'r_per_g': {
        'name': 'R/G',
        'label': 'Runs per Game',
        'description': '',
        'decimal_places': 2,
        'context': 'batting',
    },
    'pa_per_gb': {
        'name': 'PA/G',
        'label': 'Plate Appearances per Game',
        'description': '',
        'qualified': True,
        'decimal_places': 2,
        'leaders': True,
        'context': 'batting',
    },
    'xbh_pct': {
        'name': 'XBH%',
        'label': 'Extra Base Hit Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True,
        'context': 'batting',
    },
    'rs_pct': {
        'name': 'RS%',
        'label': 'Run Scored Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True,
        'context': 'batting',
    },
    'rc_pct': {
        'name': 'RC%',
        'label': 'Run Created Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True,
        'context': 'batting',
    },
    # -- League context (season aggregates, not player-facing) -----------------
    'lg_wsb': {
        'name': 'lg_wSB',
        'label': 'League wSB Rate',
        'description': 'League-average value of a stolen base attempt, used to compute Rbr',
        'decimal_places': 3,
        'context': 'batting',
    },
    'r_per_w': {
        'name': 'R/W',
        'label': 'Runs per Win',
        'description': 'Runs required to add one win, scaled to season run environment',
        'decimal_places': 2,
        'context': 'batting',
    },
    'rw_per_pa': {
        'name': 'RW/PA',
        'label': 'Replacement Wins per PA',
        'description': 'Number of wins a replacement level player would contribute per plate appearance.',
        'decimal_places': 4,
        'context': 'batting',
    },
    'rr_per_pa': {
        'name': 'RR/PA',
        'label': 'Replacement Runs per PA',
        'description': 'Number of runs a replacement level player would contribute per plate appearance.',
        'decimal_places': 4,
        'context': 'batting',
    },
    'r_per_pa': {
        'name': 'R/PA',
        'label': 'Runs per Plate Appearance',
        'description': 'League average runs scored per plate appearance',
        'decimal_places': 3,
        'context': 'batting',
    },
    # -- Value (WAR components) ------------------------------------------------
    'r_bat': {
        'name': 'Rbat',
        'label': 'Batting Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'r_br': {
        'name': 'Rbr',
        'label': 'Baserunning Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'r_def': {
        'name': 'Rdef',
        'label': 'Defensive Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'r_pos': {
        'name': 'Rpos',
        'label': 'Positional Adjustment Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'r_corr': {
        'name': 'Rcorr',
        'label': 'Correction Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'raa': {
        'name': 'RAA',
        'label': 'Runs Above Average',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'waa': {
        'name': 'WAA',
        'label': 'Wins Above Average',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'rar': {
        'name': 'RAR',
        'label': 'Runs Above Replacement',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },
    'r_rep': {
        'name': 'Rrep',
        'label': 'Replacement Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'batting',
    },

    # =========================================================================
    # Baserunning (context: 'baserunning')
    # =========================================================================

    # -- Counting --------------------------------------------------------------
    'sb': {
        'name': 'SB',
        'label': 'Stolen Bases',
        'description': '',
        'leaders': True,
        'context': 'baserunning',
    },
    'cs': {
        'name': 'CS',
        'label': 'Caught Stealing',
        'description': '',
        'leaders': True,
        'context': 'baserunning',
    },
    'sb_att': {
        'name': 'SBatt',
        'label': 'Stolen Base Attempts',
        'description': '',
        'leaders': True,
        'context': 'baserunning',
    },
    # -- Rate ------------------------------------------------------------------
    'sb_pct': {
        'name': 'SB%',
        'label': 'Stolen Base Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True, 'has_worst': True,
        'context': 'baserunning',
    },
    'sb_att_pct': {
        'name': 'SBatt%',
        'label': 'Stolen Base Attempt Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True,
        'context': 'baserunning',
    },

    # =========================================================================
    # Fielding (context: 'fielding')
    # =========================================================================

    # -- Counting --------------------------------------------------------------
    'e': {
        'name': 'E',
        'label': 'Errors',
        'description': '',
        'leaders': True,
        'context': 'fielding',
    },
    'pb': {
        'name': 'PB',
        'label': 'Passed Balls',
        'description': '',
        'leaders': True,
        'context': 'fielding',
    },
    'gf': {
        'name': 'GF',
        'label': 'Games Fielded',
        'description': '',
        'decimal_places': 1,
        'context': 'fielding',
    },
    # -- Rate ------------------------------------------------------------------
    'e_per_gf': {
        'name': 'E/GF',
        'label': 'Errors per Game Fielded',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
        'context': 'fielding',
    },
    'pb_per_gf': {
        'name': 'PB/GF',
        'label': 'Passed Balls per Game Fielded',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
        'context': 'fielding',
    },

    # =========================================================================
    # Pitching (context: 'pitching')
    # =========================================================================

    # -- Value -----------------------------------------------------------------
    'p_war': {
        'name': 'WAR',
        'label': 'Wins Above Replacement',
        'description': '',
        'decimal_places': 1,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    # -- Cy Young Predictor ----------------------------------------------------
    'p_cyp': {
        'name': 'CYP',
        'label': 'Cy Young Points (Bill James\'s formula)',
        'description': '((5*IP/9)-ER) + (K/12) + (SV*2.5) + SHO + ((W*6)-(L*2)) + (VB*12)',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_cyp2': {
        'name': 'CYP2',
        'label': 'Cy Young Points (Tom Tango\'s formula)',
        'description': 'IP/2 - ER + K/10 + W',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_cyp3': {
        'name': 'CYP3',
        'label': 'Cy Young Points (Tom Tango\'s updated formula)',
        'description': 'IP/2 - FIPruns + K/10 + W',
        'decimal_places': 1,
        'context': 'pitching',
    },
    # -- Victory Bonus ---------------------------------------------------------
    'p_vb': {
        'name': 'VB',
        'label': 'Victory Bonus',
        'description': '1 if the pitcher\'s team won their division that season, else 0',
        'context': 'pitching',
    },
    # -- Counting --------------------------------------------------------------
    'p_w': {
        'name': 'W',
        'label': 'Wins',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_l': {
        'name': 'L',
        'label': 'Losses',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_gp': {
        'name': 'G',
        'label': 'Games Pitched',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_gs': {
        'name': 'GS',
        'label': 'Games Started',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_gr': {
        'name': 'GR',
        'label': 'Games in Relief',
        'description': '',
        'context': 'pitching',
    },
    'p_ip': {
        'name': 'IP',
        'label': 'Innings Pitched',
        'description': '',
        'decimal_places': 1,
        'type': 'ip',
        'leaders': True,
        'context': 'pitching',
    },
    'p_cg': {
        'name': 'CG',
        'label': 'Complete Games',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_sho': {
        'name': 'SHO',
        'label': 'Shutouts',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_sv': {
        'name': 'SV',
        'label': 'Saves',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_k': {
        'name': 'K',
        'label': 'Strikeouts',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_bb': {
        'name': 'BB',
        'label': 'Bases on Balls',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_h': {
        'name': 'H',
        'label': 'Hits Allowed',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_er': {
        'name': 'ER',
        'label': 'Earned Runs Allowed',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_hr': {
        'name': 'HR',
        'label': 'Home Runs Allowed',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_hbp': {
        'name': 'HBP',
        'label': 'Hit by Pitch',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_tp': {
        'name': 'TP',
        'label': 'Total Pitches',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_bf': {
        'name': 'BF',
        'label': 'Batters Faced',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_ra': {
        'name': 'R',
        'label': 'Runs Allowed',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_wp': {
        'name': 'WP',
        'label': 'Wild Pitches',
        'description': '',
        'leaders': True,
        'context': 'pitching',
    },
    'p_bip': {
        'name': 'BIP',
        'label': 'Balls in Play',
        'description': '',
        'context': 'pitching',
    },
    # -- Rate ------------------------------------------------------------------
    'p_era': {
        'name': 'ERA',
        'label': 'Earned Run Average',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_era_minus': {
        'name': 'ERA-',
        'label': 'Adjusted ERA',
        'description': '',
        'qualified': True, 'lowest': True,
        'leaders': True,
        'context': 'pitching',
    },
    'p_ra9': {
        'name': 'RA9',
        'label': 'Runs Allowed per 9 Innings',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'leaders': True,
        'context': 'pitching',
    },
    'p_ra9_def': {
        'name': 'RA9def',
        'label': 'Defense-Adjusted RA9',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'leaders': True,
        'context': 'pitching',
    },
    'p_whip': {
        'name': 'WHIP',
        'label': 'Walks and Hits per Inning',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'leaders': True,
        'context': 'pitching',
    },
    'p_fip': {
        'name': 'FIP',
        'label': 'Fielding Independent Pitching',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'leaders': True,
        'context': 'pitching',
    },
    'p_baa': {
        'name': 'AVG',
        'label': 'Batting Average Allowed',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True,
        'context': 'pitching',
    },
    'p_obpa': {
        'name': 'OBP',
        'label': 'On-Base Percentage Allowed',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True,
        'context': 'pitching',
    },
    'p_babip': {
        'name': 'BABIP',
        'label': 'Batting Average on Balls in Play',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 3, 'leading_zero': False,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_win_pct': {
        'name': 'Win%',
        'label': 'Win Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_sv_pct': {
        'name': 'SV%',
        'label': 'Save Percentage',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True,
        'context': 'pitching',
    },
    'p_k_per_9': {
        'name': 'K/9',
        'label': 'Strikeouts per 9 Innings',
        'description': '',
        'qualified': True,
        'decimal_places': 1,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_h_per_9': {
        'name': 'H/9',
        'label': 'Hits per 9 Innings',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_hr_per_9': {
        'name': 'HR/9',
        'label': 'Home Runs per 9 Innings',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_bb_per_9': {
        'name': 'BB/9',
        'label': 'Walks per 9 Innings',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_k_per_bb': {
        'name': 'K/BB',
        'label': 'Strikeout-to-Walk Ratio',
        'description': '',
        'qualified': True,
        'decimal_places': 2,
        'leaders': True,
        'context': 'pitching',
    },
    'p_k_pct': {
        'name': 'K%',
        'label': 'Strikeout Rate',
        'description': '',
        'qualified': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_bb_pct': {
        'name': 'BB%',
        'label': 'Walk Rate',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1, 'percentage': True,
        'leaders': True, 'has_worst': True,
        'context': 'pitching',
    },
    'p_hr_pct': {
        'name': 'HR%',
        'label': 'Home Run Rate',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1, 'percentage': True,
        'context': 'pitching',
    },
    'p_p_per_gp': {
        'name': 'P/G',
        'label': 'Pitches per Game',
        'description': '',
        'qualified': True,
        'decimal_places': 1,
        'leaders': True,
        'context': 'pitching',
    },
    'p_p_per_ip': {
        'name': 'P/IP',
        'label': 'Pitches per Inning',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 1,
        'leaders': True,
        'context': 'pitching',
    },
    'p_p_per_pa': {
        'name': 'P/PA',
        'label': 'Pitches per Plate Appearance',
        'description': '',
        'qualified': True, 'lowest': True,
        'decimal_places': 2,
        'leaders': True,
        'context': 'pitching',
    },
    'p_ip_per_gp': {
        'name': 'IP/G',
        'label': 'Innings per Game',
        'description': '',
        'qualified': True,
        'decimal_places': 1,
        'leaders': True,
        'context': 'pitching',
    },
    # -- Value (WAR components) ------------------------------------------------
    'p_r_def': {
        'name': 'Rdef',
        'label': 'Defense Adjustment',
        'description': '',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_r_corr': {
        'name': 'Rcorr',
        'label': 'Correction Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_raa': {
        'name': 'RAA',
        'label': 'Runs Above Average',
        'description': '',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_waa': {
        'name': 'WAA',
        'label': 'Wins Above Average',
        'description': '',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_r_rep': {
        'name': 'Rrep',
        'label': 'Replacement Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_rar': {
        'name': 'RAR',
        'label': 'Runs Above Replacement',
        'description': '',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_r_lev': {
        'name': 'Rlev',
        'label': 'Leverage Runs',
        'description': '',
        'decimal_places': 1,
        'context': 'pitching',
    },
    'p_raa_lev': {
        'name': 'RAAlev',
        'label': 'Leverage-Adjusted Runs Above Average',
        'description': '',
        'decimal_places': 1,
        'context': 'pitching',
    },

    # -- League context (season aggregates, not player-facing) -----------------
    'p_r_per_g': {
        'name': 'R/G',
        'label': 'Runs Allowed per Game',
        'description': 'League-average runs allowed per team game',
        'decimal_places': 2,
        'context': 'pitching',
    },
    'rw_per_ip': {
        'name': 'RW/IP',
        'label': 'Replacement Wins per IP',
        'description': 'Wins per inning pitched at replacement level',
        'decimal_places': 4,
        'context': 'pitching',
    },
    'r_sv': {
        'name': 'R_sv',
        'label': 'Save Run Value',
        'description': 'Run value of recording a save',
        'decimal_places': 2,
        'context': 'pitching',
    },
    'r_no_sv': {
        'name': 'R_no_SV',
        'label': 'Non-Save Run Value',
        'description': 'Run value of a relief appearance without a save',
        'decimal_places': 2,
        'context': 'pitching',
    },

    # =========================================================================
    # Column metadata (context: 'meta')
    # Non-stat columns for render_table; no stat formatting fields.
    # =========================================================================

    'g': {
        'name': 'G',
        'label': 'Games',
        'type': 'integer',
        'context': 'meta',
    },
    'first_name': {'name': 'First Name', 'type': 'text',   'align': 'left',  'context': 'meta'},
    'last_name':  {'name': 'Last Name',  'type': 'text',   'align': 'left',  'context': 'meta'},
    'jersey':     {'name': '#', 'label': 'Jersey Number', 'type': 'integer', 'align': 'right', 'context': 'meta'},
    'salary':     {'name': 'Salary',     'type': 'salary', 'align': 'right', 'context': 'meta'},
    'rank':     {'name': 'Rank',   'type': 'integer', 'align': 'right', 'context': 'meta'},

    # ── Team standings columns ────────────────────────────────────────────────
    'team_name':     {'name': 'Team',     'type': 'team_link', 'align': 'left',  'context': 'meta'},
    't_w':           {'name': 'W',        'label': 'Wins',             'type': 'integer',   'align': 'right', 'context': 'meta'},
    't_l':           {'name': 'L',        'label': 'Losses',           'type': 'integer',   'align': 'right', 'context': 'meta'},
    't_pct':         {'name': 'Pct',      'label': 'Win Percentage',   'type': 'stat',      'align': 'right', 'decimal_places': 3, 'leading_zero': False, 'context': 'meta'},
    't_gb':          {'name': 'GB',       'label': 'Games Back',       'type': 'gb',        'align': 'right', 'context': 'meta'},
    't_rs':          {'name': 'RS',       'label': 'Runs Scored',      'type': 'integer',   'align': 'right', 'context': 'meta'},
    't_ra':          {'name': 'RA',       'label': 'Runs Against',     'type': 'integer',   'align': 'right', 'context': 'meta'},
    't_diff':        {'name': 'Diff',     'label': 'Run Differential', 'type': 'rdiff',     'align': 'right', 'context': 'meta'},
    # Split records (W-L strings)
    't_last10':      {'name': 'L10',       'label': 'Record Last 10 Games',                 'type': 'text',      'align': 'right', 'context': 'meta'},
    't_div':         {'name': 'Div',       'label': 'Record vs. Divisional Opponents',      'type': 'text',      'align': 'right', 'context': 'meta'},
    't_conf':        {'name': 'Conf',      'label': 'Record vs. Conference Opponents',      'type': 'text',      'align': 'right', 'context': 'meta'},
    't_inter':       {'name': 'Inter',     'label': 'Record vs. Interconference Opponents', 'type': 'text',      'align': 'right', 'context': 'meta'},
    't_one_run':     {'name': '1-Run',     'label': 'Record in 1-Run Games',                'type': 'text',      'align': 'right', 'context': 'meta'},
    't_blowout':     {'name': 'Blowout',   'label': 'Record in >5-Run Games',               'type': 'text',      'align': 'right', 'context': 'meta'},
    't_home':        {'name': 'Home',      'label': 'Record in Home Games',                 'type': 'text',      'align': 'right', 'context': 'meta'},
    't_away':        {'name': 'Away',      'label': 'Record in Away Games',                 'type': 'text',      'align': 'right', 'context': 'meta'},
    't_vs500':       {'name': '>.500',     'label': 'Record vs. Teams Above .500',          'type': 'text',      'align': 'right', 'context': 'meta'},
    't_first_half':  {'name': '1st',       'label': 'Record in First Half of Season',       'type': 'text',      'align': 'right', 'context': 'meta'},
    't_second_half': {'name': '2nd',       'label': 'Record in Second Half of Season',      'type': 'text',      'align': 'right', 'context': 'meta'},
    't_shutout':     {'name': 'SHO',       'label': 'Record in Shutouts',                   'type': 'text',      'align': 'right', 'context': 'meta'},
    't_sos':         {'name': 'SOS',       'label': 'Strength of Schedule (played)',         'type': 'stat',      'align': 'right', 'context': 'meta', 'decimal_places': 3, 'leading_zero': False, 'percentage': False},
    't_sos_rem':     {'name': 'SOSR',   'label': 'Strength of Schedule (remaining)',      'type': 'stat',      'align': 'right', 'context': 'meta', 'decimal_places': 3, 'leading_zero': False, 'percentage': False},
    # Game log columns
    'gl_num':        {'name': '#',         'label': 'Game Number',       'type': 'integer',   'align': 'right', 'context': 'meta'},
    'gl_ha':         {'name': 'H/A',       'label': 'Home or Away',      'type': 'text',      'align': 'center','context': 'meta'},
    'gl_opp':        {'name': 'Opp',       'label': 'Opponent Team',     'type': 'team_link', 'align': 'left',  'context': 'meta'},
    'gl_r':          {'name': 'R',         'label': 'Runs Scored',       'type': 'integer',   'align': 'right', 'context': 'meta'},
    'gl_ra':         {'name': 'RA',        'label': 'Runs Allowed',      'type': 'integer',   'align': 'right', 'context': 'meta'},
    'gl_wl':         {'name': 'W/L',       'label': 'Win or Loss',       'type': 'text',      'align': 'center','context': 'meta'},
    'gl_rec':        {'name': 'Record',    'label': 'Cumulative Record', 'type': 'text',      'align': 'right', 'context': 'meta'},
    'gl_streak':     {'name': 'Streak',    'label': 'Win/Loss Streak',   'type': 'text',      'align': 'left',  'context': 'meta'},
    'player':        {'name': 'Player',    'type': 'link',    'align': 'left',  'context': 'meta'},
    'team':          {'name': 'Team',      'type': 'text',    'align': 'left',  'context': 'meta'},
    'season':        {'name': 'Season',    'type': 'season_link', 'align': 'left', 'context': 'meta'},
    'stream':        {'name': 'Stream',    'type': 'text',    'align': 'right', 'context': 'meta'},
    'age':           {'name': 'Age',       'type': 'integer', 'align': 'right', 'context': 'meta'},
    'pos1':          {'name': 'PP',        'label': 'Primary Position',   'type': 'text',    'align': 'left',  'context': 'meta'},
    'pos2':          {'name': '2P',        'label': 'Secondary Position', 'type': 'text',    'align': 'left',  'context': 'meta'},
    'role':          {'name': 'Role',      'label': 'Pitching Role',      'type': 'text',    'align': 'left',  'context': 'meta'},
    'throws':        {'name': 'T',         'label': 'Throws',             'type': 'text',    'align': 'left',  'context': 'meta'},
    'bats':          {'name': 'B',         'label': 'Bats',               'type': 'text',    'align': 'left',  'context': 'meta'},
    'power':         {'name': 'POW',       'label': 'Power',              'type': 'integer', 'align': 'right', 'context': 'meta'},
    'contact':       {'name': 'CON',       'label': 'Contact',            'type': 'integer', 'align': 'right', 'context': 'meta'},
    'speed':         {'name': 'SPD',       'label': 'Speed',              'type': 'integer', 'align': 'right', 'context': 'meta'},
    'fielding':      {'name': 'FLD',       'label': 'Fielding',           'type': 'integer', 'align': 'right', 'context': 'meta'},
    'arm':           {'name': 'ARM',       'label': 'Arm',                'type': 'integer', 'align': 'right', 'context': 'meta'},
    'velocity':      {'name': 'VEL',       'label': 'Velocity',           'type': 'integer', 'align': 'right', 'context': 'meta'},
    'junk':          {'name': 'JNK',       'label': 'Junk',               'type': 'integer', 'align': 'right', 'context': 'meta'},
    'accuracy':      {'name': 'ACC',       'label': 'Accuracy',           'type': 'integer', 'align': 'right', 'context': 'meta'},
    'arsenal':       {'name': 'Arsenal',   'label': 'Pitch Arsenal',      'type': 'text',    'align': 'left',  'context': 'meta'},
    'dh_off':        {'name': 'OFF',       'type': 'stat',    'align': 'right', 'decimal_places': 3, 'leading_zero': True,  'context': 'meta'},
    'dh_def':        {'name': 'DEF',       'type': 'stat',    'align': 'right', 'decimal_places': 3, 'leading_zero': True,  'context': 'meta'},
    'p_dh':          {'name': 'P(DH)',     'type': 'stat', 'align': 'right', 'decimal_places': 1, 'leading_zero': True, 'percentage': True, 'context': 'meta'},
    'rpos_per_gb':   {'name': 'Rpos/G',    'type': 'stat', 'align': 'right', 'decimal_places': 3, 'leading_zero': True,  'context': 'meta'},
    'rpos_per_80g':  {'name': 'Rpos/80G',  'type': 'stat', 'align': 'right', 'decimal_places': 2, 'leading_zero': False, 'context': 'meta'},
    'rdef_attr':     {'name': 'Rdef(A)',   'type': 'stat', 'align': 'right', 'decimal_places': 1, 'leading_zero': True,  'context': 'meta'},
    'rdef_e20':      {'name': 'Rdef(E20)', 'type': 'stat', 'align': 'right', 'decimal_places': 1, 'leading_zero': True,  'context': 'meta'},
    'rdef_old':      {'name': 'Rdef(S20)', 'type': 'stat', 'align': 'right', 'decimal_places': 1, 'leading_zero': True,  'context': 'meta'},
    'rdef':          {'name': 'Rdef',      'type': 'stat', 'align': 'right', 'decimal_places': 1, 'leading_zero': True,  'context': 'meta'},
}

# -- Fill in defaults -----------------------------------------------------------

_DEFAULTS = {
    'qualified':      False,
    'lowest':         False,
    'decimal_places': 0,
    'leading_zero':   True,
    'leaders':        False,
    'has_worst':      False,
    'percentage':     False,
}

for _key, _meta in REGISTRY.items():
    for _dkey, _val in _DEFAULTS.items():
        _meta.setdefault(_dkey, _val)
    # name defaults to key if not explicitly set
    _meta.setdefault('name', _key)
    ctx = _meta.get('context', 'meta')
    _meta.setdefault('type', 'stat' if ctx != 'meta' else _meta.get('type', 'text'))
    _meta.setdefault('align', 'right')
    if ctx == 'batting':
        _meta.setdefault('qual_col', 'pa')
    elif ctx == 'baserunning':
        _meta.setdefault('qual_col', 'sb_att')
    elif ctx == 'fielding':
        _meta.setdefault('qual_col', 'gf')
    elif ctx == 'pitching':
        _meta.setdefault('qual_col', 'p_ip')
