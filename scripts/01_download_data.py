"""Step 1 - download the raw NSE bhavcopy files (about 2 GB, 10-20 minutes).

    python scripts/01_download_data.py            # everything needed to rebuild the panel
    python scripts/01_download_data.py --reference # also the optional validation dataset

You do NOT need this step to reproduce the paper: the processed panel is already in
data/processed/. Run it only if you want to rebuild that panel from the raw files.

The files are the exchange's own daily price lists. NSE's website blocks scripted
downloads, so they are taken from four public GitHub mirrors that archive the files
unchanged (scripts/02 cross-checks two of the mirrors against each other, row by row).

    data/raw/cm_bhav/                     legacy layout, 2003-2022   (gadiyar/NSEBhavcopy)
    data/raw/sec_bhavdata_full/a_tilak999 current layout, 2010-today (tilak999/NSE-Data-bank)
    data/raw/sec_bhavdata_full/b_chartiny gap filler, 2020-2025     (chartiny/nse-sec-bhavdata-full)
    data/raw/sec_bhavdata_full/c_girishg4t gap filler, 2025-today   (girishg4t/nse-bse-bhavcopy)
    data/raw/eod2/                        optional reference         (BennyThadikaran/eod2_data)

Requires git on your PATH.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tarfile

from midcapq import config

GITHUB = "https://github.com/"
CACHE = config.RAW / "_clones"


def git(*args: str, cwd=None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def clone(repo: str, blobless: bool = False):
    """Shallow-clone ``owner/name`` into the cache (skipped if already there)."""
    dest = CACHE / repo.replace("/", "_")
    if dest.exists():
        return dest
    print(f"cloning {repo} ...", flush=True)
    extra = ["--filter=blob:none", "--no-checkout"] if blobless else []
    git("clone", "--depth", "1", *extra, GITHUB + repo + ".git", str(dest))
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--reference", action="store_true", help="also fetch the eod2 dataset")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)

    # 1. legacy files: one tarball per year, unpacked into cm_bhav/<year>/
    src = clone("gadiyar/NSEBhavcopy")
    config.RAW_CM_BHAV.mkdir(parents=True, exist_ok=True)
    for tar in sorted((src / "zips").glob("*.tar.bz2")):
        if int(tar.name[:4]) < int(config.DATA_START[:4]):
            continue
        with tarfile.open(tar) as archive:
            archive.extractall(config.RAW_CM_BHAV, filter="data")
    print("  cm_bhav ready")

    # 2. current layout, the main mirror (updated daily by its owner)
    src = clone("tilak999/NSE-Data-bank")
    target = config.RAW_SEC_FULL / "a_tilak999"
    target.mkdir(parents=True, exist_ok=True)
    for f in (src / "data").glob("sec_bhavdata_full_*.csv"):
        shutil.copy2(f, target / f.name)
    print("  sec_bhavdata_full/a_tilak999 ready")

    # 3. second mirror: fills the sessions the first one missed
    src = clone("chartiny/nse-sec-bhavdata-full")
    target = config.RAW_SEC_FULL / "b_chartiny"
    target.mkdir(parents=True, exist_ok=True)
    for year in ("2020", "2023", "2024", "2025"):
        for f in (src / year).glob("*.csv"):
            shutil.copy2(f, target / f.name)
    print("  sec_bhavdata_full/b_chartiny ready")

    # 4. third mirror: only the most recent two years are needed
    src = clone("girishg4t/nse-bse-bhavcopy", blobless=True)
    wanted = [
        p
        for p in git("ls-tree", "-r", "--name-only", "HEAD", cwd=src).split()
        if p.startswith("nse/") and p.endswith((".csv",)) and p[-8:-4] in ("2025", "2026")
    ]
    git("checkout", "HEAD", "--", *wanted, cwd=src)
    target = config.RAW_SEC_FULL / "c_girishg4t"
    target.mkdir(parents=True, exist_ok=True)
    for p in wanted:
        shutil.copy2(src / p, target / p.split("/")[-1])
    print("  sec_bhavdata_full/c_girishg4t ready")

    if args.reference:
        src = clone("BennyThadikaran/eod2_data")
        (config.RAW_EOD2).mkdir(parents=True, exist_ok=True)
        shutil.copytree(src / "daily", config.RAW_EOD2 / "daily", dirs_exist_ok=True)
        print("  eod2 reference ready")

    print("\nraw data in", config.RAW, "- next: python scripts/02_build_panel.py")


if __name__ == "__main__":
    main()
