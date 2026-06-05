/**
 * Shared utilities: status checking, staleness banner, card rendering.
 * Loaded on every page.
 */

const BASE = '';   // same-origin — data/ is relative to the page root

async function fetchJSON(path) {
  const resp = await fetch(BASE + path);
  if (!resp.ok) throw new Error(`${resp.status} ${path}`);
  return resp.json();
}

/** Check status.json and show staleness banner if last run > 2 hours ago. */
async function initStatus() {
  const dot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const banner = document.getElementById('stale-banner');

  try {
    const s = await fetchJSON('data/status.json');

    const lastRun = new Date(s.last_run);
    const ageHrs = (Date.now() - lastRun) / 3_600_000;
    const ago = formatAgo(lastRun);

    if (!s.success) {
      if (dot) { dot.className = 'status-dot error'; }
      if (statusText) statusText.textContent = `Last update failed ${ago}`;
      if (banner) {
        banner.textContent = `⚠ Last successful update was ${ago}. Content may be outdated.`;
        banner.style.display = 'block';
      }
    } else if (ageHrs > 2) {
      if (dot) { dot.className = 'status-dot stale'; }
      if (statusText) statusText.textContent = `Updated ${ago}`;
      if (banner) {
        banner.textContent = `⚠ Content last refreshed ${ago} — next update coming soon.`;
        banner.style.display = 'block';
      }
    } else {
      if (dot) { dot.className = 'status-dot'; }
      if (statusText) statusText.textContent = `Updated ${ago}`;
    }
  } catch (_) {
    // status.json not yet available (first deploy) — stay silent
  }
}

function formatAgo(date) {
  const mins = Math.round((Date.now() - date) / 60_000);
  if (mins < 2) return 'just now';
  if (mins < 60) return `${mins} minutes ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs !== 1 ? 's' : ''} ago`;
  const days = Math.round(hrs / 24);
  return `${days} day${days !== 1 ? 's' : ''} ago`;
}

/** Build a photo card element from an image object. */
function buildCard(img) {
  const card = document.createElement('div');
  card.className = 'card';
  card.dataset.era = img.era || '';
  card.dataset.category = img.category || '';

  const tags = [];
  if (img.era) tags.push(`<span class="tag era">${img.era}</span>`);
  if (img.category && img.category !== 'historical') {
    tags.push(`<span class="tag">${img.category}</span>`);
  }
  if (img.tags) {
    img.tags.split(',').slice(0, 2).forEach(t => {
      const trimmed = t.trim();
      if (trimmed) tags.push(`<span class="tag">${trimmed}</span>`);
    });
  }

  const alt = img.alt || img.description || 'Hair style photo';
  const creditName = img.photographer || 'Photographer';
  const creditLink = img.photographer_url || '#';
  const photoLink = img.photo_url || img.url;

  card.innerHTML = `
    <div class="card-img-wrap">
      <img
        src="${img.thumb}"
        data-src="${img.url}"
        alt="${escHtml(alt)}"
        class="loading"
        loading="lazy"
      />
    </div>
    <div class="card-body">
      ${tags.length ? `<div class="card-tags">${tags.join('')}</div>` : ''}
      <p class="card-alt">${escHtml(alt)}</p>
      <p class="card-credit">
        Photo by <a href="${creditLink}" target="_blank" rel="noopener">${escHtml(creditName)}</a>
        on <a href="${photoLink}" target="_blank" rel="noopener">Unsplash</a>
      </p>
    </div>`;

  // Swap thumb → regular when the image enters the viewport
  const imgEl = card.querySelector('img');
  const obs = new IntersectionObserver((entries, o) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const el = e.target;
        el.src = el.dataset.src;
        el.onload = () => el.classList.remove('loading');
        o.unobserve(el);
      }
    });
  }, { rootMargin: '200px' });
  obs.observe(imgEl);

  return card;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', initStatus);
