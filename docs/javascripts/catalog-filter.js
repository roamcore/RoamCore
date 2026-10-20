// RoamCore docs: simple client-side filtering for catalog cards
// Filters elements with: .rc-card[data-tier][data-tags][data-title]

(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function norm(s) {
    return String(s || '').trim().toLowerCase();
  }

  function splitTags(s) {
    return norm(s).split(',').map(t => t.trim()).filter(Boolean);
  }

  function applyFilters(root) {
    const state = root.__rcFilterState || { tier: 'all', q: '' };
    const tier = state.tier;
    const q = norm(state.q);

    const cards = qsa('.rc-card[data-tier]', root);
    let shown = 0;

    for (const c of cards) {
      const t = norm(c.getAttribute('data-tier'));
      const title = norm(c.getAttribute('data-title') || c.textContent);
      const tags = splitTags(c.getAttribute('data-tags'));

      const tierOk = (tier === 'all') || (t === tier);
      const qOk = !q || title.includes(q) || tags.some(x => x.includes(q));
      const ok = tierOk && qOk;

      c.style.display = ok ? '' : 'none';
      if (ok) shown++;
    }

    const counter = qs('[data-rc-filter-counter]', root);
    if (counter) counter.textContent = String(shown);
  }

  function setTier(root, tier) {
    root.__rcFilterState = root.__rcFilterState || { tier: 'all', q: '' };
    root.__rcFilterState.tier = tier;

    // update active styles
    qsa('[data-rc-tier]', root).forEach(btn => {
      const v = norm(btn.getAttribute('data-rc-tier'));
      btn.classList.toggle('active', v === tier);
    });

    applyFilters(root);
  }

  function setQuery(root, q) {
    root.__rcFilterState = root.__rcFilterState || { tier: 'all', q: '' };
    root.__rcFilterState.q = q;
    applyFilters(root);
  }

  function init() {
    const roots = qsa('[data-rc-filter-root]');
    for (const root of roots) {
      // default
      root.__rcFilterState = { tier: 'all', q: '' };

      qsa('[data-rc-tier]', root).forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          setTier(root, norm(btn.getAttribute('data-rc-tier')));
        });
      });

      const input = qs('[data-rc-filter-q]', root);
      if (input) {
        input.addEventListener('input', () => setQuery(root, input.value));
      }

      const clear = qs('[data-rc-filter-clear]', root);
      if (clear) {
        clear.addEventListener('click', (e) => {
          e.preventDefault();
          if (input) input.value = '';
          setQuery(root, '');
          setTier(root, 'all');
        });
      }

      setTier(root, 'all');
      applyFilters(root);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
