"""
Centralized stat calculators.

Each function takes a single subscriptable `d` - a DataFrame, a Series row,
or a plain dict - reads its inputs via `d['col']`, and writes the result back
as `d['col'] = ...`.

The safe-division helper `_div` handles both the array case (DataFrame column
returns a Series) and the scalar case (dict/row returns a plain number).

Function naming convention: compute_<output_column_name>.
For columns shared between batting and pitching DataFrames (war, raa, rar, etc.),
use b_ or p_ prefix to disambiguate: compute_b_war, compute_p_war, etc.
"""
import numpy as np
import pandas as pd

from constants import weight_BB, weight_HBP, weight_1B, weight_2B, weight_3B, weight_HR, ratio_GF


# -- Safe division -------------------------------------------------------------

def _div(num, denom):
    """Return num/denom, substituting 0 wherever denom is zero."""
    if isinstance(denom, pd.Series):
        return np.divide(num, denom, out=np.zeros(len(denom), dtype=float), where=denom != 0)
    return (num / denom) if denom != 0 else 0.0


# -- Shared wOBA building blocks (batting column names) ------------------------

def wOBA_num(d):   return weight_BB*d['bb'] + weight_HBP*d['hbp'] + weight_1B*d['b_1b'] + weight_2B*d['b_2b'] + weight_3B*d['b_3b'] + weight_HR*d['hr']
def wOBA_denom(d): return d['ab'] + d['bb'] + d['hbp'] + d['sf']
def compute_woba(d): d['woba'] = _div(wOBA_num(d), wOBA_denom(d))

# Legacy aliases used by league.py (still operates on raw CSV with old names)
def wOBA_num_raw(d):   return weight_BB*d['BB'] + weight_HBP*d['HBP'] + weight_1B*d['1B'] + weight_2B*d['2B'] + weight_3B*d['3B'] + weight_HR*d['HR']
def wOBA_denom_raw(d): return d['AB'] + d['BB'] + d['HBP'] + d['SF']


# -- Batting counting stats (final column names) --------------------------------

def compute_tb(d):      d['tb']     = d['b_1b'] + 2*d['b_2b'] + 3*d['b_3b'] + 4*d['hr']
def compute_xbh(d):     d['xbh']    = d['b_2b'] + d['b_3b'] + d['hr']
def compute_bip_bat(d): d['bip']    = d['ab'] - d['k'] - d['hr'] + d['sf']
def compute_gf(d):      d['gf']     = d['gb'] * ratio_GF
def compute_sb_att(d):  d['sb_att'] = d['sb'] + d['cs']
def compute_rs(d):      d['rs']     = d['r'] * 4
def compute_rb(d):      d['rb']     = d['bb'] + d['hbp'] + d['b_1b'] + 2*d['b_2b'] + 3*d['b_3b'] + 4*d['hr']


# -- Batting rate stats (final column names) ------------------------------------

def compute_avg(d):        d['avg']        = _div(d['h'], d['ab'])
def compute_obp(d):        d['obp']        = _div(d['h'] + d['bb'] + d['hbp'], d['ab'] + d['bb'] + d['hbp'] + d['sf'])
def compute_slg(d):        d['slg']        = _div(d['tb'], d['ab'])
def compute_ops(d):        d['ops']        = d['obp'] + d['slg']
def compute_iso(d):        d['iso']        = d['slg'] - d['avg']
def compute_babip_bat(d):  d['babip']      = _div(d['h'] - d['hr'], d['bip'])
def compute_hr_pct_bat(d): d['hr_pct']     = _div(d['hr'], d['pa'])
def compute_k_pct_bat(d):  d['k_pct']      = _div(d['k'],  d['pa'])
def compute_bb_pct_bat(d): d['bb_pct']     = _div(d['bb'], d['pa'])
def compute_pa_per_gb(d):  d['pa_per_gb']  = _div(d['pa'], d['gb'])
def compute_pa_per_hr(d):  d['pa_per_hr']  = _div(d['pa'], d['hr'])
def compute_xbh_pct(d):    d['xbh_pct']    = _div(d['xbh'], d['h'])
def compute_rs_pct(d):     d['rs_pct']     = _div(d['r'], d['h'] + d['bb'] + d['hbp'])
def compute_rc_pct(d):     d['rc_pct']     = _div(d['r'] - d['hr'], d['h'] - d['hr'] + d['bb'] + d['hbp'])
def compute_sb_pct(d):     d['sb_pct']     = _div(d['sb'], d['sb'] + d['cs'])
def compute_sb_att_pct(d): d['sb_att_pct'] = _div(d['sb'] + d['cs'], d['b_1b'])
def compute_e_per_gf(d):   d['e_per_gf']   = _div(d['e'], d['gf'])
def compute_pb_per_gf(d):  d['pb_per_gf']  = _div(d['pb'], d['gf'])
def compute_b_raa(d):      d['raa']        = d['r_bat'] + d['r_br'] + d['r_def'] + d['r_pos'] + d['r_corr']
def compute_b_rar(d):      d['rar']        = d['raa'] + d['r_rep']

# TODO: compute_wraa    - needs lg_woba, park factor
# TODO: compute_wsb     - needs lg_wsb
# TODO: compute_r_def   - needs agg_fielding
# TODO: compute_r_pos   - needs agg_woba
# TODO: compute_r_rep   - needs season RR/PA
# TODO: compute_waa     = raa / rpw
# TODO: compute_b_war   = rar / rpw
# TODO: compute_ops_plus  - needs lg_obp, lg_slg, park factor
def compute_r_per_pa(d): d['R/PA'] = _div(d['R'], d['PA'])
# TODO: compute_wrc      - needs lg_woba, lg_R/PA
# TODO: compute_wrc_plus - needs wraa, lg_wrc, lg_pa, lg_R/PA


# -- Pitching counting stats (final column names) ------------------------------

def compute_p_gr(d):      d['p_gr']  = d['p_gp'] - d['p_gs']
def compute_p_bip(d):     d['p_bip'] = d['p_bf'] - d['p_k'] - d['p_hr'] - d['p_bb'] - d['p_hbp']


# -- Pitching rate stats (final column names) -----------------------------------

def compute_p_ra9_def(d):  d['p_ra9_def'] = _div((d['p_ra'] + d['p_r_def']) * 9, d['p_ip'])
def compute_p_raa_lev(d):  d['p_raa_lev'] = d['p_raa'] + d['p_r_lev']
def compute_p_rar(d):      d['p_rar']      = d['p_raa_lev'] + d['p_r_rep']

# TODO: compute_p_era_minus - needs lg_era
# TODO: compute_p_fip       - compute_fip_raw (below) + cfip from league
# TODO: compute_r_def_pit   - needs team babip diff, R/H, DEF_IMPACT
# TODO: compute_p_raa       - needs ra9_comp (role), park factor
# TODO: compute_p_r_lev     - needs role_leverage
# TODO: compute_p_waa       = p_raa_lev / rpw
# TODO: compute_p_r_rep     - needs role_innings, rpw
# TODO: compute_p_war       = rar / rpw

def compute_p_era(d):        d['p_era']       = 9 * _div(d['p_er'], d['p_ip'])
def compute_p_ra9(d):        d['p_ra9']       = 9 * _div(d['p_ra'], d['p_ip'])
def compute_p_whip(d):       d['p_whip']      = _div(d['p_bb'] + d['p_h'], d['p_ip'])
def compute_p_baa(d):        d['p_baa']       = _div(d['p_h'], d['p_bf'] - d['p_bb'] - d['p_hbp'])
def compute_p_obpa(d):       d['p_obpa']      = _div(d['p_h'] + d['p_bb'] + d['p_hbp'], d['p_bf'])
def compute_p_babip(d):      d['p_babip']     = _div(d['p_h'] - d['p_hr'], d['p_bip'])
def compute_p_win_pct(d):    d['p_win_pct']   = _div(d['p_w'], d['p_w'] + d['p_l'])
def compute_p_k_per_9(d):    d['p_k_per_9']   = 9 * _div(d['p_k'],  d['p_ip'])
def compute_p_h_per_9(d):    d['p_h_per_9']   = 9 * _div(d['p_h'],  d['p_ip'])
def compute_p_hr_per_9(d):   d['p_hr_per_9']  = 9 * _div(d['p_hr'], d['p_ip'])
def compute_p_bb_per_9(d):   d['p_bb_per_9']  = 9 * _div(d['p_bb'], d['p_ip'])
def compute_p_k_per_bb(d):   d['p_k_per_bb']  = _div(d['p_k'],  d['p_bb'])
def compute_p_hr_pct(d):     d['p_hr_pct']    = _div(d['p_hr'], d['p_bf'])
def compute_p_k_pct(d):      d['p_k_pct']     = _div(d['p_k'],  d['p_bf'])
def compute_p_bb_pct(d):     d['p_bb_pct']    = _div(d['p_bb'], d['p_bf'])
def compute_p_p_per_gp(d):   d['p_p_per_gp']  = _div(d['p_tp'], d['p_gp'])
def compute_p_p_per_ip(d):   d['p_p_per_ip']  = _div(d['p_tp'], d['p_ip'])
def compute_p_p_per_pa(d):   d['p_p_per_pa']  = _div(d['p_tp'], d['p_bf'])
def compute_p_ip_per_gp(d):  d['p_ip_per_gp'] = _div(d['p_ip'], d['p_gp'])
def compute_p_sv_pct(d):     d['p_sv_pct']    = _div(d['p_sv'], d['p_gr'])

# FIP without the cFIP constant - add league cFIP to get final FIP
def compute_fip_raw(d): d['p_fip'] = _div(13*d['p_hr'] + 3*(d['p_bb'] + d['p_hbp']) - 2*d['p_k'], d['p_ip'])

# League context only - not meaningful for individual players:
def compute_r_per_h(d): d['R/H']  = _div(d['RA'], d['H'])   # league run environment proxy used for defense adjustment
def compute_cfip(d):    d['cFIP'] = d['ERA'] - d['FIP']      # scales FIP_raw to ERA level; requires ERA and FIP already computed


# -- League-level helpers operating on RAW CSV names (used only in league.py) --
# These operate on the raw pitching_stats DataFrame before column renaming.

def compute_bip_pit_raw(d):  d['BIP']  = d['BF'] - d['K'] - d['HR'] - d['BB'] - d['HBP']
def compute_gr_raw(d):       d['GR']   = d['GP'] - d['GS']
def compute_era_raw(d):      d['ERA']  = 9 * _div(d['ER'], d['IP_true'])
def compute_ra9_raw(d):      d['RA9']  = 9 * _div(d['RA'], d['IP_true'])
def compute_whip_raw(d):     d['WHIP'] = _div(d['BB'] + d['H'], d['IP_true'])
def compute_babip_pit_raw(d):d['BABIP']= _div(d['H'] - d['HR'], d['BIP'])
def compute_sv_pct_raw(d):   d['SV%']  = _div(d['SV'], d['GR'])
def compute_h_per_9_raw(d):  d['p_h_per_9']  = 9 * _div(d['H'],  d['IP_true'])
def compute_hr_per_9_raw(d): d['p_hr_per_9'] = 9 * _div(d['HR'], d['IP_true'])
def compute_bb_per_9_raw(d): d['p_bb_per_9'] = 9 * _div(d['BB'], d['IP_true'])
def compute_k_per_9_raw(d):  d['p_k_per_9']  = 9 * _div(d['K'],  d['IP_true'])
def compute_k_per_bb_raw(d): d['p_k_per_bb'] = _div(d['K'],  d['BB'])
def compute_k_pct_pit_raw(d):d['p_k_pct']    = _div(d['K'],  d['BF'])
def compute_bb_pct_pit_raw(d):d['p_bb_pct']  = _div(d['BB'], d['BF'])
def compute_hr_pct_pit_raw(d):d['p_hr_pct']  = _div(d['HR'], d['BF'])
def compute_fip_raw_raw(d):  d['FIP']  = _div(13*d['HR'] + 3*(d['BB'] + d['HBP']) - 2*d['K'], d['IP_true'])
def compute_p_per_ip_raw(d): d['p_p_per_ip'] = _div(d['TP'], d['IP_true'])
def compute_p_per_pa_raw(d): d['p_p_per_pa'] = _div(d['TP'], d['BF'])

# League batting raw helpers (season_batting DataFrame still uses raw CSV names)
def compute_avg_raw(d):  d['AVG'] = _div(d['H'], d['AB'])
def compute_obp_raw(d):  d['OBP'] = _div(d['H'] + d['BB'] + d['HBP'], d['AB'] + d['BB'] + d['HBP'] + d['SF'])
def compute_slg_raw(d):  d['SLG'] = _div(d['TB'], d['AB'])
def compute_sb_pct_raw(d): d['sb_pct'] = _div(d['SB'], d['SB'] + d['CS'])
def compute_woba_raw(d): d['wOBA'] = _div(wOBA_num_raw(d), wOBA_denom_raw(d))
def compute_e_per_gf_raw(d): d['e_per_gf'] = _div(d['E'], d['GF'])
def compute_pb_per_gf_raw(d): d['pb_per_gf'] = _div(d['PB'], d['GF'])
