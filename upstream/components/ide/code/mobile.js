'use strict';
(() => {
  const compact = window.matchMedia('(max-width:760px)');
  const toggle = document.getElementById('mobileFilesToggle');
  const sidebar = document.getElementById('fileSidebar');
  const main = document.querySelector('.main');
  if (!toggle || !sidebar || !main) return;
  if (typeof setIcon === 'function' && typeof SVG !== 'undefined') setIcon('mobileFilesToggle', 'folder', '<span>Files</span>');
  const run = document.getElementById('runBtn');
  if (run) {
    const label = document.createElement('span');
    label.className = 'mobile-run-label';
    label.textContent = 'Run';
    run.append(label);
  }
  const resizeEditor = () => requestAnimationFrame(() => {
    if (typeof editor !== 'undefined' && typeof editor.resize === 'function') editor.resize(true);
  });
  const close = (focus = false) => {
    document.body.classList.remove('mobile-files-open');
    toggle.setAttribute('aria-expanded', 'false');
    main.inert = false;
    sidebar.setAttribute('aria-hidden', compact.matches ? 'true' : 'false');
    if (focus) toggle.focus();
    resizeEditor();
  };
  toggle.addEventListener('click', () => {
    if (document.body.classList.contains('mobile-files-open')) return close();
    document.body.classList.add('mobile-files-open');
    toggle.setAttribute('aria-expanded', 'true');
    sidebar.setAttribute('aria-hidden', 'false');
    main.inert = true;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.body.classList.contains('mobile-files-open')) close(true);
  });
  // Preserve existing file/media handlers; only close the drawer after selection.
  if (typeof openFile === 'function') {
    const original = openFile;
    openFile = async function(...args) {
      const result = await original.apply(this, args);
      if (compact.matches && typeof active === 'function' && active()?.path === args[0]) close();
      return result;
    };
  }
  if (typeof openMedia === 'function') {
    const original = openMedia;
    openMedia = async function(...args) {
      const result = await original.apply(this, args);
      if (compact.matches) close();
      return result;
    };
  }
  compact.addEventListener('change', () => close());
  window.visualViewport?.addEventListener('resize', resizeEditor);
  close();
})();
