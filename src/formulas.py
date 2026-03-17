"""
Centralized stat calculators.

Each function takes a single subscriptable `d` - a DataFrame, a Series row,
or a plain dict - reads its inputs via `d['col']`, and writes the result back
as `d['col'] = ...`.

The safe-division helper `_div` handles both the array case (DataFrame column
returns a Series) and the scalar case (dict/row returns a plain number).
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


# -- Shared wOBA building blocks -----------------------------------------------

def wOBA_num(d):   return weight_BB*d['BB'] + weight_HBP*d['HBP'] + weight_1B*d['1B'] + weight_2B*d['2B'] + weight_3B*d['3B'] + weight_HR*d['HR']
def wOBA_denom(d): return d['AB'] + d['BB'] + d['HBP'] + d['SF']
def compute_wOBA(d): d['wOBA'] = _div(wOBA_num(d), wOBA_denom(d))


# -- Batting counting stats ----------------------------------------------------

def compute_TB(d):      d['TB']    = d['1B'] + 2*d['2B'] + 3*d['3B'] + 4*d['HR']
def compute_XBH(d):     d['XBH']   = d['2B'] + d['3B'] + d['HR']
def compute_BIP_bat(d): d['BIP']   = d['AB'] - d['K'] - d['HR'] + d['SF']
def compute_GF(d):      d['GF']    = d['GB'] * ratio_GF
def compute_SBatt(d):   d['SBatt'] = d['SB'] + d['CS']
def compute_RS(d):      d['RS']   = d['R'] * 4
def compute_RB(d):      d['RB']   = d['BB'] + d['HBP'] + d['1B'] + 2*d['2B'] + 3*d['3B'] + 4*d['HR']


# -- Batting rate stats --------------------------------------------------------

def compute_AVG(d):        d['AVG']    = _div(d['H'], d['AB'])
def compute_OBP(d):        d['OBP']    = _div(d['H'] + d['BB'] + d['HBP'], d['AB'] + d['BB'] + d['HBP'] + d['SF'])
def compute_SLG(d):        d['SLG']    = _div(d['TB'], d['AB'])
def compute_OPS(d):        d['OPS']    = d['OBP'] + d['SLG']
def compute_ISO(d):        d['ISO']    = d['SLG'] - d['AVG']
def compute_BABIP_bat(d):  d['BABIP']  = _div(d['H'] - d['HR'], d['BIP'])
def compute_HR_pct_bat(d): d['HR%']    = _div(d['HR'], d['PA'])
def compute_K_pct_bat(d):  d['K%']     = _div(d['K'],  d['PA'])
def compute_BB_pct_bat(d): d['BB%']    = _div(d['BB'], d['PA'])
def compute_PA_per_GB(d):  d['PA/GB']  = _div(d['PA'], d['GB'])
def compute_PA_per_HR(d):  d['PA/HR']  = _div(d['PA'], d['HR'])
def compute_XBH_pct(d):    d['XBH%']   = _div(d['XBH'], d['H'])
def compute_RS_pct(d):     d['RS%']    = _div(d['R'], d['H'] + d['BB'] + d['HBP'])
def compute_RC_pct(d):     d['RC%']    = _div(d['R'] - d['HR'], d['H'] - d['HR'] + d['BB'] + d['HBP'])
def compute_SB_pct(d):     d['SB%']    = _div(d['SB'], d['SB'] + d['CS'])
def compute_SbAtt_pct(d):  d['SbAtt%'] = _div(d['SB'] + d['CS'], d['1B'])
def compute_E_per_GF(d):   d['E/GF']   = _div(d['E'], d['GF'])
def compute_PB_per_GF(d):  d['PB/GF']  = _div(d['PB'], d['GF'])
def compute_RAA_bat(d):    d['RAA']    = d['Rbat'] + d['Rbr'] + d['Rdef'] + d['Rpos'] + d['Rcorr']
def compute_RAR_bat(d):    d['RAR']    = d['RAA'] + d['Rrep']

# TODO: compute_wRAA    - needs lg_wOBA, park factor
# TODO: compute_wSB     - needs lg_wSB
# TODO: compute_Def_bat - needs agg_fielding
# TODO: compute_Pos     - needs agg_wOBA
# TODO: compute_Rrep    - needs season RR/PA
# TODO: compute_WAA     = RAA / rpw
# TODO: compute_WAR     = RAR / rpw
# TODO: compute_OPS_plus  - needs lg_OBP, lg_SLG, park factor
def compute_R_per_PA(d): d['R/PA'] = _div(d['R'], d['PA'])
# TODO: compute_wRC      - needs lg_wOBA, lg_R/PA
# TODO: compute_wRC_plus - needs wRAA, lg_wRC, lg_PA, lg_R/PA


# -- Pitching counting stats ---------------------------------------------------

def compute_GR(d):      d['GR']  = d['GP'] - d['GS']
def compute_BIP_pit(d): d['BIP'] = d['BF'] - d['K'] - d['HR'] - d['BB'] - d['HBP']


# -- Pitching rate stats -------------------------------------------------------

def compute_RA9def(d):   d['RA9def']  = _div((d['RA'] + d['Rdef']) * 9, d['IP_true'])
def compute_RAAlev(d):   d['RAAlev']  = d['RAA'] + d['Rlev']
def compute_RAR_pit(d):  d['RAR']     = d['RAAlev'] + d['Rrep']

# TODO: compute_ERA_minus - needs lg_ERA
# TODO: compute_FIP       - compute_FIP_raw (below) + cFIP from league
# TODO: compute_Def_pit   - needs team BABIP diff, R/H, DEF_IMPACT
# TODO: compute_RAA_pit   - needs ra9_comp (role), park factor
# TODO: compute_Rlev      - needs role_leverage
# TODO: compute_WAA_pit   = RAAlev / rpw
# TODO: compute_Rrep_pit  - needs role_innings, rpw
# TODO: compute_WAR_pit   = RAR / rpw

def compute_ERA(d):        d['ERA']   = 9 * _div(d['ER'], d['IP_true'])
def compute_RA9(d):        d['RA9']   = 9 * _div(d['RA'], d['IP_true'])
def compute_WHIP(d):       d['WHIP']  = _div(d['BB'] + d['H'], d['IP_true'])
def compute_BAA(d):        d['BAA']   = _div(d['H'], d['BF'] - d['BB'] - d['HBP'])
def compute_OBPA(d):       d['OBPA']  = _div(d['H'] + d['BB'] + d['HBP'], d['BF'])
def compute_BABIP_pit(d):  d['BABIP'] = _div(d['H'] - d['HR'], d['BIP'])
def compute_WIN_pct(d):    d['WIN%']  = _div(d['W'], d['W'] + d['L'])
def compute_K_per_9(d):    d['K/9']   = 9 * _div(d['K'],  d['IP_true'])
def compute_H_per_9(d):    d['H/9']   = 9 * _div(d['H'],  d['IP_true'])
def compute_HR_per_9(d):   d['HR/9']  = 9 * _div(d['HR'], d['IP_true'])
def compute_BB_per_9(d):   d['BB/9']  = 9 * _div(d['BB'], d['IP_true'])
def compute_K_per_BB(d):   d['K/BB']  = _div(d['K'],  d['BB'])
def compute_HR_pct_pit(d): d['HR%']   = _div(d['HR'], d['BF'])
def compute_K_pct_pit(d):  d['K%']    = _div(d['K'],  d['BF'])
def compute_BB_pct_pit(d): d['BB%']   = _div(d['BB'], d['BF'])
def compute_P_per_GP(d):   d['P/GP']  = _div(d['TP'], d['GP'])
def compute_P_per_IP(d):   d['P/IP']  = _div(d['TP'], d['IP_true'])
def compute_P_per_PA(d):   d['P/PA']  = _div(d['TP'], d['BF'])
def compute_IP_per_GP(d):  d['IP/GP'] = _div(d['IP_true'], d['GP'])
def compute_SV_pct(d):     d['SV%']   = _div(d['SV'], d['GR'])

# FIP without the cFIP constant - add league cFIP to get final FIP
def compute_FIP_raw(d): d['FIP'] = _div(13*d['HR'] + 3*(d['BB'] + d['HBP']) - 2*d['K'], d['IP_true'])

# League context only - not meaningful for individual players:
def compute_R_per_H(d): d['R/H']  = _div(d['RA'], d['H'])  # league run environment proxy used for defense adjustment
def compute_cFIP(d):    d['cFIP'] = d['ERA'] - d['FIP']     # scales FIP_raw to ERA level; requires ERA and FIP already computed
