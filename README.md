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
