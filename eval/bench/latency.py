"""Délais mesurés sur un kiosque en fonctionnement (réel ou simulé), via son API.

    python -m eval.bench.latency --url http://aristote-k01.local:8000 -n 20 -o eval/results/delais.json

Sur un kiosque réel, lancer depuis le kiosque lui-même (`--url http://127.0.0.1:8000`) pour ne pas mesurer le Wi-Fi.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

from ..common import percentile


def measure(url: str, n: int, with_scan: bool) -> dict:
    client = httpx.Client(base_url=url, timeout=60)
    state = client.get("/api/state").json()
    switches, scans = [], []
    for i in range(n):
        index = i % len(state["students"])
        start = time.perf_counter()
        client.post(f"/api/students/{index}/select").raise_for_status()
        switches.append(time.perf_counter() - start)
        client.post("/api/tutor/next")
        if with_scan and state["capabilities"]["camera"]:
            start = time.perf_counter()
            if client.post("/api/scan").status_code == 200:
                scans.append(time.perf_counter() - start)
    client.post("/api/session/end")
    result = {"changement_eleve_s": {"valeur": percentile(switches, 0.95), "fiable": True, "n": len(switches)}}
    if scans:
        result["scan_s"] = {"valeur": percentile(scans, 0.5), "fiable": True, "n": len(scans)}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("-n", type=int, default=20)
    parser.add_argument("--no-scan", action="store_true")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    result = measure(args.url, args.n, not args.no_scan)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        open(args.output, "w", encoding="utf-8").write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
