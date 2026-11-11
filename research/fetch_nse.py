#!/usr/bin/env python3
"""Download NSE delivery (sec_bhavdata_full) and F&O bhavcopy (stock futures only) for every trading day in the research panel.
Resumable: one compact CSV per day under trader/cache/nse/{deliv,fut}/YYYYMMDD.csv; existing files are skipped.

    python research/fetch_nse.py            # all panel dates
    python research/fetch_nse.py --check    # coverage report only

Sources (public archives, no login):
  delivery   https://archives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv
  F&O (old)  https://archives.nseindia.com/content/historical/DERIVATIVES/YYYY/MON/foDDMONYYYYbhav.csv.zip   (until 2024-07-05)
  F&O (new)  https://archives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip           (from 2024-07-08, UDiFF)
Both F&O formats report open interest in SHARES and prices UNADJUSTED for splits/bonuses (use within-day ratios and % changes only).
"""

import csv
import io
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "trader", "cache", "nse")
UA = {"User-Agent": "Mozilla/5.0 (compatible; india-equity-intraday-skill/1.0)"}
UDIFF_START = date(2024, 7, 8)


def clean(raw):
    return raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            e.close()
            if e.code in (403, 404):
                return None
            time.sleep(2 + 3 * k)
        except (urllib.error.URLError, OSError):
            time.sleep(2 + 3 * k)
    return None


def deliv(d):
    raw = get("https://archives.nseindia.com/products/content/sec_bhavdata_full_%s.csv" % d.strftime("%d%m%Y"))
    if not raw:
        return None
    rows = []
    rdr = csv.reader(io.StringIO(clean(raw)))
    hdr = [h.strip() for h in next(rdr)]
    for r in rdr:
        if len(r) != len(hdr):
            continue
        x = dict(zip(hdr, (c.strip() for c in r)))
        if x.get("SERIES") != "EQ":
            continue
        if datetime.strptime(x["DATE1"], "%d-%b-%Y").date() != d:
            return None                       # NSE posts the previous session under a holiday's date
        rows.append({"sym": x["SYMBOL"], "close_unadj": x["CLOSE_PRICE"], "qty": x["TTL_TRD_QNTY"], "trades": x["NO_OF_TRADES"],
                     "deliv_qty": x["DELIV_QTY"], "deliv_pct": x["DELIV_PER"]})
    return rows


def fut(d):
    rows = []
    if d < UDIFF_START:
        mon = d.strftime("%b").upper()
        raw = get("https://archives.nseindia.com/content/historical/DERIVATIVES/%d/%s/fo%02d%s%dbhav.csv.zip" % (d.year, mon, d.day, mon, d.year))
        if not raw:
            return None
        z = zipfile.ZipFile(io.BytesIO(raw))
        for x in csv.DictReader(io.StringIO(clean(z.read(z.namelist()[0])))):
            if (x.get("INSTRUMENT") or "").strip() != "FUTSTK":
                continue
            rows.append({"sym": x["SYMBOL"].strip(), "expiry": datetime.strptime(x["EXPIRY_DT"].strip(), "%d-%b-%Y").date().isoformat(),
                         "close": x["CLOSE"], "settle": x["SETTLE_PR"], "oi": x["OPEN_INT"], "chg_oi": x["CHG_IN_OI"],
                         "contracts": x["CONTRACTS"], "underlying": ""})
    else:
        raw = get("https://archives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_%s_F_0000.csv.zip" % d.strftime("%Y%m%d"))
        if not raw:
            return None
        z = zipfile.ZipFile(io.BytesIO(raw))
        for x in csv.DictReader(io.StringIO(clean(z.read(z.namelist()[0])))):
            if (x.get("FinInstrmTp") or "").strip() != "STF":
                continue
            rows.append({"sym": x["TckrSymb"].strip(), "expiry": x["XpryDt"].strip(), "close": x["ClsPric"], "settle": x["SttlmPric"],
                         "oi": x["OpnIntrst"], "chg_oi": x["ChngInOpnIntrst"], "contracts": x["TtlTradgVol"], "underlying": x["UndrlygPric"]})
    return rows


def main():
    panel = pd.read_pickle(os.path.join(ROOT, "research", "cache", "panel.pkl"))
    days = sorted({pd.Timestamp(x).date() for x in panel.d.unique()})
    for kind in ("deliv", "fut"):
        os.makedirs(os.path.join(BASE, kind), exist_ok=True)
    if "--check" in sys.argv:
        for kind in ("deliv", "fut"):
            have = {f[:8] for f in os.listdir(os.path.join(BASE, kind))}
            print(kind, "%d of %d panel days" % (sum(1 for d in days if d.strftime("%Y%m%d") in have), len(days)))
        return
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()

    def one(d):
        for kind, fn in (("deliv", deliv), ("fut", fut)):
            path = os.path.join(BASE, kind, d.strftime("%Y%m%d") + ".csv")
            if os.path.exists(path) or os.path.exists(path + ".missing"):
                continue
            try:
                rows = fn(d)
            except Exception as e:                      # one bad file must not stop the run
                print("error %s %s: %s" % (kind, d, e), flush=True)
                continue
            time.sleep(0.3)
            if rows is None:
                open(path + ".missing", "w").close()
            else:
                pd.DataFrame(rows).to_csv(path, index=False)
        return d

    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:       # 4 polite parallel workers
        for _ in ex.map(one, days):
            done += 1
            if done % 100 == 0:
                print("%d / %d days, %.0f s" % (done, len(days), time.time() - t0), flush=True)
    print("finished %d days in %.0f s" % (done, time.time() - t0))


if __name__ == "__main__":
    main()
