# wOBA linear weights
weight_BB  = 0.701
weight_HBP = 0.732
weight_1B  = 0.895
weight_2B  = 1.270
weight_3B  = 1.608
weight_HR  = 2.072
scale_wOBA = 1.251

MIN_PA = 5000  # stabilization rate for multi-position wOBA adjustment

# Baserunning
runs_SB = 0.2
runs_CS = -0.45

# Fielding
ratio_GF   = 8/9
runs_E     = -0.7   # used in Seasons 1-20 Rdef calculation
runs_PB    = -0.45  # used in Seasons 1-20 Rdef calculation
runs_E_new = -0.4   # used in new attribute-based Rdef model (Season 21+)
DEF_IMPACT = 0.5

# MLB average errors per game by position (2021-2025, all 30 teams)
# Source: mlb_errors.csv
mlb_E_rate = {
    'SS': 0.0933,
    '3B': 0.0863,
    'C':  0.0567,
    '2B': 0.0562,
    '1B': 0.0413,
    'RF': 0.0234,
    'LF': 0.0212,
    'CF': 0.0205,
}

# Pitching
runs_SV           = 0.5
SPRP_INNING_SHARE = 0.5

# WAR framework
# TODO: RUNS_PER_WIN should be calculated from league run data rather than hardcoded
RUNS_PER_WIN      = 9.86107227952777
num_games         = 80
num_teams         = 30
replacement_level = 1/6

TOTAL_SEASON_GAMES = num_teams * num_games // 2

total_WAR     = (0.5 - replacement_level) * num_games * num_teams
batter_share  = 13/21
starter_share = 2/3

batter_WAR   = total_WAR * batter_share
pitcher_WAR  = total_WAR - batter_WAR
starter_WAR  = pitcher_WAR * starter_share
reliever_WAR = pitcher_WAR - starter_WAR

# TODO: park_factors should be calculated from historical run data rather than hardcoded
# Park factors (raw values / 100 so 1.0 = league average)
park_factors = {
    'CAS': 101.1658, 'MSLA': 99.6863, 'PDX': 102.4566, 'SCS': 102.0354, 'CHI': 96.7187,
    'BSD': 95.2162,  'CAR': 106.5279, 'HAV': 99.4989,  'CDMX': 99.4989, 'SPT': 95.2162,
    'BOS': 106.5279, 'MTL': 102.4566, 'NYF': 99.7004,  'NYN': 99.7004,  'PIT': 96.7187,
    'PAL': 102.0354, 'DUB': 102.4566, 'GLA': 102.4566, 'VAL': 95.2162,  'MUN': 102.4566,
    'BUS': 109.2252, 'HON': 89.0382,  'KBC': 98.1349,  'NGO': 95.5229,  'SEO': 109.2252,
    'BBR': 98.9917,  'JAK': 96.7187,  'JSB': 96.7187,  'MFP': 98.9917,  'DAK': 99.6863,
}
park_factors = {team.lower(): value / 100 for team, value in park_factors.items()}
# NOTE: we implicitly assume league-average park factor is 100

# Qualification thresholds
BAT_PA_PER_GAME      = 2.7
BR_SBATT_PER_GAME    = 0.1
FLD_GF_PER_GAME      = 0.67
PIT_IP_PER_GAME      = 1.0

BAT_SEASON_MIN_PA    = BAT_PA_PER_GAME   * num_games
BAT_CAREER_MIN_PA    = 1500
BR_SEASON_MIN_SBATT  = BR_SBATT_PER_GAME * num_games
BR_CAREER_MIN_SBATT  = 40
FLD_SEASON_MIN_GF    = FLD_GF_PER_GAME   * num_games
FLD_CAREER_MIN_GF    = 250
PIT_SEASON_MIN_IP    = PIT_IP_PER_GAME   * num_games
PIT_CAREER_MIN_IP    = 500.0

# Seasons for projections
CURRENT_SEASON        = 21
LAST_COMPLETED_SEASON = 20

# Projection seasons and Marcel-style weights (most recent to oldest)
PROJ_SEASONS      = [LAST_COMPLETED_SEASON - 2, LAST_COMPLETED_SEASON - 1, LAST_COMPLETED_SEASON]
PROJ_WEIGHTS      = {LAST_COMPLETED_SEASON - 2: 3, LAST_COMPLETED_SEASON - 1: 4, LAST_COMPLETED_SEASON: 5}
PROJ_WEIGHT_TOTAL = sum(PROJ_WEIGHTS.values())

# Season range (all seasons including current)
SEASON_RANGE = range(1, CURRENT_SEASON + 1)
