/**
 * Timeline page: decade-by-decade scroll with Wikipedia-grounded narratives.
 */

const DECADES = [
  '1920s','1930s','1940s','1950s','1960s',
  '1970s','1980s','1990s','2000s','2010s','2020s',
];

const container = document.getElementById('timeline-decades');
const navLinks = document.querySelectorAll('.timeline-nav a');

async function initTimeline() {
  for (const decade of DECADES) {
    await renderDecade(decade);
  }
  initScrollSpy();
}

async function renderDecade(decade) {
  let data = { era: decade, narrative: '', images: [] };
  try {
    data = await fetchJSON(`data/historical/${decade}.json`);
  } catch (_) {
    // Decade data not yet generated — render empty placeholder
  }

  const block = document.createElement('section');
  block.className = 'decade-block';
  block.id = `decade-${decade}`;

  const narrative = data.narrative
    ? `<p class="decade-narrative">${escHtml(data.narrative)}</p>`
    : `<p class="decade-narrative"><em>Narrative will appear after the first daily update.</em></p>`;

  let imagesHtml = '';
  if (data.images && data.images.length) {
    imagesHtml = '<div class="decade-grid"></div>';
  }

  block.innerHTML = `
    <h2 class="decade-label">${decade}</h2>
    ${narrative}
    ${imagesHtml}`;

  if (data.images && data.images.length) {
    const decadeGrid = block.querySelector('.decade-grid');
    data.images.slice(0, 6).forEach(img => {
      decadeGrid.appendChild(buildCard(img));
    });
  }

  container.appendChild(block);
}

function initScrollSpy() {
  const blocks = document.querySelectorAll('.decade-block');
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        navLinks.forEach(a => {
          a.classList.toggle('active', a.getAttribute('href') === `#${id}`);
        });
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });

  blocks.forEach(b => obs.observe(b));
}

document.addEventListener('DOMContentLoaded', initTimeline);
