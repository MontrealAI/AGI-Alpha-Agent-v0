/* Reading controls only. No analytics, storage, provider calls or remote content. */
(() => {
  'use strict';
  const root = document.documentElement;
  const language = document.getElementById('language');
  const size = document.getElementById('text-size');
  const nodes = [...document.querySelectorAll('[data-fr]')];
  const original = new Map(nodes.map(node => [node, node.textContent]));
  let french = new URLSearchParams(location.search).get('lang') === 'fr';
  const applyLanguage = () => {
    root.lang = french ? 'fr' : 'en';
    nodes.forEach(node => { node.textContent = french ? node.dataset.fr : original.get(node); });
    if (language) {
      language.textContent = french ? 'English' : 'Français';
      language.lang = french ? 'en' : 'fr';
      language.setAttribute('aria-label', french ? 'Read in English' : 'Lire en français');
    }
    document.title = french ? 'Un travail utile. Récupéré. Réutilisé. | Étude AGI Alpha' : 'Useful work. Recovered. Reused. | AGI Alpha study';
  };
  if (language) {
    language.addEventListener('click', () => {
      french = !french;
      applyLanguage();
      try {
        const url = new URL(location.href);
        if (french) url.searchParams.set('lang', 'fr'); else url.searchParams.delete('lang');
        history.replaceState(null, '', url);
      } catch (_) { /* Reading still works when local history changes are unavailable. */ }
    });
    applyLanguage();
  }
  if (size) {
    size.addEventListener('click', () => {
      const enabled = root.classList.toggle('large-text');
      size.setAttribute('aria-pressed', String(enabled));
    });
  }
  document.querySelectorAll('[data-print]').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('details').forEach(detail => { detail.open = true; });
      window.print();
    });
  });
})();
