#!/usr/bin/env python3
"""A small NSE India JSON client shared by trader-news, trader-analyst and trader-flows. Standard library only.

NSE's website APIs (nseindia.com/api/...) are public but UNOFFICIAL and not a licensed data feed: they
need a browser-like User-Agent and the cookies the home page sets, they rate-limit, they sometimes
answer 401/403/503, and NSE can change them without notice. This client:

  - opens https://www.nseindia.com/ once to collect cookies, then calls the API with them;
  - waits `pause` seconds between calls and retries once with fresh cookies on 401/403/429/5xx;
  - never retries more than that and never hammers the site;
  - reads saved files instead of the network when `offline` is a folder (the tests do).

Use it for end-of-day facts and announcements. It is NOT a real-time, tick-level or order-book source.
For anything that depends on live prices, bid/ask or depth, use your Zerodha Kite chart and say so.
"""

import gzip
import http.cookiejar
import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://www.nseindia.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")


class NseError(Exception):
    pass


class NseClient(object):
    def __init__(self, offline=None, pause=0.6, timeout=30):
        self.offline = offline
        self.pause = pause
        self.timeout = timeout
        self._last = 0.0
        self._warm = False
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._jar))

    def _sleep(self):
        gap = time.time() - self._last
        if gap < self.pause:
            time.sleep(self.pause - gap)
        self._last = time.time()

    def _open(self, url, accept):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip", "Referer": BASE + "/"})
        with self._opener.open(req, timeout=self.timeout) as resp:
            data = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
            return data

    def warm(self):
        self._sleep()
        try:
            self._open(BASE + "/", "text/html,application/xhtml+xml")
        except urllib.error.HTTPError as exc:
            exc.close()
            raise NseError("nseindia.com refused the request (HTTP %d). NSE blocks some scripted access and this "
                           "tool does not try to get around that. Open the NSE page in your browser, or paste "
                           "the announcement text here." % exc.code)
        except (urllib.error.URLError, OSError) as exc:
            raise NseError("could not open nseindia.com: %s" % getattr(exc, "reason", exc))
        self._warm = True

    def get_json(self, path, offline_name=None):
        """GET BASE+path and parse JSON. `path` starts with /api/..."""
        if self.offline:
            name = offline_name or path.strip("/").replace("/", "_").replace("?", "_").replace("&", "_") + ".json"
            p = os.path.join(self.offline, name)
            if not os.path.isfile(p):
                raise NseError("offline: no file %s" % p)
            with open(p, "rb") as fh:
                return json.loads(fh.read().decode("utf-8"))
        last = "no answer"
        for attempt in (0, 1):
            if not self._warm:
                self.warm()      # a refusal here is final: no retries, no workarounds
            self._sleep()
            try:
                data = self._open(BASE + path, "application/json, text/plain, */*")
                text = data.decode("utf-8", "replace").lstrip()
                if not text or text[0] not in "[{":
                    last = "NSE answered something that is not JSON (maintenance or blocked)"
                    self._warm = False
                    continue
                return json.loads(text)
            except urllib.error.HTTPError as exc:
                last = "HTTP %d" % exc.code
                exc.close()
                self._warm = False
                if exc.code in (401, 403, 429) or exc.code >= 500:
                    time.sleep(2.0 if attempt == 0 else 0)
                    continue
                break
            except (urllib.error.URLError, OSError, ValueError) as exc:
                last = str(getattr(exc, "reason", exc))
                self._warm = False
                continue
        raise NseError("NSE %s: %s" % (path.split("?")[0], last))
