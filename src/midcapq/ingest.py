"""Stage 1 - read raw NSE bhavcopy files into one tidy table.

A *bhavcopy* is the exchange's end-of-day price list: one CSV per trading day with
one row per security that was listed that day. Because each file is a snapshot of
what actually traded, companies that later died are still in the old files - which
is exactly why this source is free of survivorship bias.

NSE has published the file in two layouts that we need:

* ``cmDDMMMYYYYbhav.csv``            (legacy layout, used here for 2000-2022)
* ``sec_bhavdata_full_DDMMYYYY.csv`` (current layout, used here for 2023-2026)

Both are mapped to the same columns so that nothing downstream cares which one a
row came from. The two layouts overlap between mid-2010 and 2022; that overlap is
used as a reconciliation check (see ``reconcile_sources``).
"""

from __future__ import annotations

import glob
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

COLUMNS = [
    "date",
    "symbol",
    "series",
    "open",
    "high",
    "low",
    "close",
    "prev_close",
    "volume",
    "value",
    "isin",
]


def _finish(df: pd.DataFrame) -> pd.DataFrame:
    """Shared clean-up: types, series filter, impossible rows."""
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["series"] = df["series"].astype(str).str.strip()
    df = df[df["series"].isin(config.KEEP_SERIES)].copy()
    for col in ["open", "high", "low", "close", "prev_close", "volume", "value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[(df["close"] > 0) & df["date"].notna()]
    return df[COLUMNS]


def read_cm_bhav(path: Path) -> pd.DataFrame:
    """Parse one legacy ``cm...bhav.csv`` file."""
    raw = pd.read_csv(path, dtype=str, index_col=False, on_bad_lines="skip")
    raw.columns = [c.strip() for c in raw.columns]
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(
                raw["TIMESTAMP"].str.strip(), format="%d-%b-%Y", errors="coerce"
            ),
            "symbol": raw["SYMBOL"],
            "series": raw["SERIES"],
            "open": raw["OPEN"],
            "high": raw["HIGH"],
            "low": raw["LOW"],
            "close": raw["CLOSE"],
            "prev_close": raw["PREVCLOSE"],
            "volume": raw["TOTTRDQTY"],
            "value": raw["TOTTRDVAL"],  # rupees
            "isin": raw["ISIN"].str.strip() if "ISIN" in raw.columns else None,
        }
    )
    return _finish(out)


def read_sec_full(path: Path) -> pd.DataFrame:
    """Parse one ``sec_bhavdata_full`` file.

    The turnover column is documented as lakhs of rupees but some early files hold
    plain rupees, so traded value is rebuilt as ``average price x quantity`` and falls
    back to ``close x quantity`` when the average price is missing.
    """
    raw = pd.read_csv(path, dtype=str, skipinitialspace=True, index_col=False)
    raw.columns = [c.strip() for c in raw.columns]
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(raw["DATE1"].str.strip(), format="%d-%b-%Y", errors="coerce"),
            "symbol": raw["SYMBOL"],
            "series": raw["SERIES"],
            "open": raw["OPEN_PRICE"],
            "high": raw["HIGH_PRICE"],
            "low": raw["LOW_PRICE"],
            "close": raw["CLOSE_PRICE"],
            "prev_close": raw["PREV_CLOSE"],
            "volume": raw["TTL_TRD_QNTY"],
            "value": np.nan,
            "isin": None,
        }
    )
    avg = pd.to_numeric(raw["AVG_PRICE"], errors="coerce")
    qty = pd.to_numeric(raw["TTL_TRD_QNTY"], errors="coerce")
    close = pd.to_numeric(raw["CLOSE_PRICE"], errors="coerce")
    out["value"] = np.where(avg > 0, avg * qty, close * qty)
    return _finish(out)


def _find_csv(folder: Path, pattern: str) -> list[Path]:
    """Recursive file search that also follows symlinked folders."""
    hits = glob.glob(str(folder / "**" / pattern), recursive=True)
    return sorted(Path(h) for h in hits)


def _read_many(files: list[Path], reader) -> pd.DataFrame:
    frames, bad = [], []
    for f in files:
        try:
            frames.append(reader(f))
        except Exception as exc:  # noqa: BLE001 - a corrupt daily file must not kill the run
            bad.append((f.name, repr(exc)[:80]))
    if bad:
        warnings.warn(f"{len(bad)} unreadable files, e.g. {bad[:3]}", stacklevel=2)
    return pd.concat(frames, ignore_index=True)


def load_cm_bhav(start: str, end: str) -> pd.DataFrame:
    files = _find_csv(config.RAW_CM_BHAV, "cm*bhav.csv")
    df = _read_many(files, read_cm_bhav)
    return df[(df["date"] >= start) & (df["date"] < end)]


def load_sec_full(start: str, end: str | None = None) -> pd.DataFrame:
    """Read every ``sec_bhavdata_full`` file from every mirror folder.

    The trading date is taken from the DATE1 column *inside* each file, never from
    the file name: mirrors name files by download date, which is sometimes a holiday.
    Mirrors are read in folder order and duplicates are resolved in ``dedupe``.
    """
    files = _find_csv(config.RAW_SEC_FULL, "*.csv")
    df = _read_many(files, read_sec_full)
    df = df[df["date"] >= start]
    return df if end is None else df[df["date"] < end]


def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (date, symbol).

    A symbol can appear twice on a day (e.g. EQ and BE during a series migration, or
    the same file mirrored twice). Keep the row with the larger traded value.
    """
    df = df.sort_values(["date", "symbol", "value"], ascending=[True, True, False])
    return df.drop_duplicates(["date", "symbol"], keep="first").reset_index(drop=True)


def build_raw_panel(sec: pd.DataFrame | None = None) -> pd.DataFrame:
    """Stitch the sources into a single raw panel.

    * before ``SWITCH_DATE``: the legacy ``cm_bhav`` files are primary; any session
      that is absent from them (a few special Saturday sessions) is filled from
      ``sec_bhavdata_full``;
    * from ``SWITCH_DATE``: ``sec_bhavdata_full`` (all mirrors merged).
    """
    old = load_cm_bhav(config.DATA_START, config.SWITCH_DATE)
    if sec is None:
        sec = load_sec_full(config.DATA_START)
    sec = sec[sec["date"] <= config.SAMPLE_END_DATA]
    fill = sec[(sec["date"] < config.SWITCH_DATE) & ~sec["date"].isin(old["date"].unique())]
    new = sec[sec["date"] >= config.SWITCH_DATE]
    panel = dedupe(pd.concat([old, fill, new], ignore_index=True))
    # rights entitlements trade under tickers such as "ABFRL-RE": not ordinary shares
    panel = panel[~panel["symbol"].str.contains(r"-RE\d*$", regex=True)]
    panel["symbol"] = panel["symbol"].astype("category")
    panel["series"] = panel["series"].astype("category")
    return panel.reset_index(drop=True)


def reconcile_sources(
    start: str = "2011-01-01", end: str = "2023-01-01", sec: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Compare the two independent mirrors on their overlap, year by year.

    Returns, per year, how many (date, symbol) rows both sources have and the share
    of those rows whose close / previous close / volume disagree.
    """
    a = dedupe(load_cm_bhav(start, end)).set_index(["date", "symbol"])
    if sec is None:
        sec = load_sec_full(start, end)
    sec = sec[(sec["date"] >= start) & (sec["date"] < end)]
    b = dedupe(sec).set_index(["date", "symbol"])
    both = a.join(b, how="inner", lsuffix="_cm", rsuffix="_sec")
    both["year"] = both.index.get_level_values("date").year
    rows = []
    for year, g in both.groupby("year"):
        rows.append(
            {
                "year": year,
                "rows_cm": int((a.index.get_level_values("date").year == year).sum()),
                "rows_sec": int((b.index.get_level_values("date").year == year).sum()),
                "rows_both": len(g),
                "close_mismatch": float((np.abs(g["close_cm"] - g["close_sec"]) > 0.011).mean()),
                "prev_close_mismatch": float(
                    (np.abs(g["prev_close_cm"] - g["prev_close_sec"]) > 0.011).mean()
                ),
                "volume_mismatch": float((g["volume_cm"] != g["volume_sec"]).mean()),
            }
        )
    return pd.DataFrame(rows)
