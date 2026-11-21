"""Central configuration: paths and the constants fixed by the pre-registration.

Everything a reader might want to change lives here, so that no script hides a
"magic number". Constants marked PRE-REGISTERED are frozen in
docs/PREREGISTRATION.md and must not be edited after results have been seen.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- paths
ROOT = Path(os.environ.get("MIDCAPQ_ROOT", Path(__file__).resolve().parents[2]))
RAW = ROOT / "data" / "raw"
RAW_CM_BHAV = RAW / "cm_bhav"  # legacy "cmDDMMMYYYYbhav.csv" files, 2000-2022
RAW_SEC_FULL = RAW / "sec_bhavdata_full"  # one sub-folder per mirror, 2010-2026
RAW_EOD2 = RAW / "eod2"  # independent split-adjusted series, validation only
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"

# ----------------------------------------------------------------- sample definition
DATA_START = "2003-01-01"  # first session kept (two years of warm-up before the sample)
SWITCH_DATE = "2023-01-01"  # cm_bhav before this date, sec_bhavdata_full from it
SAMPLE_END_DATA = "2026-11-10"  # last trading date kept in the panel
SAMPLE_START = "2005-01-01"  # PRE-REGISTERED first date strategy returns are measured
SAMPLE_END = "2026-10-30"  # PRE-REGISTERED last date (last complete month in the data)
HOLDOUT_START = "2016-01-01"  # PRE-REGISTERED split: discovery < this date <= confirmation

KEEP_SERIES = ("EQ", "BE", "BZ")  # ordinary equity: rolling, trade-for-trade, Z-category

# ------------------------------------------------------------ universe (PRE-REGISTERED)
UNIVERSE_LOOKBACK = 126  # trading days of history used to rank liquidity
UNIVERSE_MIN_TRADED_FRAC = 0.90  # must trade on >= 90% of those days
UNIVERSE_MIN_PRICE = 10.0  # rupees, unadjusted close on the formation date
LARGE_N = 100  # ranks 1..100 = large-cap proxy
MID_N = 150  # ranks 101..250 = mid-cap proxy (mirrors the Nifty Midcap 150 rule)

# --------------------------------------------------------------- costs (PRE-REGISTERED)
# One-way cost in basis points of traded value, cash-equity delivery trade.
# Statutory part: STT 10 bps on each side + stamp duty 1.5 bps (buy only, averaged to
# 0.75 per side) + exchange/SEBI/GST ~0.5 bps  ~= 11 bps.  See docs/METHODOLOGY.md.
STATUTORY_BPS = 11.0
IMPACT_BPS = 10.0  # half-spread + impact assumption for a liquid mid-cap
COST_BPS = STATUTORY_BPS + IMPACT_BPS  # 21 bps one-way, base case
COST_GRID_BPS = (0.0, 5.0, 11.0, 21.0, 31.0, 51.0)

TRADING_DAYS = 250  # NSE averages ~248-250 sessions a year
SEED = 20261112
