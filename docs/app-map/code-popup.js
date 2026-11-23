// Click-to-see-code for App map pages. Needs code/<page>.js (window.CODE_INDEX), built by
// scripts/index_code.py. Without it the page still renders, just without popups.
(function () {
  const index = window.CODE_INDEX && window.CODE_INDEX.classes;
  if (!index) return;

  const style = document.createElement('style');
  style.textContent = `
    :root { --kw: #8a2b8f; --str: #2f7a32; --com: #7b7790; --num: #a1521b; --typ: #1f5fa8; }
    @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
      --kw: #e29be6; --str: #9ad48f; --com: #8d88a6; --num: #f0b27a; --typ: #8fbff5; } }
    :root[data-theme="dark"] { --kw: #e29be6; --str: #9ad48f; --com: #8d88a6; --num: #f0b27a; --typ: #8fbff5; }
    .code-link { cursor: pointer; }
    .code-link:hover, .code-link:focus-visible { text-decoration: underline; text-decoration-color: var(--accent); outline: none; }
    g.code-link:hover text, g.code-link:hover tspan { text-decoration: underline; }
    dialog.code-pop { width: min(920px, calc(100vw - 32px)); max-height: calc(100vh - 48px); padding: 0;
      border: 1px solid var(--line); border-radius: 14px; background: var(--surface); color: var(--ink); }
    dialog.code-pop::backdrop { background: rgb(10 8 20 / 0.45); }
    .code-pop header { position: sticky; top: 0; display: flex; gap: 12px; align-items: center;
      padding: 12px 16px; background: var(--surface); border-bottom: 1px solid var(--line); }
    .code-pop header h3 { margin: 0; font-family: var(--font-mono); font-size: 15px; font-weight: 500; flex: 1; min-width: 0; overflow-wrap: anywhere; }
    .code-pop header button { flex: none; width: 32px; height: 32px; display: grid; place-items: center;
      font: 16px/1 var(--font-body); background: none; border: 0; border-radius: 8px; color: var(--muted); cursor: pointer; }
    .code-pop header button:hover, .code-pop header button:focus-visible { background: var(--accent-soft); color: var(--ink); }
    .code-pop .part { padding: 12px 16px 16px; display: grid; gap: 8px; }
    .code-pop .part + .part { border-top: 1px solid var(--line); }
    .code-pop .where { font-family: var(--font-mono); font-size: 12px; color: var(--muted); margin: 0; overflow-wrap: anywhere; }
    .code-pop .where a { color: var(--accent); }
    .code-pop .appears { margin: 0; padding: 10px 16px 0; font-size: 13px; color: var(--muted); }
    .code-pop .appears a { color: var(--accent); }
    .code-pop .shot { margin: 0; padding: 16px 16px 0; display: flex; justify-content: center; }
    .code-pop .shot img { display: block; max-width: 100%; max-height: 60vh; object-fit: contain;
      border: 1px solid var(--line); border-radius: 10px; background: var(--bg); }
    .code-pop pre { margin: 0; padding: 12px; background: var(--bg); border: 1px solid var(--line); border-radius: 10px;
      overflow: auto; font-family: var(--font-mono); font-size: 12.5px; line-height: 1.55; tab-size: 2; }
    .code-pop .ln { display: inline-block; width: 3.5ch; margin-right: 1.5ch; text-align: right; color: var(--com); user-select: none; }
    .code-pop .hljs-keyword, .code-pop .hljs-built_in, .code-pop .hljs-literal { color: var(--kw); }
    .code-pop .hljs-string { color: var(--str); }
    .code-pop .hljs-comment { color: var(--com); font-style: italic; }
    .code-pop .hljs-number { color: var(--num); }
    .code-pop .hljs-title, .code-pop .hljs-type { color: var(--typ); }
    .code-pop .hljs-meta { color: var(--num); }
  `;
  document.head.appendChild(style);

  // ---- Lookup -------------------------------------------------------------------------

  /**
   * Where `name` is declared, searching the class, then its parents and mixins: the declaring
   * class's entry and the member key (a named constructor `main` is keyed `Class.main`).
   */
  function lookup(className, name) {
    const queue = [className];
    const seen = new Set();
    while (queue.length) {
      const current = queue.shift();
      const entry = index[current];
      if (!entry || seen.has(entry)) continue;
      seen.add(entry);
      if (entry.members[name]) return { owner: entry, key: name };
      if (entry.members[current + '.' + name]) return { owner: entry, key: current + '.' + name };
      queue.push(...(entry.supers || []));
    }
    return null;
  }

  /** Members of `className` named on a diagram line like `toggleLike(card)` or `read · ask`. */
  function membersIn(className, text) {
    const found = [];
    for (const word of text.match(/[A-Za-z_]\w*/g) || []) {
      if (word === className) continue;
      const hit = lookup(className, word);
      if (hit && !found.some((part) => part.name === hit.key)) found.push({ owner: hit.owner, name: hit.key });
    }
    return found;
  }

  // ---- Popup --------------------------------------------------------------------------

  const dialog = document.createElement('dialog');
  dialog.className = 'code-pop';
  dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
  document.body.appendChild(dialog);

  // Editor links work when the page is opened from disk, next to the repo it maps.
  const repoRoot = location.protocol === 'file:' && typeof window.CODE_INDEX.root === 'string'
    ? decodeURIComponent(new URL(window.CODE_INDEX.root + '/', location.href).pathname).replace(/\/$/, '')
    : null;

  let highlighter = null;
  function loadHighlighter() {
    if (highlighter) return highlighter;
    const load = (src) => new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src; script.onload = resolve; script.onerror = reject;
      document.head.appendChild(script);
    });
    const base = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/';
    highlighter = load(base + 'highlight.min.js').then(() => load(base + 'languages/dart.min.js'))
      .then(() => window.hljs).catch(() => null);
    return highlighter;
  }

  function escape(text) {
    return text.replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
  }

  /** Lines `from..to` (1-based, in the file) of a class's code. */
  function slice(entry, from, to) {
    return entry.code.split('\n').slice(from - entry.line, to - entry.line + 1).join('\n');
  }

  function partHtml(title, entry, from, to, hljs) {
    const code = slice(entry, from, to);
    const body = hljs ? hljs.highlight(code, { language: 'dart' }).value : escape(code);
    // Highlighted spans may cross lines; close and reopen them around each line number.
    const lines = [];
    let open = [];
    for (const [offset, line] of body.split('\n').entries()) {
      const full = open.join('') + line;
      open = [];
      for (const tag of full.match(/<span[^>]*>|<\/span>/g) || []) {
        if (tag === '</span>') open.pop(); else open.push(tag);
      }
      lines.push('<span class="ln">' + (from + offset) + '</span>' + full + '</span>'.repeat(open.length));
    }
    const where = entry.file + ':' + from;
    // A published map links to the lines on the web; a local one opens them in the editor.
    const sourceUrl = window.CODE_INDEX.sourceUrl;
    const link = sourceUrl
      ? '<a href="' + escape(sourceUrl + entry.file + '#L' + from + '-L' + to) + '" target="_blank" rel="noopener">'
        + escape(where) + ' ↗</a>'
      : repoRoot
        ? '<a href="vscode://file' + escape(repoRoot + '/' + entry.file) + ':' + from + '">' + escape(where) + '</a>'
        : escape(where);
    const also = entry.alsoIn ? ' · also declared in ' + entry.alsoIn.map(escape).join(', ') : '';
    return '<div class="part"><p class="where">' + escape(title) + ' — ' + link + also + '</p><pre><code>'
      + lines.join('\n') + '</code></pre></div>';
  }

  /** The page's or widget's crop from the real app; crops are saved at 2x. */
  function shotHtml(entry, name) {
    if (!entry.shot) return '';
    return '<figure class="shot"><img src="' + escape(entry.shot) + '" alt="' + escape(name)
      + ' in the app" onload="this.style.width = this.naturalWidth / 2 + \'px\'"></figure>';
  }

  /** "Appears in: Home · Logic, Meds · Sequence" — every diagram on the map that draws it. */
  function appearsHtml(className) {
    const entry = className && index[className];
    const spots = (entry && entry.appearsIn) || [];
    if (spots.length < 2) return '';
    const here = location.pathname.split('/').pop().replace(/\.html$/, '');
    const links = spots.map(([page, sectionId, title]) => {
      const pageName = page === 'index' ? 'Overview'
        : page.replace(/-/g, ' ').replace(/^./, (char) => char.toUpperCase());
      const label = escape(pageName + ': ' + title.split(' · ')[0]);
      return page === here && document.getElementById(sectionId)
        ? '<a href="#' + escape(sectionId) + '" data-close>' + label + '</a>'
        : '<a href="' + escape(page) + '.html#' + escape(sectionId) + '">' + label + '</a>';
    });
    return '<p class="appears">Appears in ' + links.join(', ') + '</p>';
  }

  async function show(heading, parts, shot, className) {
    const hljs = await loadHighlighter();
    dialog.innerHTML = '<header><h3></h3><button type="button" aria-label="Close">✕</button></header>'
      + appearsHtml(className) + (shot || '') + parts.map((part) => partHtml(part.title, part.entry, part.from, part.to, hljs)).join('');
    dialog.querySelector('h3').textContent = heading;
    dialog.querySelector('button').addEventListener('click', () => dialog.close());
    dialog.querySelectorAll('[data-close]').forEach((link) => link.addEventListener('click', () => dialog.close()));
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
  }

  function showClass(className) {
    const entry = index[className];
    const lineCount = entry.code.split('\n').length;
    show(entry.kind + ' ' + className, [{ title: className, entry, from: entry.line, to: entry.line + lineCount - 1 }],
      shotHtml(entry, className), className);
  }

  function showMembers(className, found) {
    showParts(className + ' · ' + found.map((part) => part.name).join(', '),
      found.map((part) => ({ ...part, className })));
  }

  /** Each part: the member `name`, the `owner` entry declaring it, the `className` it was asked on. */
  function showParts(heading, found) {
    show(heading, found.map((part) => ({
      title: (part.name.includes('.') ? part.name : ownerName(part.owner) + '.' + part.name)
        + (part.owner === index[part.className] ? ''
          : /State$/.test(ownerName(part.owner)) && ownerName(part.owner).includes(part.className)
            ? ' (in its State class)'
            : ' (inherited by ' + part.className + ')'),
      entry: part.owner, from: part.owner.members[part.name][0], to: part.owner.members[part.name][1],
    })), '', found.length === 1 ? found[0].className : null);
  }

  function ownerName(entry) { return Object.keys(index).find((name) => index[name] === entry); }

  function makeLink(element, label, open) {
    element.classList.add('code-link');
    element.setAttribute('tabindex', '0');
    element.setAttribute('role', 'button');
    element.setAttribute('aria-label', 'Show code: ' + label);
    element.addEventListener('click', (event) => { event.stopPropagation(); open(); });
    element.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); }
    });
  }

  // ---- Wiring the rendered SVGs ----------------------------------------------------------

  /** Innermost elements holding one visible line of text. */
  function textLines(root) {
    const all = Array.from(root.querySelectorAll('text, span, p, div'));
    return all.filter((element) => element.textContent.trim()
      && !Array.from(element.children).some((child) => child.textContent.trim() && child.matches('text, span, p, div')));
  }

  /** Relation labels (`A ..> B : reschedule() after an answer`) → the classes at both ends. */
  function relationsByLabel(source) {
    const byLabel = {};
    const relation = /^[ \t]*([A-Za-z_]\w*)[ \t]+(?:"[^"\n]*"[ \t]+)?\S*(?:--|\.\.)\S*[ \t]+(?:"[^"\n]*"[ \t]+)?([A-Za-z_]\w*)[ \t]*:[ \t]*(.+?)[ \t]*$/gm;
    for (const match of source.matchAll(relation)) {
      (byLabel[match[3]] = byLabel[match[3]] || []).push([match[1], match[2]]);
    }
    return byLabel;
  }

  /** Flowchart node ids → the class each label names (`"Menu<br/>MenuPage"` → MenuPage). */
  const flowTitles = {};
  function flowNodes(source) {
    const nodes = {};
    for (const match of source.matchAll(/(\w+)\s*(?:\["?|\("?|\{"?)([^"\]\)\}]*)/g)) {
      // The label's first line names the node in popup headings ("Splash", not `SplashS`).
      if (!flowTitles[match[1]]) flowTitles[match[1]] = match[2].split(/<br\s*\/?>/)[0].trim() || match[1];
      if (nodes[match[1]]) continue;
      const words = match[2].split(/<br\s*\/?>|[\s·,]+/).filter((word) => index[word]);
      if (words.length) nodes[match[1]] = words[words.length - 1];
      else if (index[match[1]]) nodes[match[1]] = match[1];
    }
    return nodes;
  }

  /** Flowchart arrow labels (`A -->|load| B`) → the classes at both ends. */
  function flowLabels(source, nodes) {
    const byLabel = {};
    const edge = /(\w+)(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\})?[ \t]*(?:-{2,}>|-\.+->|={2,}>|-{3,})[ \t]*\|([^|]+)\|[ \t]*(\w+)/g;
    for (const match of source.matchAll(edge)) {
      const label = match[2].trim();
      (byLabel[label] = byLabel[label] || []).push([nodes[match[1]] || match[1], nodes[match[3]] || match[3],
        flowTitles[match[1]] || match[1], flowTitles[match[3]] || match[3]]);
    }
    return byLabel;
  }

  function wireFlowchart(svg, source) {
    const nodes = flowNodes(source);
    // A box linked to a module page keeps opening that page; any other box naming a class opens it.
    for (const node of svg.querySelectorAll('g.node')) {
      const idMatch = /^flowchart-(.+)-\d+$/.exec(node.id || '');
      const className = idMatch && nodes[idMatch[1]];
      if (!className || node.classList.contains('link')) continue;
      makeLink(node, className, () => showClass(className));
    }
    wireEdgeLabels(svg, flowLabels(source, nodes));
  }

  function wireEdgeLabels(svg, byLabel) {
    for (const edge of svg.querySelectorAll('g.edgeLabel')) {
      for (const line of textLines(edge)) {
        const text = line.textContent.trim();
        const found = [];
        // A label names a method on either end: `..> Service : load()` or `--> VM : viewModel`.
        for (const [from, to] of byLabel[text] || []) {
          for (const className of [to, from]) {
            for (const part of membersIn(className, text)) {
              if (!found.some((other) => other.owner === part.owner && other.name === part.name)) {
                found.push({ ...part, className });
              }
            }
          }
        }
        if (!found.length) continue;
        const ends = (byLabel[text] || []).map(([from, to, fromTitle, toTitle]) =>
          (fromTitle || from) + ' → ' + (toTitle || to)).join(', ');
        makeLink(line, text, () => showParts(ends + ' · ' + text, found));
      }
    }
  }

  function wireClassDiagram(svg) {
    for (const node of svg.querySelectorAll('g.node')) {
      const idMatch = /classId-(.+)-\d+$/.exec(node.id || '');
      const className = idMatch && idMatch[1];
      if (!className || !index[className]) continue;
      for (const line of textLines(node)) {
        const text = line.textContent.trim();
        if (text === className) {
          makeLink(line, className, () => showClass(className));
        } else if (!/^[«<]/.test(text)) {
          const found = membersIn(className, text);
          if (found.length) makeLink(line, text, () => showMembers(className, found));
        }
      }
    }
  }

  function wireSequence(svg, source) {
    const alias = {};
    for (const match of source.matchAll(/^[ \t]*(?:participant|actor)[ \t]+(\w+)(?:[ \t]+as[ \t]+(\w+))?/gm)) {
      alias[match[1]] = match[2] || match[1];
    }
    const messages = Array.from(source.matchAll(/^[ \t]*(\w+)[ \t]*(-{1,2}[>x)]{1,2})[+-]?[ \t]*(\w+)[ \t]*:[ \t]*(.*)$/gm))
      .map((match) => ({ from: alias[match[1]] || match[1], to: alias[match[3]] || match[3], reply: match[2].startsWith('--') }));
    for (const actor of svg.querySelectorAll('text.actor')) {
      const name = actor.textContent.trim();
      if (index[name]) makeLink(actor, name, () => showClass(name));
    }
    Array.from(svg.querySelectorAll('text.messageText')).forEach((label, position) => {
      const message = messages[position];
      // Replies describe a result in words, so only calls link to the receiver's method.
      if (!message || message.reply) return;
      const found = index[message.to] ? membersIn(message.to, label.textContent) : [];
      if (found.length) makeLink(label, label.textContent.trim(), () => showMembers(message.to, found));
    });
  }

  function wire(out) {
    const svg = out.querySelector('svg');
    if (!svg || svg.dataset.codeWired) return;
    svg.dataset.codeWired = '1';
    const source = document.getElementById(out.dataset.src).textContent;
    if (/^\s*classDiagram/.test(source)) {
      wireClassDiagram(svg);
      wireEdgeLabels(svg, relationsByLabel(source));
    }
    if (/^\s*(flowchart|graph)\b/.test(source)) wireFlowchart(svg, source);
    if (/^\s*sequenceDiagram/.test(source)) wireSequence(svg, source);
  }

  // Diagrams render after load and again on theme change; wire each new SVG.
  for (const out of document.querySelectorAll('.diagram .out')) {
    wire(out);
    new MutationObserver(() => wire(out)).observe(out, { childList: true });
  }
})();
