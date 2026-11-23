"""Converts an App map written as HTML pages (the pre-Markdown format) into Markdown sources.

Usage: html_to_md.py <map dir>     writes index.md and <module>.md next to the .html pages
"""
import html
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import slug  # noqa: E402


def to_md(fragment):
    """Inline HTML (code, a, b) back to Markdown."""
    text = re.sub(r'<code>(.*?)</code>', lambda m: '`' + html.unescape(m.group(1)) + '`', fragment, flags=re.S)
    text = re.sub(r'<a href="([^"]*)"[^>]*>(.*?)</a>', lambda m: f'[{m.group(2)}]({html.unescape(m.group(1))})',
                  text, flags=re.S)
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.S)
    text = re.sub(r'<[^>]+>', '', text)
    return ' '.join(html.unescape(text).split())


def sources(page):
    return dict(re.findall(r'<script type="text/plain" id="([^"]+)">\n?([\s\S]*?)</script>', page))


def section_md(block, diagrams):
    heading = re.search(r'<h2 id="([^"]+)">(.*?)</h2>', block, re.S)
    section_id, inner = heading.groups()
    label_match = re.search(r'<span>(.*?)</span>', inner, re.S)
    title = to_md(re.sub(r'<span>.*?</span>', '', inner, flags=re.S))
    label = to_md(label_match.group(1)) if label_match else ''
    head = title + (f' · {label}' if label else '')
    if slug(title) != section_id[2:]:
        head += f' {{#{section_id[2:]}}}'
    out = [f'## {head}', '']
    for caption in re.findall(r'<p class="cap">(.*?)</p>', block, re.S):
        out += [to_md(caption), '']
    for list_html in re.findall(r'<ul class="(?:updates|maps(?: none)?)">([\s\S]*?)</ul>', block):
        out += [f'- {to_md(item)}' for item in re.findall(r'<li>(.*?)</li>', list_html, re.S)] + ['']
    out_div = re.search(r'<div class="out" data-src="([^"]+)"', block)
    if out_div:
        out += ['```mermaid', diagrams[out_div.group(1)].rstrip('\n'), '```', '']
        legend = re.search(r'<ul class="legend">([\s\S]*?)</ul>', block)
        if legend:
            for item in re.findall(r'<li>(.*?)</li>', legend.group(1), re.S):
                symbol = re.match(r'\s*<b>(.*?)</b>\s*(.*)', item, re.S)
                out.append(f'- `{html.unescape(symbol.group(1))}` {to_md(symbol.group(2))}' if symbol
                           else f'- {to_md(item)}')
            out.append('')
    return '\n'.join(out)


def frontmatter(meta):
    return '---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000) + '---\n\n'


def convert_module(map_dir, name, card, card_image=''):
    with open(os.path.join(map_dir, name + '.html'), encoding='utf-8') as handle:
        page = handle.read()
    main = page[page.index('<main>'):page.index('</main>')]
    sub = re.search(r'<p class="sub">(.*?)</p>', main, re.S).group(1)
    sub = re.sub(r'^\s*<a href="index.html">[^<]*</a>\s*·\s*', '', sub)
    meta = {'title': to_md(re.search(r'<h1>(.*?)</h1>', main, re.S).group(1)), 'sub': to_md(sub)}
    meta.update(card)
    shots = []
    for src, caption in re.findall(r'<img src="([^"]+)" alt="[^"]*"[^>]*></a><figcaption>(.*?)</figcaption>', main, re.S):
        shots.append({'file': src, 'caption': to_md(caption)})
    if shots:
        meta['screenshots'] = shots
    # The overview card shows the first screenshot unless it names another.
    if card_image and (not shots or shots[0]['file'] != card_image):
        meta['card_image'] = card_image
    diagrams = sources(page)
    body = []
    for block in re.findall(r'<section[^>]*>([\s\S]*?)</section>', main):
        if 'id="h-shots"' in block:
            continue
        body.append(section_md(block, diagrams))
    with open(os.path.join(map_dir, name + '.md'), 'w', encoding='utf-8') as handle:
        handle.write(frontmatter(meta) + '\n'.join(body).rstrip() + '\n')


def main():
    map_dir = sys.argv[1]
    with open(os.path.join(map_dir, 'index.html'), encoding='utf-8') as handle:
        page = handle.read()
    main_html = page[page.index('<main>'):page.index('</main>')]
    cards = re.findall(r'<li><a href="([\w-]+)\.html">(?:<img src="([^"]*)"[^>]*>)?<b>(.*?)</b><span>(.*?)</span></a></li>', main_html)
    meta = {'title': to_md(re.search(r'<h1>(.*?)</h1>', main_html, re.S).group(1)),
            'sub': to_md(re.search(r'<p class="sub">(.*?)</p>', main_html, re.S).group(1)),
            'modules': [name for name, _, _, _ in cards]}
    diagrams = sources(page)
    links, body = {}, []
    for block in re.findall(r'<section[^>]*>([\s\S]*?)</section>', main_html):
        if 'id="h-modules"' in block:
            continue
        body.append(section_md(block, diagrams))
        data = re.search(r"data-links='([^']*)'", block)
        if data:
            key = re.search(r'<h2 id="h-([^"]+)"', block).group(1)
            links[key] = {node: target[:-5] if target.endswith('.html') else target
                          for node, target in json.loads(data.group(1)).items()}
    if links:
        meta['links'] = links
    with open(os.path.join(map_dir, 'index.md'), 'w', encoding='utf-8') as handle:
        handle.write(frontmatter(meta) + '\n'.join(body).rstrip() + '\n')
    for name, image, card_title, card in cards:
        convert_module(map_dir, name, {'card_title': to_md(card_title), 'card': to_md(card)}, image)
    print(f'html_to_md: index.md + {len(cards)} module sources in {map_dir}')


if __name__ == '__main__':
    main()
