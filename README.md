# .github

Organisation-level GitHub config for **Acurento-Solutions-GmbH**.

- [`profile/README.md`](profile/README.md) — the public org profile shown at
  [github.com/Acurento-Solutions-GmbH](https://github.com/Acurento-Solutions-GmbH).
- [`profile/heatmap.svg`](profile/heatmap.svg) — push-activity heatmap, auto-generated.
- [`scripts/generate_heatmap.py`](scripts/generate_heatmap.py) — builds the heatmap.
- [`.github/workflows/heatmap.yml`](.github/workflows/heatmap.yml) — regenerates it hourly.

## Push heatmap

A scheduled Action counts commits per day across **all** org repositories (default
branch, last 53 weeks), renders a contribution-graph-style SVG, and commits it to
`profile/heatmap.svg`, which the profile README embeds. It runs **hourly** and on
manual **Run workflow**.

> It counts commits-per-day, not literal push events: GitHub's Events API only
> retains ~90 days and omits private-repo activity, so it can't drive a private-org
> heatmap. Per-day commit counts are what the contribution graph shows anyway.

### Setup (one-time)

The default `GITHUB_TOKEN` can only read **this** repo, so to count commits across
the org's other (private) repos the workflow needs a read token:

1. Create a token with read access to the org's repo contents:
   - **Fine-grained PAT** (recommended): Resource owner = `Acurento-Solutions-GmbH`,
     all repositories, **Contents: Read-only**. Or
   - **Classic PAT** with the `repo` scope.
2. Add it as an org or repo **Actions secret** named `ORG_READ_TOKEN`
   (Settings → Secrets and variables → Actions).
3. Run the workflow once: **Actions → Update push heatmap → Run workflow**.

Without `ORG_READ_TOKEN` the heatmap still renders, but only counts commits in this
`.github` repo (whatever the job token can see).

### Local run

```bash
GH_TOKEN=$(gh auth token) python scripts/generate_heatmap.py
# writes profile/heatmap.svg
```
