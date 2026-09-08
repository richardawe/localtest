# Crown & Culture

Hourly-updated gallery of Black and African women's hair trends.
**Live site:** https://richardawe.github.io/localtest

## How it works

| Layer | Technology |
|-------|-----------|
| Research | Ollama `llama3.1:8b` generates search queries and summaries |
| Historical grounding | Wikipedia REST API → Ollama RAG (no hallucination) |
| Images | Unsplash API (licensed, hotlink-permitted, attribution shown) |
| Storage | SQLite local database |
| Deployment | `gh-pages` branch via git worktree |
| Scheduling | macOS launchd — fires at :00 every hour |
| Frontend | Static HTML/CSS/JS on GitHub Pages |

---

## One-time setup

### 1. Create the `gh-pages` branch

```bash
git checkout --orphan gh-pages
git reset --hard
echo "<html><body>Deploying…</body></html>" > index.html
git add index.html
git commit -m "chore: init gh-pages"
git push origin gh-pages
git checkout main
```

### 2. Enable GitHub Pages

Go to: **GitHub repo → Settings → Pages**
- Source: `Deploy from a branch`
- Branch: `gh-pages` / `/ (root)`
- Click **Save**

### 3. Get API keys

| Key | Where |
|-----|-------|
| Unsplash Access Key | https://unsplash.com/developers → New Application |
| GitHub PAT | https://github.com/settings/tokens → New token → `repo` scope |

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in both keys
```

### 5. Install Python dependencies

```bash
/opt/homebrew/bin/pip3.11 install -r backend/requirements.txt
```

### 6. Run once manually to seed data

```bash
/opt/homebrew/bin/python3.11 backend/main.py
```

This seeds the SQLite database, exports JSON, and deploys to `gh-pages`.
GitHub Pages will be live within ~1 minute of the push.

### 7. Install the hourly launchd job

```bash
cp com.hairtrends.agent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.hairtrends.agent.plist
```

To verify it loaded:
```bash
launchctl list | grep hairtrends
```

To run it immediately (for testing):
```bash
launchctl start com.hairtrends.agent
```

To uninstall:
```bash
launchctl unload ~/Library/LaunchAgents/com.hairtrends.agent.plist
rm ~/Library/LaunchAgents/com.hairtrends.agent.plist
```

---

## Project structure

```
localtest/
├── backend/
│   ├── main.py           # Entry point (called by launchd)
│   ├── researcher.py     # Ollama keyword + summary generation
│   ├── image_fetcher.py  # Unsplash API client + SQLite store
│   ├── historian.py      # Wikipedia RAG + decade narratives
│   ├── data_manager.py   # Paginated JSON export
│   ├── git_publisher.py  # gh-pages worktree deploy
│   ├── config.py         # Constants and taxonomy
│   └── requirements.txt
├── frontend/             # Static site source (deployed to gh-pages)
│   ├── index.html        # Latest trends
│   ├── gallery.html      # Full filterable gallery
│   ├── timeline.html     # Historical timeline
│   ├── css/style.css
│   └── js/
│       ├── app.js        # Shared utilities
│       ├── gallery.js    # Infinite scroll + filters
│       └── timeline.js   # Decade rendering + scroll spy
├── .env                  # API keys (gitignored)
├── .env.example
├── com.hairtrends.agent.plist
└── README.md
```

---

## Nigeria content desk (ngr.ltd blog)

A second, independent pipeline — same Mac, same Ollama model, its own SQLite
database and launchd schedule — that writes drafts for
[ngr.ltd/blog](https://ngr.ltd/blog) and pushes them into its admin review
queue. Nothing it produces goes live on its own: every push lands as a draft
at `ngr.ltd/admin/blog-posts` and needs a human approval before it's public.

| Layer | Technology |
|-------|-----------|
| Research | Google News RSS, one Nigeria-focused category per run (news, culture, notable people, tech, entertainment, lifestyle) |
| Writing | Ollama `llama3.1:8b` — original commentary citing sources, never reproducing them |
| Images | Unsplash API, one cover image per post, download-tracked per Unsplash's API guidelines |
| Delivery | `POST https://ngr.ltd/api/internal/blog-posts`, bearer-token authenticated |
| Scheduling | macOS launchd — 08:00, 14:00, 20:00 daily |

### Setup

1. Add to `.env`:
   ```
   NGR_API_BASE=https://ngr.ltd
   CONTENT_PIPELINE_TOKEN=<same value as ngr.ltd's own .env — generate with `php artisan tinker` -> `Str::random(64)` on that side>
   ```
2. Run once manually to confirm it reaches ngr.ltd:
   ```bash
   /opt/homebrew/bin/python3.11 backend/main_ngr.py
   ```
3. Install the schedule:
   ```bash
   cp com.ngrblog.agent.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.ngrblog.agent.plist
   ```

Logs land in `backend/logs/ngr-YYYY-MM-DD.log`. Review and publish drafts at
`https://ngr.ltd/admin/blog-posts`.

---

## Monitoring

Logs are written to `backend/logs/` (one file per day).

The frontend reads `data/status.json` on every page load.
If the last successful update was more than 2 hours ago, a yellow banner appears.

---

## Notes

- **Sleep behaviour**: launchd fires at `:00` of each hour. If the Mac is
  asleep when the interval fires, the job runs once on wake — it does not
  replay missed intervals.
- **Unsplash free tier**: 50 requests/hour. The pipeline uses 12 queries/run —
  well within the limit. Apply for Production access (free) for 5,000 req/hr.
- **Historical narratives**: generated once per day at midnight UTC using
  Wikipedia source material as context. The LLM is instructed not to add
  facts outside the provided sources.
