"""Measure latency to regional reference endpoints and rank game regions.

The probes use a TCP handshake (port 443) against well-known regional cloud
endpoints. That is far more reliable than ICMP, which many game and cloud
networks block. It estimates the routing quality to a region, not the exact
latency of a specific game server.
"""
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

# region key -> (reference host, translation key)
REGIONS = {
    "eu_west": ("s3.eu-west-3.amazonaws.com", "region_eu_west"),
    "eu_central": ("s3.eu-central-1.amazonaws.com", "region_eu_central"),
    "eu_north": ("s3.eu-north-1.amazonaws.com", "region_eu_north"),
    "us_east": ("s3.us-east-1.amazonaws.com", "region_us_east"),
    "us_west": ("s3.us-west-2.amazonaws.com", "region_us_west"),
    "sa_east": ("s3.sa-east-1.amazonaws.com", "region_sa_east"),
    "ap_southeast": ("s3.ap-southeast-1.amazonaws.com", "region_ap_southeast"),
    "ap_southeast2": ("s3.ap-southeast-2.amazonaws.com", "region_ap_southeast2"),
    "ap_northeast": ("s3.ap-northeast-1.amazonaws.com", "region_ap_northeast"),
    "ap_south": ("s3.ap-south-1.amazonaws.com", "region_ap_south"),
    "af_south": ("s3.af-south-1.amazonaws.com", "region_af_south"),
}

# game key -> (label, tested regions)
GAMES = {
    "valorant": ("VALORANT", (
        "eu_west", "eu_central", "eu_north", "us_east", "us_west",
        "sa_east", "ap_southeast", "ap_northeast", "ap_south",
    )),
    "cs2": ("Counter-Strike 2", (
        "eu_west", "eu_central", "eu_north", "us_east", "us_west", "sa_east",
        "ap_southeast", "ap_southeast2", "ap_northeast", "ap_south", "af_south",
    )),
    "fortnite": ("Fortnite", (
        "eu_west", "eu_central", "us_east", "us_west", "sa_east",
        "ap_southeast", "ap_northeast", "ap_southeast2", "ap_south", "af_south",
    )),
    "apex": ("Apex Legends", (
        "eu_west", "eu_central", "us_east", "us_west", "sa_east",
        "ap_southeast", "ap_northeast", "ap_southeast2",
    )),
    "rocketleague": ("Rocket League", (
        "eu_west", "eu_central", "eu_north", "us_east", "us_west",
        "sa_east", "ap_southeast", "ap_southeast2",
    )),
    "minecraft": ("Minecraft", (
        "eu_west", "eu_central", "eu_north", "us_east", "us_west", "sa_east",
        "ap_southeast", "ap_northeast", "ap_southeast2", "ap_south", "af_south",
    )),
    "scpsl": ("SCP: Secret Laboratory", (
        "eu_west", "eu_central", "us_east", "us_west", "sa_east",
        "ap_southeast", "ap_northeast", "ap_southeast2",
    )),
    "rainbow6": ("Rainbow Six Siege", (
        "eu_west", "eu_central", "us_east", "us_west", "sa_east",
        "ap_southeast", "ap_northeast", "ap_southeast2",
    )),
    "league": ("League of Legends", (
        "eu_west", "eu_central", "eu_north", "us_east", "us_west", "sa_east",
        "ap_southeast", "ap_northeast", "ap_southeast2", "ap_south",
    )),
    "fallguys": ("Fall Guys", (
        "eu_west", "eu_central", "us_east", "us_west", "sa_east",
        "ap_southeast", "ap_northeast", "ap_southeast2",
    )),
}


def probe_region(region, attempts=3, timeout=1.1, port=443):
    """TCP latency to one region's reference endpoint."""
    host = REGIONS.get(region, ("", ""))[0]
    if not host:
        return {"key": region, "host": "", "ping": None, "loss": 100}

    samples = []
    failures = 0
    for _ in range(max(1, attempts)):
        start = time.perf_counter()
        try:
            connection = socket.create_connection((host, port), timeout=timeout)
            connection.close()
            samples.append((time.perf_counter() - start) * 1000)
        except OSError:
            failures += 1
    total = failures + len(samples)
    ping = round(statistics.median(samples), 1) if samples else None
    loss = round(failures * 100 / total) if total else 100
    return {"key": region, "host": host, "ping": ping, "loss": loss}


def regions_for(game=None):
    """Regions to test for a game, or every known region when unknown."""
    if game and game in GAMES:
        return GAMES[game][1]
    return tuple(REGIONS.keys())


def rank_regions(game=None, attempts=3, timeout=1.1):
    """Probe every region of a game, fastest first, unreachable last.

    When the game is not one of the presets (for example a game detected on
    this PC), every known region is tested.
    """
    regions = regions_for(game)
    if not regions:
        return []
    with ThreadPoolExecutor(max_workers=max(1, len(regions))) as pool:
        rows = list(pool.map(lambda key: probe_region(key, attempts, timeout), regions))
    rows.sort(key=lambda row: (row["ping"] is None, row["ping"] or 0.0))
    return rows


def best_region(rows):
    for row in rows or []:
        if row.get("ping") is not None:
            return row
    return None
