"""Builds the App map site from its Markdown sources, next to them in the same folder.

Usage: build.py <map dir>

Sources (the map's source of truth, readable on GitHub as they are):
  index.md        the overview: title, module order, overview diagrams and lists
  <module>.md     one per module
Each file is YAML frontmatter plus `## Title · label` sections. A section's first paragraph is
its caption; a ```mermaid block is its diagram; a list after the diagram is its legend; a list
in a section without a diagram is shown as a list. See reference/markdown.md.

Writes <module>.html and index.html from the templates in assets/, and copies code-popup.js.
"""
import html
import os
import re
import shutil
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, '..', 'assets')


# ---- Markdown subset ------------------------------------------------------------------------

def inline(text):
    """`code`, **bold**, [label](url) and plain text, escaped for HTML."""
    out, pos = [], 0
    pattern = re.compile(r'`([^`]+)`|\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)')
    for match in pattern.finditer(text):
        out.append(html.escape(text[pos:match.start()], quote=False))
        code, bold, label, url = match.groups()
        if code is not None:
            out.append(f'<code>{html.escape(code, quote=False)}</code>')
        elif bold is not None:
            out.append(f'<b>{inline(bold)}</b>')
        else:
            out.append(f'<a href="{html.escape(url)}">{inline(label)}</a>')
        pos = match.end()
    out.append(html.escape(text[pos:], quote=False))
    return ''.join(out)


def read(path):
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    match = re.match(r'---\n([\s\S]*?)\n---\n', text)
    meta = yaml.safe_load(match.group(1)) if match else {}
    body = text[match.end():] if match else text
    return meta or {}, sections(body)


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'section'


def sections(body):
    """[{title, label, caption: [paragraphs], diagram, legend: [items], items: [items]}]"""
    found = []
    for chunk in re.split(r'^## ', body, flags=re.M)[1:]:
        head, _, rest = chunk.partition('\n')
        title, _, label = head.partition(' · ')
        section = {'title': title.strip(), 'label': label.strip(), 'caption': [], 'diagram': None,
                   'legend': [], 'items': [], 'id': None}
        id_match = re.search(r'\s*\{#([\w-]+)\}$', section['label'] or section['title'])
        if id_match:
            section['id'] = id_match.group(1)
            if section['label']:
                section['label'] = section['label'][:id_match.start()].strip()
            else:
                section['title'] = section['title'][:id_match.start()].strip()
        diagram = re.search(r'```mermaid\n([\s\S]*?)```', rest)
        before, after = (rest[:diagram.start()], rest[diagram.end():]) if diagram else (rest, '')
        if diagram:
            section['diagram'] = diagram.group(1)
        for block in re.split(r'\n\s*\n', before.strip()):
            if not block.strip():
                continue
            if block.lstrip().startswith('- '):
                section['items'] += list_items(block)
            else:
                section['caption'].append(' '.join(line.strip() for line in block.splitlines()))
        for block in re.split(r'\n\s*\n', after.strip()):
            if block.lstrip().startswith('- '):
                section['legend' if diagram else 'items'] += list_items(block)
        found.append(section)
    return found


def list_items(block):
    items = []
    for line in block.splitlines():
        if line.startswith('- '):
            items.append(line[2:].strip())
        elif items and line.strip():
            items[-1] += ' ' + line.strip()
    return items


# ---- Pages ----------------------------------------------------------------------------------

def template_parts(name):
    with open(os.path.join(ASSETS, name), encoding='utf-8') as handle:
        text = handle.read()
    head = text[:text.index('<main>')]
    tail = text[text.index('<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid'):]
    return head, tail


def legend_html(items):
    out = []
    for item in items:
        match = re.match(r'`([^`]+)`\s*(.*)', item)
        out.append(f'      <li><b>{html.escape(match.group(1), quote=False)}</b> {inline(match.group(2))}</li>'
                   if match else f'      <li>{inline(item)}</li>')
    return '    <ul class="legend">\n' + '\n'.join(out) + '\n    </ul>\n'


def section_html(section, source_id, list_class, links=None):
    section_id = 'h-' + (section['id'] or slug(section['title']))
    label = f' <span>{inline(section["label"])}</span>' if section['label'] else ''
    out = [f'  <section aria-labelledby="{section_id}">',
           f'    <h2 id="{section_id}">{inline(section["title"])}{label}</h2>']
    for paragraph in section['caption']:
        out.append(f'    <p class="cap">{inline(paragraph)}</p>')
    if section['items']:
        out.append(f'    <ul class="{list_class}">')
        out += [f'      <li>{inline(item)}</li>' for item in section['items']]
        out.append('    </ul>')
    text = '\n'.join(out) + '\n'
    if section['diagram'] is not None:
        attrs = f' data-links=\'{links}\'' if links else ''
        text += f'    <div class="diagram"><div class="out" data-src="{source_id}"{attrs}></div></div>\n'
        if section['legend']:
            text += legend_html(section['legend'])
    return text + '  </section>\n'


def sources_html(diagrams):
    out = []
    for source_id, source in diagrams:
        safe = source.replace('</script', '<\\/script')
        out.append(f'<script type="text/plain" id="{source_id}">\n{safe}</script>\n')
    return '\n'.join(out)


def shots_html(module, shots):
    if not shots:
        return ''
    items = []
    for shot in shots:
        path, caption = (shot[0], shot[1]) if isinstance(shot, list) else (shot['file'], shot.get('caption', ''))
        items.append(f'      <li><figure><a href="{html.escape(path)}"><img src="{html.escape(path)}" '
                     f'alt="{html.escape(caption)}" loading="lazy"></a><figcaption>{inline(caption)}'
                     f'</figcaption></figure></li>')
    return ('  <section aria-labelledby="h-shots">\n'
            '    <h2 id="h-shots">Screenshots <span>scroll sideways · tap to enlarge</span></h2>\n'
            '    <ul class="shots">\n' + '\n'.join(items) + '\n    </ul>\n  </section>\n')


def build_module(map_dir, name):
    meta, parts = read(os.path.join(map_dir, name + '.md'))
    head, tail = template_parts('module.html')
    title = meta.get('title', name)
    head = re.sub(r'<title>.*?</title>', f'<title>{html.escape(title)}</title>', head)
    tail = tail.replace('code/{{module}}.js', f'code/{name}.js')
    main = ['<main>\n  <header>\n',
            f'    <h1>{html.escape(title)}</h1>\n',
            f'    <p class="sub"><a href="index.html">← App map</a> · {inline(meta.get("sub", ""))}</p>\n',
            '  </header>\n', shots_html(name, meta.get('screenshots'))]
    diagrams, used = [], set()
    for section in parts:
        source_id = 'src-' + (section['id'] or slug(section['title']))
        while source_id in used:
            source_id += '-2'
        used.add(source_id)
        main.append(section_html(section, source_id, 'updates'))
        if section['diagram'] is not None:
            diagrams.append((source_id, section['diagram']))
    main.append('</main>\n\n')
    write(os.path.join(map_dir, name + '.html'), head + ''.join(main) + sources_html(diagrams) + '\n' + tail)
    return meta


def build_index(map_dir, modules):
    meta, parts = read(os.path.join(map_dir, 'index.md'))
    head, tail = template_parts('index.html')
    title = meta.get('title', 'App Map')
    head = re.sub(r'<title>.*?</title>', f'<title>{html.escape(title)}</title>', head)
    cards = []
    for name, module_meta in modules:
        shots = module_meta.get('screenshots') or []
        first = shots[0] if shots else None
        image = module_meta.get('card_image') or \
            ((first[0] if isinstance(first, list) else first['file']) if first else None)
        picture = f'<img src="{html.escape(image)}" alt="" loading="lazy">' if image else ''
        cards.append(f'      <li><a href="{name}.html">{picture}<b>{inline(module_meta.get("card_title", name))}</b>'
                     f'<span>{inline(module_meta.get("card", ""))}</span></a></li>')
    main = ['<main>\n  <header>\n', f'    <h1>{html.escape(title)}</h1>\n',
            f'    <p class="sub">{inline(meta.get("sub", ""))}</p>\n', '  </header>\n',
            '  <section aria-labelledby="h-modules">\n',
            f'    <h2 id="h-modules">Modules <span>{len(modules)}</span></h2>\n',
            '    <ul class="modules">\n' + '\n'.join(cards) + '\n    </ul>\n  </section>\n']
    main.append(FIND_SECTION)
    links = meta.get('links') or {}
    diagrams = []
    for section in parts:
        key = section['id'] or slug(section['title'])
        source_id = 'src-' + key
        section_links = links.get(key)
        rendered = None
        if section_links:
            rendered = '{' + ', '.join(f'"{node}": "{target}.html"' if not str(target).endswith('.html')
                                       else f'"{node}": "{target}"'
                                       for node, target in section_links.items()) + '}'
        main.append(section_html(section, source_id, 'maps', rendered))
        if section['diagram'] is not None:
            diagrams.append((source_id, section['diagram']))
    main.append('</main>\n')
    write(os.path.join(map_dir, 'index.html'),
          head + ''.join(main) + sources_html(diagrams) + tail + FIND_SCRIPT)


# Code → map: type a class (or file) and see every diagram that draws it.
FIND_SECTION = """  <section aria-labelledby="h-find" class="find" hidden>
    <h2 id="h-find">Find in the map <span>a class or a file</span></h2>
    <style>
      .find input { font: inherit; width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px;
        border: 1px solid var(--line); background: var(--bg); color: var(--ink); }
      .find input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
      .find ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 6px; }
      .find li { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline; }
      .find li code { font-family: var(--font-mono); color: var(--ink); }
      .find li a { color: var(--accent); font-size: 14px; }
      .find .file { color: var(--muted); font-size: 12px; font-family: var(--font-mono); }
    </style>
    <input type="search" placeholder="A class or file name" aria-label="Find a class or file in the map" autocomplete="off">
    <ul></ul>
  </section>
"""

FIND_SCRIPT = """<script src="code/index.js"></script>
<script src="code-popup.js"></script>
<script src="code/_where.js"></script>
<script>
  (function () {
    const data = window.APP_MAP_WHERE;
    const section = document.querySelector('section.find');
    if (!data || !section) return;
    section.hidden = false;
    const input = section.querySelector('input');
    const list = section.querySelector('ul');
    const escape = (text) => String(text).replace(/[&<>"]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
    // The example is this map's most-drawn class, so it names something in this app.
    const [example] = Object.keys(data.classes).filter((name) => data.files[name])
      .sort((a, b) => data.classes[b].length - data.classes[a].length || a.localeCompare(b));
    if (example) input.placeholder = 'e.g. ' + example + ' or ' + data.files[example].split('/').pop();
    const title = (page) => page.replace(/-/g, ' ').replace(/^./, (c) => c.toUpperCase());
    input.addEventListener('input', () => {
      const query = input.value.trim().toLowerCase();
      if (query.length < 2) { list.innerHTML = ''; return; }
      const hits = Object.keys(data.classes).filter((name) =>
        name.toLowerCase().includes(query) || (data.files[name] || '').toLowerCase().includes(query)).sort().slice(0, 30);
      list.innerHTML = hits.length ? hits.map((name) => '<li><code>' + escape(name) + '</code>'
        + data.classes[name].map(([page, id, heading]) => '<a href="' + escape(page) + '.html#' + escape(id) + '">'
          + escape(title(page) + ' · ' + heading) + '</a>').join('')
        + '<span class="file">' + escape(data.files[name] || '') + '</span></li>').join('')
        : '<li>Not drawn on the map.</li>';
    });
  })();
</script>
"""


def write(path, text):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as handle:
            if handle.read() == text:
                return
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def main():
    map_dir = sys.argv[1]
    index_meta, _ = read(os.path.join(map_dir, 'index.md'))
    order = index_meta.get('modules') or sorted(
        name[:-3] for name in os.listdir(map_dir) if name.endswith('.md') and name != 'index.md')
    modules = [(name, build_module(map_dir, name)) for name in order]
    build_index(map_dir, modules)
    shutil.copy(os.path.join(ASSETS, 'code-popup.js'), os.path.join(map_dir, 'code-popup.js'))
    print(f'build: {len(modules)} module pages + index in {map_dir}')


if __name__ == '__main__':
    main()
