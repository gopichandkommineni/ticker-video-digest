# Moving this into its own private repo

This directory was built inside `ticker-video-digest` only because the agent
session that created it could not create a GitHub repository (the integration
returned `403 Resource not accessible by integration` on `POST /user/repos`).
Committing it here made the work durable; it was never meant to live here.

Career Compass has nothing to do with the trading dashboard, and its
`profile/resume.yaml` and `data/career.db` will eventually hold personal career
data. Move it out.

## Option A — clean start (recommended)

Simplest, and you lose nothing but a single scaffolding commit.

```bash
gh repo create career-compass --private --clone
cp -r /path/to/ticker-video-digest/career-compass/. career-compass/
cd career-compass
rm EXTRACT-TO-NEW-REPO.md
git add -A
git commit -m "feat: career compass — architecture, data model, and decision log"
git push -u origin main
```

## Option B — keep the commit history

```bash
cd /path/to/ticker-video-digest
git subtree split --prefix=career-compass -b career-compass-only

gh repo create career-compass --private
cd $(mktemp -d) && git init career-compass && cd career-compass
git pull /path/to/ticker-video-digest career-compass-only
rm EXTRACT-TO-NEW-REPO.md && git add -A && git commit -m "chore: remove extraction note"
git remote add origin git@github.com:<you>/career-compass.git
git push -u origin main
```

## Then, in `ticker-video-digest`

```bash
git rm -r career-compass
git commit -m "chore: move career-compass to its own repository"
```

## After the move

1. `.github/workflows/` becomes live once it is at the repo root — it is inert
   here. Add `ANTHROPIC_API_KEY` to the new repo's secrets before enabling the
   schedules, and leave them disabled until M6 (`docs/07-roadmap.md`), since
   there is nothing to run yet.
2. **Confirm the repo is private.** `profile/resume.yaml` and `manual/` are
   gitignored, but that protects you from accidents, not from a public repo.
3. Start at M1 in `docs/07-roadmap.md` — `career profile show` is useful
   before a single company is ingested.

Delete this file once the move is done.
