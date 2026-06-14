# I Built a Fully Automated, AI-Powered Content Platform for $0/Month — Here's the Architecture

There's a persistent myth in the AI space: that doing something meaningful with machine learning requires cloud GPU bills, OpenAI API credits, and a team of engineers.

I want to challenge that directly.

I recently built **Crown & Culture** — a live, hourly-updated gallery and editorial platform celebrating Black and African women's hairstyles and hair culture. It surfaces curated images, Wikipedia-grounded historical narratives spanning the 1920s to today, AI-written blog posts synthesized from real news, and a searchable gallery with infinite scroll and era filtering.

It runs entirely automatically. And it costs **nothing** to operate.

---

## The Stack (and Why Each Piece Is Free)

**AI / LLM: Ollama + llama3.1:8b — $0**

Rather than routing every prompt through a paid API, the pipeline runs a local language model via Ollama on consumer hardware. The model handles three jobs: generating search queries, filtering image relevance (a deterministic YES/NO classifier at temperature 0.0), and synthesizing blog posts from real news sources. No monthly bill. No token counting. No rate limit anxiety.

**Image Source: Unsplash API — $0**

Unsplash's free tier allows 50 requests per hour. The pipeline makes at most 12 per run — well within budget. Every image includes photographer attribution, and the API returns portrait-oriented, high-quality photos with structured metadata. Licensed. Legal. Free.

**Historical Content: Wikipedia REST API — $0**

Instead of asking an LLM to invent history (and hallucinate), the historian module fetches real Wikipedia article extracts — covering the Natural Hair Movement, Afro, Cornrows, Dreadlocks, the CROWN Act, and more — and passes them verbatim to the model. The prompt explicitly forbids the LLM from adding any fact not present in the provided source. RAG without a vector database. No drift. No fabrication.

**News: Google News RSS — $0**

Eight rotating search queries hit Google News RSS feeds. No API key. No auth. Fully public. The results feed the blog writer, which synthesizes editorial posts with natural source attribution ("According to Essence…").

**Database: SQLite — $0**

A single file on disk handles deduplication, pagination metadata, blog archives, and historical narratives. No Postgres instance. No Redis. No connection pooling headaches.

**Hosting: GitHub Pages — $0**

The deployment step uses a git worktree to atomically push a static frontend — HTML, CSS, vanilla JavaScript — to an orphan `gh-pages` branch. GitHub serves it globally via CDN. Zero infrastructure to manage.

**Scheduling: macOS launchd — $0**

A single `.plist` file fires the pipeline every hour at `:00 UTC`. No cron daemon to babysit. No cloud scheduler to configure.

---

## The Architecture in One Paragraph

Every hour: Ollama generates search queries → Unsplash returns images → Ollama filters for relevance → approved images land in SQLite → data exports (paginated JSON, catalog, status) are written to disk → a git worktree commits the entire frontend + data layer to `gh-pages` → GitHub Pages serves the result. Once daily at midnight: Wikipedia articles are fetched, decade narratives are generated with RAG constraints, news RSS feeds are pulled, and a blog post is synthesized. The whole thing is orchestrated by a 100-line Python script with structured logging.

That's it.

---

## What Makes This Interesting Beyond the Project Itself

The pattern here — local LLM + free public APIs + static hosting + SQLite — is not niche. It's a blueprint that applies to dozens of common business problems that companies currently solve with expensive SaaS tools or avoid entirely because "AI is too costly."

**Who should be paying attention:**

**Independent Media & Newsletter Publishers** — Automated content aggregation, editorial synthesis, and trend spotting without a content team or a Substack/Beehiiv API bill. Run it on your laptop overnight.

**Cultural Organizations and Non-Profits** — Museums, advocacy groups, cultural archives, and educational platforms often have rich source material (archives, Wikipedia, public domain collections) but no budget for AI tooling. This pattern unlocks AI-assisted curation at zero marginal cost.

**Boutique E-commerce Brands** — A skincare brand, a natural hair product company, a fashion label — each could run a similar pipeline to surface user-generated style content, synthesize trend reports, and maintain a living editorial presence without hiring a content strategist.

**Recruitment and HR Teams** — Swap the domain: instead of hairstyles, index job market signals. Pull from Google News RSS on your industry, synthesize weekly briefings via a local LLM, store in SQLite, serve via GitHub Pages to your team. Same stack, different data.

**Local Journalism and Community Media** — Hyperlocal news aggregation, community event synthesis, neighborhood trend coverage — all achievable with this architecture and zero cloud spend.

**Academic Researchers and Digital Humanities Teams** — Wikipedia RAG + LLM synthesis is genuinely useful for survey generation, literature review bootstrapping, and building living encyclopedias in specialized domains.

---

## The Simplicity Is the Point

We've collectively overcomplicated AI-powered products. The assumption is that useful AI requires:
- Managed vector databases (Pinecone, Weaviate, Qdrant)
- LLM API subscriptions (OpenAI, Anthropic, Cohere)
- Containerized microservices
- Cloud object storage
- A DevOps engineer on retainer

Crown & Culture demonstrates that none of that is required to build something genuinely useful, well-designed, and automatically maintained.

The relevance classifier is 15 lines of Python. The RAG system is a Wikipedia fetch + a prompt constraint. The deployment pipeline is a git worktree. The entire backend is five modules and an orchestrator.

The elegance isn't in the complexity — it's in choosing the simplest tool that does the job.

---

## What's Next

The same architecture scales. Unsplash's production tier (5,000 req/hr) is available for teams that outgrow the free tier. Ollama supports model swaps without code changes — upgrade to a larger model as hardware improves. SQLite handles millions of rows before you'd ever need Postgres.

And if you want to run this in the cloud? The local LLM is the only component that changes — swap Ollama for any hosted inference endpoint and the rest runs identically on any Linux server or CI runner.

The zero-cost floor is real. The ceiling is wherever you need it to be.

---

*If you're building something similar, or work in an organization that could benefit from this pattern, I'd love to connect. The architecture is straightforward — the value is in knowing it exists.*

#AI #MachineLearning #BuildInPublic #ZeroCost #LocalAI #Ollama #GitHubPages #ContentAutomation #BlackHairCulture #TechForGood #OpenSource #SoftwareEngineering #StaticSites #NaturalHair #CROWNAct

---

## For Property Operators (Short Version)

Property operators are sitting on a content goldmine they never publish — neighbourhood guides, local market updates, listing trends, maintenance tips, tenant FAQs — and most pay handsomely for someone to produce it or skip it entirely. This repo is a working proof that you don't have to do either. The same pipeline that powers Crown & Culture can be pointed at your market in an afternoon: swap the search queries to pull local property news via Google News RSS, swap the image source to your own listing photos or a free Unsplash search for your city, and let a local AI model (running on any office laptop, no API bill) synthesise a weekly market briefing, a neighbourhood spotlight, or a blog post about rental trends — then deploy the whole thing as a static site on GitHub Pages for free. Hourly updates, automated attribution, zero cloud spend.

If you manage a portfolio of rentals, run a letting agency, or operate a build-to-rent scheme and you're currently paying a content agency or leaving your website editorially dormant, check out the repo at github.com/richardawe/localtest. The architecture is five Python modules and a scheduler. The hosting is free. The AI runs locally. Fork it, point it at your market, and have a living editorial presence running before the end of the week — at no cost.

#PropertyManagement #RealEstate #BuildToRent #PropTech #AIForProperty #ZeroCost #ContentAutomation #LetAgents #PropertyOperators #LocalAI
