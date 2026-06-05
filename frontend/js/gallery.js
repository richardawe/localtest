/**
 * Gallery page: infinite-scroll paginated masonry grid with era/style filters.
 */

let catalog = null;
let currentPage = 0;
let loading = false;
let activeEra = 'all';
let activeCategory = 'all';

const grid = document.getElementById('gallery-grid');
const sentinel = document.getElementById('scroll-sentinel');
const filterBar = document.getElementById('filter-bar');

async function initGallery() {
  try {
    catalog = await fetchJSON('data/catalog.json');
  } catch (_) {
    showEmpty('Could not load catalog. The first data run may still be in progress.');
    return;
  }

  buildFilters();
  await loadNextPage();
  initInfiniteScroll();
}

function buildFilters() {
  // Era filters
  const eras = Object.keys(catalog.era_counts || {})
    .filter(e => catalog.era_counts[e] > 0)
    .sort();

  // Category filters (exclude 'historical' bucket which is era-indexed)
  const cats = Object.keys(catalog.category_counts || {})
    .filter(c => c && c !== 'historical' && catalog.category_counts[c] > 0)
    .sort();

  const makeBtn = (value, label, group) => {
    const btn = document.createElement('button');
    btn.className = 'filter-btn' + (value === 'all' ? ' active' : '');
    btn.textContent = label;
    btn.dataset.group = group;
    btn.dataset.value = value;
    btn.addEventListener('click', () => onFilter(btn, group, value));
    return btn;
  };

  // Era group
  if (eras.length) {
    const sep = document.createElement('span');
    sep.className = 'tag';
    sep.textContent = 'Era:';
    filterBar.appendChild(sep);
    filterBar.appendChild(makeBtn('all', 'All eras', 'era'));
    eras.forEach(e => filterBar.appendChild(makeBtn(e, e, 'era')));
  }

  // Style group
  if (cats.length) {
    const sep = document.createElement('span');
    sep.className = 'tag';
    sep.style.marginLeft = '.5rem';
    sep.textContent = 'Style:';
    filterBar.appendChild(sep);
    filterBar.appendChild(makeBtn('all', 'All styles', 'cat'));
    cats.slice(0, 10).forEach(c =>
      filterBar.appendChild(makeBtn(c, titleCase(c), 'cat'))
    );
  }
}

function onFilter(btn, group, value) {
  // Deactivate sibling buttons in this group
  filterBar.querySelectorAll(`[data-group="${group}"]`)
    .forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  if (group === 'era') activeEra = value;
  if (group === 'cat') activeCategory = value;

  // Re-filter visible cards without re-fetching
  applyFilter();
}

function applyFilter() {
  grid.querySelectorAll('.card').forEach(card => {
    const eraMatch = activeEra === 'all' || card.dataset.era === activeEra;
    const catMatch = activeCategory === 'all' || card.dataset.category === activeCategory;
    card.style.display = eraMatch && catMatch ? '' : 'none';
  });
}

async function loadNextPage() {
  if (loading) return;
  if (catalog && currentPage >= catalog.total_pages) return;

  loading = true;
  showSpinner(true);

  try {
    const page = currentPage + 1;
    const data = await fetchJSON(`data/page_${String(page).padStart(3, '0')}.json`);
    currentPage = page;

    (data.images || []).forEach(img => {
      const card = buildCard(img);
      grid.appendChild(card);
    });

    applyFilter();
  } catch (e) {
    if (currentPage === 0) {
      showEmpty('No images yet — the first hourly run will populate the gallery.');
    }
  } finally {
    loading = false;
    showSpinner(false);
  }
}

function initInfiniteScroll() {
  const obs = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) loadNextPage();
  }, { rootMargin: '400px' });
  if (sentinel) obs.observe(sentinel);
}

function showSpinner(show) {
  const el = document.getElementById('spinner');
  if (el) el.style.display = show ? 'flex' : 'none';
}

function showEmpty(msg) {
  grid.innerHTML = `<div class="empty-state"><h2>No images yet</h2><p>${msg}</p></div>`;
}

function titleCase(str) {
  return str.replace(/\b\w/g, c => c.toUpperCase());
}

document.addEventListener('DOMContentLoaded', initGallery);
