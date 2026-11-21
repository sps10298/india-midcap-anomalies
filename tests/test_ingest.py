"""The two raw layouts must map to identical tidy rows."""

from midcapq import ingest

CM = """SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,
RELIANCE,EQ,823,832.5,815,818.1,816.6,1645.4,7408536,6093238362.2,07-SEP-2017,125644,INE002A01018,
SOMEBOND,N1,100,100,100,100,100,100,5,500,07-SEP-2017,1,INE000000000,
"""
SEC = """SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER
RELIANCE, EQ, 07-Sep-2017, 1645.40, 823.00, 832.50, 815.00, 816.60, 818.10, 822.46, 7408536, 60932.38, 125644, 100, 1.0
1018GS2026, GS, 07-Sep-2017, 107.98, 111.00, 111.00, 109.00, 109.00, 109.51, 109.51, 470, 0.51, 2, 470, 100.00
"""


def test_both_layouts_agree(tmp_path):
    (tmp_path / "cm07SEP2017bhav.csv").write_text(CM)
    (tmp_path / "sec.csv").write_text(SEC)
    a = ingest.read_cm_bhav(tmp_path / "cm07SEP2017bhav.csv")
    b = ingest.read_sec_full(tmp_path / "sec.csv")
    assert list(a["symbol"]) == list(b["symbol"]) == ["RELIANCE"]  # bonds are dropped
    for col in ["date", "open", "close", "prev_close", "volume"]:
        assert a[col].iloc[0] == b[col].iloc[0]
    assert abs(a["value"].iloc[0] / b["value"].iloc[0] - 1) < 1e-3  # rupees in both


def test_dedupe_keeps_the_more_liquid_row(tmp_path):
    (tmp_path / "cm.csv").write_text(CM)
    a = ingest.read_cm_bhav(tmp_path / "cm.csv")
    twin = a.copy()
    twin["value"] = 1.0
    out = ingest.dedupe(__import__("pandas").concat([twin, a]))
    assert len(out) == 1 and out["value"].iloc[0] > 1.0
