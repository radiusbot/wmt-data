# wmt-data

Static website and remote config for the **Where is My Train** app, served at
**https://radiusbot.com/wmt-data/** (GitHub Pages project site of `radiusbot/wmt-data`. The custom
domain `radiusbot.com` comes from the owner's user site `radiusbot/radiusbot.github.io`).

This repo holds **no railway data**. The owner decided on 2026-11-25 not to publish a timetable,
after reading the NTES terms of use. The app on each phone reads the public Indian Railways pages
itself. See [docs/SOURCES.md](docs/SOURCES.md) for the source findings and the decision.

## What is published

| File | Purpose |
|---|---|
| `site/index.html` | Landing page |
| `site/privacy.html`, `site/terms.html` | Privacy policy and terms (**DRAFT, pending owner review**) |
| `site/config.json` | Remote kill switches and app settings. Contract: `../docs/contracts/remote_files.md` |
| `site/parser-config.json` | Copy of `app/assets/config/parser-config.json`. Never edit it here. |
| `site/style.css` | Shared styles (light and dark) |

`app-ads.txt` is **not** published from here: it is only valid at a domain root, so it lives at
`https://radiusbot.com/app-ads.txt` in the `radiusbot/radiusbot.github.io` repo.

## Everyday tasks

```sh
make venv                 # once: .venv with pytest, ruff, mypy (the validator itself is stdlib only)
make check                # ruff + mypy + pytest + validate site/ (same as CI)
```

* **Turn a source off** (for example, Indian Railways asks us to stop, or a page layout broke): set
  `sources.<name>` to `false` in `site/config.json`, run `make check`, then merge to `main`.
  Phones pick it up on their next config fetch, with no app update.
* **Show a message in the app:** set `notice` to a short string. Set it back to `null` to remove it.
* **Force an update:** raise `minSupportedAppVersion`.
* **Ship a parser fix without an app release:** bump `version` in
  `app/assets/config/parser-config.json`, then `make sync-parser-config` (`APP_REPO` defaults to `../app`).
  The sync refuses an invalid file and refuses to replace a newer published version. Phones use the
  remote copy only when its `version` is higher than the bundled one.

`make check-site` (also `python -m wmt_data check`) fails on missing pages, invalid JSON, duplicate
keys, unknown or missing `config.json` keys (including each `sources` entry, because the app treats a
missing key as enabled and ignores unknown keys), a bad version string, or a `parser-config.json`
without an integer `version`.

## CI and deploy

* `.github/workflows/ci.yml` runs `make check` on every pull request.
* `.github/workflows/deploy.yml` runs the same check on every push to `main`, then deploys `site/`
  with `actions/upload-pages-artifact` and `actions/deploy-pages`. Every action is pinned to a commit SHA.
  There is no schedule and no crawling.

## One-time owner setup

1. Create the GitHub repo `radiusbot/wmt-data` and push this folder to `main`.
2. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Check that `radiusbot/radiusbot.github.io` has the custom domain `radiusbot.com` set and
   "Enforce HTTPS" on. The project site then appears at `https://radiusbot.com/wmt-data/`.
4. **app-ads.txt:** in the `radiusbot/radiusbot.github.io` repo, add a file `app-ads.txt` at the
   repository root (next to its `CNAME`). It contains the single line AdMob shows under
   *Apps → View all apps → app-ads.txt*, which looks like
   `google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0`. Commit to the branch that site publishes from.
   Check that `https://radiusbot.com/app-ads.txt` serves it. On Google Play and the App Store, the
   developer website must be `https://radiusbot.com` (the domain root) for AdMob to find it.
5. Review `site/privacy.html` and `site/terms.html`: fill every `[bracketed]` item, then remove the DRAFT
   banners.
