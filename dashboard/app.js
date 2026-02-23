/* ═══════════════════════════════════════════════════════════════════════════
   AI PULSE — app.js  (ZYROX Brand Edition)
   Frontend logic: data fetching, rendering, filters, modal, save/unsave
   ═══════════════════════════════════════════════════════════════════════════ */

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────
const State = {
    currentTab: 'feed',   // 'feed' | 'saved'
    activeFilter: 'all',
    searchQuery: '',
    allArticles: [],
    stats: {},
    modalArticleId: null,
    isRefreshing: false,
};

// ─────────────────────────────────────────────────────────────────────────────
// API
// ─────────────────────────────────────────────────────────────────────────────
const API = {
    async get(endpoint) {
        const resp = await fetch(endpoint);
        if (!resp.ok) throw new Error(`${endpoint} → ${resp.status}`);
        return resp.json();
    },
    async post(endpoint, body) {
        const resp = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error(`POST ${endpoint} → ${resp.status}`);
        return resp.json();
    },
};

// ─────────────────────────────────────────────────────────────────────────────
// Formatters
// ─────────────────────────────────────────────────────────────────────────────
function timeAgo(isoString) {
    if (!isoString) return '—';
    try {
        const diffMs = Date.now() - new Date(isoString).getTime();
        const diffMin = Math.floor(diffMs / 60000);
        const diffH = Math.floor(diffMin / 60);
        const diffD = Math.floor(diffH / 24);
        if (diffMin < 1) return 'just now';
        if (diffMin < 60) return `${diffMin}m ago`;
        if (diffH < 24) return `${diffH}h ago`;
        if (diffD < 7) return `${diffD}d ago`;
        return new Date(isoString).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch { return '—'; }
}

function sourceLabel(source) {
    return { bensbites: "BEN'S BITES", therundown: "THE RUNDOWN", reddit: "REDDIT AI" }[source] || source.toUpperCase();
}

function sourceEmoji(source) {
    return { bensbites: '🍿', therundown: '⚡', reddit: '🤖' }[source] || '📰';
}

function truncate(str, n) {
    if (!str) return '';
    return str.length > n ? str.slice(0, n).trimEnd() + '…' : str;
}

function escHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

// ─────────────────────────────────────────────────────────────────────────────
// Toast
// ─────────────────────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const t = document.createElement('div');
    t.className = `toast ${type}`;

    const icons = { success: '✓', error: '✗', info: '·' };
    const cls = { success: 'toast-icon-success', error: 'toast-icon-error', info: 'toast-icon-info' };

    t.innerHTML = `<span class="${cls[type]}">${icons[type]}</span><span>${message}</span>`;
    container.appendChild(t);
    setTimeout(() => t.remove(), 3700);
}

// ─────────────────────────────────────────────────────────────────────────────
// Tab Switching
// ─────────────────────────────────────────────────────────────────────────────
function switchTab(tab) {
    State.currentTab = tab;
    State.activeFilter = 'all';
    State.searchQuery = '';

    document.getElementById('nav-feed').classList.toggle('active', tab === 'feed');
    document.getElementById('nav-saved').classList.toggle('active', tab === 'saved');

    // Reset filter chips
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    document.getElementById('filter-all').classList.add('active');
    document.getElementById('search-input').value = '';

    // Update title
    const titleEl = document.getElementById('page-title');
    if (tab === 'feed') {
        titleEl.innerHTML = `Today's <span class="accent">Feed</span>`;
        document.getElementById('feed-label').textContent = 'Latest · 24H';
    } else {
        titleEl.innerHTML = `Saved <span class="accent">Articles</span>`;
        document.getElementById('feed-label').textContent = 'Your Library';
    }

    loadData();
}

// ─────────────────────────────────────────────────────────────────────────────
// Filter + Search
// ─────────────────────────────────────────────────────────────────────────────
function applyFilter(source) {
    State.activeFilter = source;
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    const el = document.getElementById(`filter-${source}`);
    if (el) el.classList.add('active');
    renderArticles();
}

function applySearch() {
    State.searchQuery = document.getElementById('search-input').value.toLowerCase().trim();
    renderArticles();
}

function getFiltered() {
    let list = State.allArticles;
    if (State.activeFilter !== 'all') {
        list = list.filter(a => a.source === State.activeFilter);
    }
    if (State.searchQuery) {
        list = list.filter(a =>
            a.title?.toLowerCase().includes(State.searchQuery) ||
            a.summary?.toLowerCase().includes(State.searchQuery) ||
            a.author?.toLowerCase().includes(State.searchQuery)
        );
    }
    return list;
}

// ─────────────────────────────────────────────────────────────────────────────
// Data Loading
// ─────────────────────────────────────────────────────────────────────────────
async function loadData() {
    showSkeletons();
    try {
        const endpoint = State.currentTab === 'feed' ? '/api/feed' : '/api/saved';
        const data = await API.get(endpoint);
        State.allArticles = data.articles || [];
        State.stats = data.stats || {};
        updateStats(data.stats);
        renderArticles();
    } catch (err) {
        console.error('Load error:', err);
        showEmpty('Could not load articles. Is the server running on port 3737?');
        showToast('Failed to load — check server is running', 'error');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Stats Panel
// ─────────────────────────────────────────────────────────────────────────────
function updateStats(stats) {
    if (!stats) return;

    // Pill numbers
    document.getElementById('stat-total-num').textContent = stats.total_articles ?? '—';
    document.getElementById('stat-today-num').textContent = stats.today_count ?? '—';
    document.getElementById('stat-saved-num').textContent = stats.saved_count ?? '—';

    // Sidebar badges
    const feedBadge = document.getElementById('feed-badge');
    const savedBadge = document.getElementById('saved-badge-icon');
    const todayCount = stats.today_count ?? 0;
    const savedCount = stats.saved_count ?? 0;

    feedBadge.textContent = todayCount;
    savedBadge.textContent = savedCount;
    savedBadge.classList.toggle('hidden', savedCount === 0);

    // Source strip counts
    const sources = stats.sources || {};
    document.getElementById('count-bensbites').textContent = sources.bensbites ?? '0';
    document.getElementById('count-therundown').textContent = sources.therundown ?? '0';
    document.getElementById('count-reddit').textContent = sources.reddit ?? '0';

    // Source status dots
    setSourceStatus('bensbites', (sources.bensbites ?? 0) > 0);
    setSourceStatus('therundown', (sources.therundown ?? 0) > 0);
    setSourceStatus('reddit', (sources.reddit ?? 0) > 0);

    // Last sync
    const lastRun = stats.last_run;
    document.getElementById('last-run-label').textContent =
        lastRun ? timeAgo(lastRun) : 'Never';

    // Subtitle
    const n = State.allArticles.length;
    if (State.currentTab === 'feed') {
        document.getElementById('page-subtitle').textContent =
            n === 0
                ? '// no new content in the last 24h'
                : `// ${n} article${n !== 1 ? 's' : ''} from the last 24h`;
    } else {
        document.getElementById('page-subtitle').textContent =
            n === 0
                ? '// your saved library is empty'
                : `// ${n} article${n !== 1 ? 's' : ''} in your library`;
    }
}

function setSourceStatus(source, isActive) {
    const el = document.getElementById(`status-${source}`);
    if (!el) return;
    el.className = `source-status ${isActive ? 'ok' : 'warn'}`;
    el.textContent = '●';
}

// ─────────────────────────────────────────────────────────────────────────────
// Render
// ─────────────────────────────────────────────────────────────────────────────
function showSkeletons() {
    const grid = document.getElementById('articles-grid');
    document.getElementById('empty-state').classList.add('hidden');
    grid.innerHTML = '';
    for (let i = 0; i < 6; i++) {
        const el = document.createElement('div');
        el.className = 'skeleton-card';
        el.style.animationDelay = `${i * 0.04}s`;
        grid.appendChild(el);
    }
}

function showEmpty(message) {
    document.getElementById('articles-grid').innerHTML = '';
    document.getElementById('empty-subtitle').textContent = message;
    document.getElementById('empty-state').classList.remove('hidden');
}

function renderArticles() {
    const articles = getFiltered();
    const grid = document.getElementById('articles-grid');
    const empty = document.getElementById('empty-state');

    grid.innerHTML = '';

    if (articles.length === 0) {
        const msg = State.searchQuery
            ? `// no results for "${State.searchQuery}"`
            : State.currentTab === 'saved'
                ? '// no saved articles yet — click 🔖 to save'
                : '// no new articles in the last 24h — try refreshing';
        showEmpty(msg);
        return;
    }

    empty.classList.add('hidden');
    articles.forEach((article, i) => {
        grid.appendChild(buildCard(article, i));
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Card Builder
// ─────────────────────────────────────────────────────────────────────────────
function buildCard(article, index) {
    const card = document.createElement('div');
    card.className = 'article-card';
    card.style.animationDelay = `${index * 0.035}s`;
    card.dataset.id = article.id;

    const source = article.source || 'unknown';
    const isSaved = article.saved;

    // Image section
    const imgSection = article.image_url
        ? `<div class="card-img-wrap">
         <img class="card-img" src="${escHtml(article.image_url)}" alt="" loading="lazy" onerror="this.closest('.card-img-wrap').remove()" />
       </div>`
        : `<div class="card-img-placeholder">${sourceEmoji(source)}</div>`;

    card.innerHTML = `
    ${imgSection}
    <div class="card-body">
      <div class="card-header">
        <div class="card-source-badge ${source}">
          ${sourceEmoji(source)} ${sourceLabel(source)}
        </div>
        <button
          class="card-save-btn ${isSaved ? 'saved' : ''}"
          id="save-btn-${article.id}"
          onclick="toggleSave(event, '${article.id}')"
          title="${isSaved ? 'Remove from saved' : 'Save article'}"
          aria-label="${isSaved ? 'Remove from saved' : 'Save article'}"
        >🔖</button>
      </div>

      <h2 class="card-title">${escHtml(article.title || 'Untitled')}</h2>
      <p class="card-summary">${escHtml(truncate(article.summary, 180))}</p>

      <div class="card-footer">
        <div class="card-meta">
          <span class="card-author">${escHtml(article.author || '—')}</span>
          <span class="card-dot">·</span>
          <span class="card-time">${timeAgo(article.published_at)}</span>
        </div>
        <span class="card-arrow">→</span>
      </div>
    </div>
  `;

    card.addEventListener('click', e => {
        if (!e.target.closest('.card-save-btn')) openModal(article);
    });

    return card;
}

// ─────────────────────────────────────────────────────────────────────────────
// Save / Unsave
// ─────────────────────────────────────────────────────────────────────────────
async function toggleSave(event, articleId) {
    event.stopPropagation();
    const article = State.allArticles.find(a => a.id === articleId);
    if (!article) return;

    const wasSaved = article.saved;
    const btn = document.getElementById(`save-btn-${articleId}`);

    try {
        if (wasSaved) {
            await API.post('/api/unsave', { id: articleId });
            article.saved = false;
            article.saved_at = null;
            if (btn) { btn.classList.remove('saved'); btn.title = 'Save article'; }
            showToast('Removed from saved', 'info');
        } else {
            await API.post('/api/save', { id: articleId });
            article.saved = true;
            article.saved_at = new Date().toISOString();
            if (btn) { btn.classList.add('saved'); btn.title = 'Remove from saved'; }
            showToast('✓ Saved to library', 'success');
        }

        // Update saved badge count
        const savedCount = State.allArticles.filter(a => a.saved).length;
        const savedBadgeEl = document.getElementById('saved-badge-icon');
        savedBadgeEl.textContent = savedCount;
        savedBadgeEl.classList.toggle('hidden', savedCount === 0);
        document.getElementById('stat-saved-num').textContent = savedCount;

        if (State.currentTab === 'saved') {
            State.allArticles = State.allArticles.filter(a => a.saved);
            renderArticles();
        }

        updateModalSaveBtn(articleId);

    } catch (err) {
        console.error('Save error:', err);
        showToast('Save failed', 'error');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Modal
// ─────────────────────────────────────────────────────────────────────────────
function openModal(article) {
    State.modalArticleId = article.id;
    const source = article.source || 'unknown';

    // Source badge styling
    const badgeEl = document.getElementById('modal-source');
    badgeEl.textContent = `${sourceEmoji(source)} ${sourceLabel(source)}`;
    badgeEl.className = `modal-source-badge ${source}`;
    const badgeCss = {
        bensbites: 'background:rgba(232,168,56,0.12);color:#E8A838;border:1px solid rgba(232,168,56,0.25)',
        therundown: 'background:rgba(155,135,245,0.12);color:#9B87F5;border:1px solid rgba(155,135,245,0.25)',
        reddit: 'background:rgba(224,90,58,0.12);color:#E05A3A;border:1px solid rgba(224,90,58,0.25)',
    };
    badgeEl.style.cssText = badgeCss[source] || '';

    // Image
    const imgWrap = document.getElementById('modal-img-wrap');
    const img = document.getElementById('modal-img');
    if (article.image_url) {
        img.src = article.image_url;
        img.alt = article.title || '';
        imgWrap.classList.remove('hidden');
    } else {
        imgWrap.classList.add('hidden');
        img.src = '';
    }

    // Text content
    document.getElementById('modal-title').textContent = article.title || 'Untitled';
    document.getElementById('modal-author').textContent = article.author || 'Unknown';
    document.getElementById('modal-date').textContent = timeAgo(article.published_at);
    document.getElementById('modal-summary').textContent = article.summary || 'No summary available.';

    // Tags
    const tagsEl = document.getElementById('modal-tags');
    tagsEl.innerHTML = '';
    (article.tags || []).forEach(tag => {
        const s = document.createElement('span');
        s.className = 'modal-tag';
        s.textContent = tag;
        tagsEl.appendChild(s);
    });

    // Read link
    document.getElementById('modal-read-btn').href = article.url || '#';

    // Save button state
    updateModalSaveBtn(article.id);

    // Show
    document.getElementById('modal-overlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function updateModalSaveBtn(articleId) {
    if (State.modalArticleId !== articleId) return;
    const article = State.allArticles.find(a => a.id === articleId);
    if (!article) return;

    const btn = document.getElementById('modal-save-btn');
    if (!btn) return;

    if (article.saved) {
        btn.textContent = '✓ Saved';
        btn.classList.add('saved');
    } else {
        btn.textContent = '🔖 Save';
        btn.classList.remove('saved');
    }
}

async function toggleSaveFromModal() {
    if (!State.modalArticleId) return;
    const article = State.allArticles.find(a => a.id === State.modalArticleId);
    if (!article) return;
    const fakeEvent = { stopPropagation: () => { } };
    await toggleSave(fakeEvent, State.modalArticleId);
}

function closeModal(event) {
    // Only close if clicking the overlay itself, not the modal card
    if (event && event.target !== document.getElementById('modal-overlay')) return;
    _closeModal();
}

function _closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
    document.body.style.overflow = '';
    State.modalArticleId = null;
}

document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) _closeModal();
});

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') _closeModal();
});

// ─────────────────────────────────────────────────────────────────────────────
// Refresh
// ─────────────────────────────────────────────────────────────────────────────
async function triggerRefresh() {
    if (State.isRefreshing) return;
    State.isRefreshing = true;

    const icon = document.getElementById('refresh-icon');
    const btn = document.getElementById('refresh-btn');
    icon.classList.add('spinning');
    btn.disabled = true;

    showToast('Scraping latest AI articles...', 'info');

    try {
        const result = await API.get('/api/refresh');
        const newCount = result.store?.new_articles ?? 0;

        showToast(
            newCount > 0
                ? `✓ ${newCount} new article${newCount !== 1 ? 's' : ''} found`
                : '// no new articles since last sync',
            newCount > 0 ? 'success' : 'info'
        );

        await loadData();
    } catch (err) {
        console.error('Refresh error:', err);
        showToast('Refresh failed — check scraper deps', 'error');
    } finally {
        icon.classList.remove('spinning');
        btn.disabled = false;
        State.isRefreshing = false;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadData();
});
