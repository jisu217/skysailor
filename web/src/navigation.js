(() => {
  if (new URLSearchParams(location.search).has('embed')) return;
  const routes = [
    ['/', '실험실', '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'],
    ['/arena/', 'Arena', '<path d="M8 3h8v6a4 4 0 0 1-8 0V3ZM8 5H4v2a4 4 0 0 0 4 4m8-6h4v2a4 4 0 0 1-4 4M12 13v5m-4 3h8m-7-3h6v3H9z"/>'],
    ['/game/', 'Game', '<path d="M7 7h10a4 4 0 0 1 4 4l1 6a3 3 0 0 1-5 2l-2-2H9l-2 2a3 3 0 0 1-5-2l1-6a4 4 0 0 1 4-4Z M7 10v4m-2-2h4m7-1h.01m3 3h.01"/>'],
    ['/manual/', '수동 조종', '<path d="M12 14V5m-3-2h6v4H9zM7 14H5l-2 7h18l-2-7h-2M8 18h8"/>'],
    ['/platform/', '기체', '<path d="m12 3 9 5v8l-9 5-9-5V8l9-5ZM3 8l9 5 9-5m-9 5v8M7.5 5.5l9 5"/>'],
    ['/training/', '학습', '<path d="M3 3v18h18M7 14l4-5 4 3 5-7"/>'],
    ['/participate/', '참가 가이드', '<path d="M12 6c-3-3-7-3-10-2v15c3-1 7-1 10 2 3-3 7-3 10-2V4c-3-1-7-1-10 2Zm0 0v15"/>'],
  ];
  const section = '/' + location.pathname.split('/').filter(Boolean)[0] + '/';
  const current = location.pathname === '/' ? '/' : section;
  document.body.dataset.navPage = current === '/' ? 'home' : current.split('/')[1];
  document.body.classList.add('with-site-nav');
  const style = document.createElement('style');
  style.textContent = `
    body.with-site-nav{padding-top:56px;box-sizing:border-box}
    #site-nav{position:fixed;inset:0 0 auto;height:56px;z-index:1000;box-sizing:border-box;display:flex;align-items:center;gap:5px;margin:0;padding:6px 16px;background:#101e27f5;border-bottom:1px solid #314650;backdrop-filter:blur(14px);overflow-x:auto;white-space:nowrap;font:12px system-ui,sans-serif;color:#a9bdc6}
    #site-nav a{display:flex;flex:none;align-items:center;justify-content:center;gap:7px;padding:9px 11px;border:1px solid transparent;border-radius:8px;color:#a9bdc6;text-decoration:none;font:inherit;line-height:20px}
    #site-nav a:hover{background:#223942;color:#e7f6ef}
    #site-nav a[aria-current=page]{background:#213e3c;border-color:#47796b;color:#9ce8cc}
    #site-nav a:focus-visible{outline:2px solid #9ce8cc;outline-offset:-2px}
    #site-nav svg{width:19px;height:19px;flex:none}
    body[data-nav-page=game] #view{top:56px}
    body[data-nav-page=game]>header{top:56px}
    body[data-nav-page=game]>aside{top:56px}
    body[data-nav-page=platform]>aside{top:76px;max-height:calc(100dvh - 112px);box-sizing:border-box}
    body[data-nav-page=platform]{padding-top:0}
    body[data-nav-page=home]>.app{height:calc(100dvh - 56px)}
    @media(max-width:700px){#site-nav{padding:6px 8px;gap:3px}#site-nav a{padding:9px 10px}#site-nav a span{display:none}#site-nav a[aria-current=page] span{display:inline}}
  `;
  document.head.append(style);
  const nav = document.createElement('nav');
  nav.id = 'site-nav';
  nav.setAttribute('aria-label', '화면 전환');
  for (const [url, label, icon] of routes) {
    const a = document.createElement('a');
    a.href = url;
    a.title = label;
    a.setAttribute('aria-label', label);
    if (current === url) a.setAttribute('aria-current', 'page');
    a.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icon}</svg><span>${label}</span>`;
    nav.append(a);
  }
  document.body.prepend(nav);
})();
