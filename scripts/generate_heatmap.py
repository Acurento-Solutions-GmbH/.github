#!/usr/bin/env python3
"""Generate a GitHub-style push/commit heatmap SVG for an organisation.

Counts commits per calendar day across all org repositories (default branch)
over the last 53 weeks, then renders a contribution-graph-style SVG. Run hourly
by .github/workflows/heatmap.yml and committed to profile/heatmap.svg, which the
org profile README embeds.

Why commits-per-day (not literal "push events"): GitHub's Events API only keeps
~90 days and excludes private-repo activity, so it can't drive a private-org
heatmap. Per-day commit counts are the same thing the contribution graph shows
and are fully available via the commits API with a read token.

Env:
  GH_TOKEN     token with read access to the org's (private) repos. REQUIRED —
               without it the script exits non-zero rather than regenerate the
               heatmap from only the repo it can see.
  GITHUB_ORG   organisation login (default: Acurento-Solutions-GmbH)
  OUTPUT       output path (default: profile/heatmap.svg relative to repo root)
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ORG = os.getenv("GITHUB_ORG", "Acurento-Solutions-GmbH")
TOKEN = os.getenv("GH_TOKEN", "")
OUTPUT = Path(os.getenv("OUTPUT", Path(__file__).resolve().parents[1] / "profile" / "heatmap.svg"))

API = "https://api.github.com"
DAYS = 371  # 53 weeks, aligned back to a Sunday below
WEEKS = 53


# ---------------------------------------------------------------- GitHub API

def _get(url: str) -> tuple[list | dict, str | None]:
    """GET one page; return (json, next_url)."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "acupulse-heatmap",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
        nxt = None
        link = resp.headers.get("Link", "")
        for part in link.split(","):
            if 'rel="next"' in part:
                nxt = part[part.find("<") + 1:part.find(">")]
        return data, nxt


def _paginate(url: str):
    while url:
        page, url = _get(url)
        if not isinstance(page, list):
            return
        yield from page


def list_repos() -> list[str]:
    repos = list(_paginate(f"{API}/orgs/{ORG}/repos?per_page=100&type=all"))
    return [r["full_name"] for r in repos]


def commit_days(full_name: str, since_iso: str) -> list[str]:
    """Return the YYYY-MM-DD (UTC) author date of each commit since `since_iso`."""
    days = []
    try:
        for c in _paginate(f"{API}/repos/{full_name}/commits?since={since_iso}&per_page=100"):
            ts = (((c.get("commit") or {}).get("author") or {}).get("date"))
            if ts:
                d = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
                days.append(d.strftime("%Y-%m-%d"))
    except urllib.error.HTTPError as e:
        # Empty repo (409) or no access (404) — skip quietly.
        if e.code not in (404, 409):
            print(f"  ! {full_name}: HTTP {e.code}", file=sys.stderr)
    return days


# ---------------------------------------------------------------- rendering

CELL, GAP = 12, 3
STEP = CELL + GAP
TOP, LEFT = 20, 30
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def level(count: int) -> int:
    if not count:
        return 0
    if count < 2:
        return 1
    if count < 5:
        return 2
    if count < 10:
        return 3
    return 4


def render_svg(counts: dict[str, int]) -> str:
    end = date.today()
    start = end - timedelta(days=DAYS - 1)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday (Sun=0)

    width = LEFT + WEEKS * STEP + 10
    height = TOP + 7 * STEP + 30
    total = sum(counts.values())

    rects, months, last_month = [], [], -1
    d, col = start, 0
    while d <= end:
        dow = (d.weekday() + 1) % 7  # Sun=0 .. Sat=6
        col = (d - start).days // 7
        x = LEFT + col * STEP
        y = TOP + dow * STEP
        iso = d.strftime("%Y-%m-%d")
        cnt = counts.get(iso, 0)
        label = f"{iso} — {cnt} commit{'' if cnt == 1 else 's'}" if cnt else f"{iso} — no commits"
        rects.append(
            f'<rect class="lvl-{level(cnt)}" x="{x}" y="{y}" width="{CELL}" '
            f'height="{CELL}" rx="2"><title>{label}</title></rect>'
        )
        if dow == 0 and d.month != last_month:
            months.append(f'<text x="{x}" y="{TOP - 6}" class="lbl">{MONTHS[d.month - 1]}</text>')
            last_month = d.month
        d += timedelta(days=1)

    dows = "".join(
        f'<text x="2" y="{TOP + i * STEP + 9}" class="lbl">{lbl}</text>'
        for i, lbl in enumerate(["", "Mon", "", "Wed", "", "Fri", ""]) if lbl
    )

    # Legend
    lx = LEFT + WEEKS * STEP - 150
    ly = TOP + 7 * STEP + 16
    legend = f'<text x="{lx - 30}" y="{ly + 10}" class="lbl">Less</text>'
    for i in range(5):
        legend += f'<rect class="lvl-{i}" x="{lx + i * 16}" y="{ly}" width="{CELL}" height="{CELL}" rx="2"/>'
    legend += f'<text x="{lx + 5 * 16 + 4}" y="{ly + 10}" class="lbl">More</text>'

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" \
viewBox="0 0 {width} {height}" role="img" aria-label="Organisation push activity heatmap">
  <style>
    text.lbl {{ fill:#57606a; font:10px -apple-system,Segoe UI,Helvetica,Arial,sans-serif; }}
    text.title {{ fill:#24292f; font:600 13px -apple-system,Segoe UI,Helvetica,Arial,sans-serif; }}
    rect {{ stroke:rgba(27,31,35,0.06); stroke-width:1px; }}
    .lvl-0 {{ fill:#ebedf0; }} .lvl-1 {{ fill:#9be9a8; }} .lvl-2 {{ fill:#40c463; }}
    .lvl-3 {{ fill:#30a14e; }} .lvl-4 {{ fill:#216e39; }}
  </style>
  <text x="0" y="12" class="title">{total} commits pushed in the last year</text>
  {"".join(months)}
  {dows}
  {"".join(rects)}
  {legend}
  <text x="0" y="{height - 4}" class="lbl">updated {updated}</text>
</svg>
'''


# ---------------------------------------------------------------- main

def main() -> None:
    if not TOKEN:
        # Fail loudly rather than overwrite a good heatmap with degraded data:
        # without an org-read token we'd only see this one repo.
        sys.exit("ERROR: GH_TOKEN is required (set the ORG_READ_TOKEN secret). "
                 "Refusing to regenerate the heatmap with only this repo's data.")

    counts: dict[str, int] = {}
    since = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repos = list_repos()
    print(f"{ORG}: {len(repos)} repos")
    for full_name in repos:
        days = commit_days(full_name, since)
        for day in days:
            counts[day] = counts.get(day, 0) + 1
        print(f"  {full_name}: {len(days)} commits")

    svg = render_svg(counts)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUTPUT} ({sum(counts.values())} commits across {len(counts)} active days)")


if __name__ == "__main__":
    main()
