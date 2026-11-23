#!/usr/bin/env python3
"""公開用の資料（handout）を PDF に組む。

    python scripts/build_handout.py <名前> [--date YYYY-MM-DD] [--out DIR] [--chrome PATH] [--keep-html]

docs/handouts/<名前>.json（構成ファイル）を読み、.temp/handouts/<名前>_<日付>.pdf を作る。
構成ファイルの書き方と、書き下ろしの章で正本を取り込む `<!-- include: ... -->` は docs/handouts/README.md。

要るもの: pandoc、Chrome か Edge（ヘッドレスの PDF 書き出し）。Python は標準ライブラリのみ。
PDF はコミットしない（DR が済んだ版だけ、ユーザーの指示で GitHub Releases に添付する）。
"""
from __future__ import annotations

import argparse
import datetime
import html
from html.parser import HTMLParser
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
# 公開リポジトリの資料に載せないもの（AGENTS.md「公開範囲」）
FORBIDDEN = ('.private/', 'collection/getstarting/', '.temp/')
INCLUDE_RE = re.compile(r'^<!--\s*include:\s*(.*?)\s*-->[ \t]*$', re.M)
IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)\)')
IMAGE_REFERENCE_RE = re.compile(r'!\[([^\]]*)\](?:\[([^\]]*)\])?(?!\()')
REFERENCE_DEF_RE = re.compile(r'^ {0,3}\[([^\]]+)\]:[ \t]*(?:<([^>\n]+)>|(\S+))', re.M)
UNINSPECTABLE_HTML_IMAGE_RE = re.compile(
    r'<\s*(?:img|picture|source|iframe|object|embed|svg|video|audio|style|link|input)\b'
    r'|\s(?:style|srcset|background)\s*=',
    re.I,
)


class HandoutError(Exception):
    pass


def repo_path(rel: str) -> Path:
    """リポジトリ内の相対パスを解決し、公開してよい場所かを確かめる。"""
    p = (ROOT / rel).resolve()
    try:
        r = p.relative_to(ROOT).as_posix()
    except ValueError:
        raise HandoutError(f'リポジトリの外のパス: {rel}')
    if any(r.startswith(f) for f in FORBIDDEN):
        raise HandoutError(f'公開資料に載せないパス: {rel}')
    if not p.is_file():
        raise HandoutError(f'ファイルが無い: {rel}')
    return p


def read_text(p: Path) -> str:
    return p.read_text(encoding='utf-8').replace('\r\n', '\n')


# ---------- include ----------

def heading_level(line: str) -> int:
    m = re.match(r'(#{1,6})\s', line)
    return len(m.group(1)) if m else 0


def section_lines(lines: list[str], heading: str | None) -> list[str]:
    if heading is None:
        return lines
    for i, line in enumerate(lines):
        if heading_level(line) and line.startswith(heading):
            lv = heading_level(line)
            j = i + 1
            while j < len(lines) and not (heading_level(lines[j]) and heading_level(lines[j]) <= lv):
                j += 1
            return lines[i + 1:j]
    raise HandoutError(f'見出しが無い: {heading}')


def tables(lines: list[str]) -> list[list[str]]:
    out, cur = [], []
    for line in lines + ['']:
        if line.startswith('|'):
            cur.append(line)
        elif cur:
            out.append(cur)
            cur = []
    return out


def cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip('|').split('|')]


def expand_include(spec: str, image_uris: set[str]) -> str:
    args = shlex.split(spec)
    if not args:
        raise HandoutError('include にパスが無い')
    path, opts = args[0], {}
    for a in args[1:]:
        k, _, v = a.partition('=')
        opts[k] = v
    unknown = set(opts) - {'section', 'table', 'rows', 'cols', 'lines'}
    if unknown:
        raise HandoutError(f'include の引数が不明: {sorted(unknown)}')
    source_path = repo_path(path)
    source = read_text(source_path)
    body = section_lines(source.split('\n'), opts.get('section'))
    where = f'{path} {opts.get("section", "")}'.strip()
    if 'table' in opts:
        ts = tables(body)
        n = int(opts['table'])
        if not 1 <= n <= len(ts):
            raise HandoutError(f'{where}: 表 {n} が無い（{len(ts)} 個）')
        t = ts[n - 1]
        rows = t[:2]
        if 'rows' in opts:
            want = [w.strip() for w in opts['rows'].split(';')]
            found = {cells(r)[0]: r for r in t[2:]}
            missing = [w for w in want if w not in found]
            if missing:
                raise HandoutError(f'{where}: 表 {n} に行が無い: {missing}')
            rows += [found[w] for w in want]
        else:
            rows += t[2:]
        if 'cols' in opts:
            k = int(opts['cols'])
            rows = ['| ' + ' | '.join(cells(r)[:k]) + ' |' for r in rows]
        selected = '\n'.join(rows)
    elif 'lines' in opts:
        prefixes = [p for p in opts['lines'].split(';') if p]
        picked = []
        for p in prefixes:
            hit = [line for line in body if line.startswith(p)]
            if not hit:
                raise HandoutError(f'{where}: 「{p}」で始まる行が無い')
            picked += hit
        selected = '\n'.join(picked)
    else:
        selected = '\n'.join(body).strip('\n')
    return absolutize_images(selected, source_path.parent, source, image_uris)


def expand_includes(md: str, image_uris: set[str]) -> str:
    return INCLUDE_RE.sub(lambda m: expand_include(m.group(1), image_uris), md)


# ---------- Markdown → HTML ----------

def image_uri(src: str, base: Path, image_uris: set[str]) -> str:
    parsed = urlsplit(src)
    if parsed.scheme in ('http', 'https'):
        return src
    if parsed.scheme and parsed.scheme != 'file':
        raise HandoutError(f'画像 URI の形式が未対応: {src}')
    if parsed.scheme == 'file':
        if parsed.netloc:
            raise HandoutError(f'ローカル以外の file URI: {src}')
        p = Path(unquote(parsed.path)).resolve()
    else:
        p = (base / unquote(src)).resolve()
    try:
        rel = p.relative_to(ROOT).as_posix()
    except ValueError:
        raise HandoutError(f'リポジトリの外の画像パス: {src}')
    checked = repo_path(rel)
    uri = checked.as_uri()
    image_uris.add(uri)
    return uri


def absolutize_images(md: str, base: Path, reference_source: str | None = None,
                      image_uris: set[str] | None = None) -> str:
    image_uris = image_uris if image_uris is not None else set()
    if UNINSPECTABLE_HTML_IMAGE_RE.search(md):
        raise HandoutError('検査できない HTML の画像埋め込みは使えない')

    definitions = {}
    for match in REFERENCE_DEF_RE.finditer(reference_source if reference_source is not None else md):
        label = ' '.join(match.group(1).split()).casefold()
        definitions[label] = match.group(2) or match.group(3)

    def fix_reference(m):
        alt, label = m.group(1), m.group(2) or m.group(1)
        target = definitions.get(' '.join(label.split()).casefold())
        if target is None:
            return m.group(0)
        return f'![{alt}]({image_uri(target, base, image_uris)})'

    md = IMAGE_REFERENCE_RE.sub(fix_reference, md)

    def fix(m):
        alt, src = m.group(1), m.group(2)
        return f'![{alt}]({image_uri(src, base, image_uris)})'
    return IMAGE_RE.sub(fix, md)


def validate_html_images(body: str, image_uris: set[str]) -> None:
    class ImageValidator(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag.lower() == 'img':
                src = dict(attrs).get('src')
                if not src:
                    raise HandoutError('src の無い HTML 画像は使えない')
                parsed = urlsplit(src)
                if parsed.scheme in ('http', 'https'):
                    return
                if parsed.scheme != 'file' or src not in image_uris:
                    raise HandoutError(f'検査されていない画像参照: {src}')

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)

    ImageValidator().feed(body)


def pandoc(md: str, prefix: str, lua: Path) -> str:
    r = subprocess.run(['pandoc', '-f', 'gfm', '-t', 'html5', f'--id-prefix={prefix}', '--lua-filter', str(lua), '--wrap=none'],
                       input=md.encode('utf-8'), capture_output=True)
    if r.returncode:
        raise HandoutError('pandoc が失敗: ' + r.stderr.decode('utf-8', 'replace'))
    out = r.stdout.decode('utf-8')
    # 段落に単独の画像は、代替テキストを図の説明にする
    return re.sub(r'<p><img src="([^"]+)" alt="([^"]*)" ?/?></p>',
                  r'<figure><img src="\1" alt="\2"><figcaption>\2</figcaption></figure>', out)


def figure(src: str, caption: str) -> str:
    p = repo_path(src)
    return f'<figure><img src="{p.as_uri()}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>'


# ---------- 回路図 ----------

def crop_svg(src: Path, dst: Path, margin: float = 6.0) -> None:
    """KiCad の SVG（絶対座標の M/L と rect だけ）を、描いてある範囲に詰める。"""
    t = src.read_text(encoding='utf-8')
    xs, ys = [], []
    for d in re.findall(r'\sd="([^"]*)"', t):
        if re.search(r'[A-Za-z]', re.sub(r'[MLZ]', '', d)):
            raise HandoutError(f'{src.name}: M・L・Z 以外のパス命令があり範囲を計算できない')
        nums = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', d)]
        xs += nums[0::2]
        ys += nums[1::2]
    for x, y, w, h in re.findall(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"', t):
        xs += [float(x), float(x) + float(w)]
        ys += [float(y), float(y) + float(h)]
    if not xs:
        raise HandoutError(f'{src.name}: 描画が見つからない')
    x0, y0 = min(xs) - margin, min(ys) - margin
    w, h = max(xs) - min(xs) + 2 * margin, max(ys) - min(ys) + 2 * margin
    t, n = re.subn(r'width="[\d.]+mm" height="[\d.]+mm" viewBox="[^"]+"',
                   f'width="{w:.3f}mm" height="{h:.3f}mm" viewBox="{x0:.3f} {y0:.3f} {w:.3f} {h:.3f}"', t, count=1)
    if n != 1:
        raise HandoutError(f'{src.name}: svg の寸法の書式が想定と違う')
    dst.write_text(t, encoding='utf-8')


# ---------- 組版 ----------

CSS = r'''
@page { size: A4; margin: 18mm 16mm 18mm 16mm;
  @top-right { content: "__HEADER__"; font-family: "Noto Sans CJK JP", "Noto Sans JP", "Yu Gothic", "Meiryo", sans-serif; font-size: 7pt; color: #6B7785; }
  @bottom-center { content: counter(page) " / " counter(pages); font-family: "Noto Sans CJK JP", "Noto Sans JP", "Yu Gothic", "Meiryo", sans-serif; font-size: 7pt; color: #6B7785; } }
@page :first { @top-right { content: none; } }
@page wide { size: A3 landscape; margin: 10mm 10mm 14mm 10mm; }
html { font-family: "Noto Sans CJK JP", "Noto Sans JP", "Yu Gothic", "Meiryo", sans-serif; font-size: 10pt; line-height: 1.7; color: #17212B; }
body { margin: 0; }
code, pre { font-family: "DejaVu Sans Mono", "Consolas", "Noto Sans CJK JP", "BIZ UDGothic", monospace; }
code { font-size: 0.88em; background: #EEF1F4; border-radius: 3px; padding: 0 3px; }
pre { background: #F3F5F7; border: 1px solid #D5DBE2; border-radius: 6px; padding: 10px 12px; font-size: 7.6pt; line-height: 1.5; white-space: pre-wrap; word-break: break-all; }
pre code { background: none; padding: 0; font-size: inherit; }
a { color: inherit; text-decoration: none; }
.cover { page-break-after: always; padding-top: 18mm; }
.eyebrow { color: #B3541E; font-weight: 700; letter-spacing: 0.08em; font-size: 10pt; }
.cover-title { font-size: 28pt; margin: 4mm 0 2mm; line-height: 1.25; }
.cover-sub { color: #4A5665; font-size: 11pt; margin: 0 0 8mm; }
.cover-img { width: 100%; border: 1px solid #D5DBE2; border-radius: 6px; margin-bottom: 8mm; }
table.meta { width: 100%; font-size: 9pt; }
table.meta th { width: 18mm; text-align: left; background: #F3F5F7; }
.cover-note { color: #4A5665; font-size: 8.5pt; margin-top: 6mm; }
.toc { page-break-after: always; }
.toc h1 { font-size: 20pt; margin: 0 0 6mm; }
.toc-ch { margin-bottom: 4mm; break-inside: avoid; }
.toc-h { font-weight: 700; font-size: 11pt; border-bottom: 1px solid #D5DBE2; padding-bottom: 1mm; margin-bottom: 1.5mm; }
.toc-h .num { display: inline-block; min-width: 16mm; color: #B3541E; }
.toc-sub { columns: 2; column-gap: 10mm; margin: 0 0 0 16mm; padding: 0; list-style: none; font-size: 9pt; }
.toc-sub li { break-inside: avoid; }
.chapter { page-break-before: always; }
.chap-head { margin-bottom: 6mm; }
.chap-num { color: #B3541E; font-weight: 700; font-size: 12pt; }
.chapter h1 { font-size: 20pt; margin: 1mm 0 1mm; line-height: 1.3; }
.chap-src { font-family: "DejaVu Sans Mono", "Consolas", monospace; font-size: 7.5pt; color: #6B7785; border-bottom: 1.5px solid #17212B; padding-bottom: 2mm; }
h2 { font-size: 13.5pt; margin: 7mm 0 3mm; padding-left: 3mm; border-left: 4px solid #B3541E; line-height: 1.4; break-after: avoid; }
h3 { font-size: 11pt; margin: 5mm 0 2mm; break-after: avoid; }
p { margin: 0 0 3mm; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
ul.task-list { list-style: none; padding-left: 1mm; }
input[type=checkbox] { margin-right: 4px; }
blockquote { margin: 0 0 4mm; padding: 2mm 4mm; background: #F3F5F7; border-left: 3px solid #B8C2CE; color: #2B3743; font-size: 9pt; }
blockquote p { margin: 0 0 1mm; }
table { border-collapse: collapse; width: auto; max-width: 100%; margin: 0 0 4mm; font-size: 8.3pt; line-height: 1.5; }
th { background: #EEF1F4; font-weight: 700; min-width: 2.4em; }
th, td { border: 1px solid #D5DBE2; padding: 3px 6px; vertical-align: top; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
figure { margin: 2mm 0 5mm; break-inside: avoid; }
figure img { width: 100%; border: 1px solid #D5DBE2; border-radius: 4px; }
figcaption { font-size: 8pt; color: #4A5665; text-align: center; margin-top: 1mm; }
.schem { page: wide; }
.schem .chap-head { margin-bottom: 2mm; }
.schem-note { font-size: 8.5pt; color: #4A5665; margin-bottom: 2mm; }
.schem-img { display: block; width: 100%; max-height: 228mm; object-fit: contain; border: 1px solid #D5DBE2; }
'''


def git_state() -> str:
    try:
        head = subprocess.run(['git', '--no-optional-locks', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(['git', '--no-optional-locks', 'status', '--porcelain', '--ignore-submodules'], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return '不明（git の情報が取れない）'
    return f'<code>{head}</code>' + ('（作業ツリーに未コミットの変更あり）' if dirty else '')


def find_chrome(given: str | None) -> str:
    if given:
        return given
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'msedge'):
        p = shutil.which(name)
        if p:
            return p
    for env, sub in (('PROGRAMFILES', r'Google\Chrome\Application\chrome.exe'),
                     ('PROGRAMFILES(X86)', r'Google\Chrome\Application\chrome.exe'),
                     ('LOCALAPPDATA', r'Google\Chrome\Application\chrome.exe'),
                     ('PROGRAMFILES(X86)', r'Microsoft\Edge\Application\msedge.exe'),
                     ('PROGRAMFILES', r'Microsoft\Edge\Application\msedge.exe')):
        base = os.environ.get(env)
        if base and Path(base, sub).is_file():
            return str(Path(base, sub))
    raise HandoutError('Chrome か Edge が見つからない（--chrome で指定する）')


def build(name: str, date: str, out: Path, chrome: str | None, keep_html: bool) -> Path:
    if shutil.which('pandoc') is None:
        raise HandoutError('pandoc が見つからない')
    conf = json.loads(read_text(repo_path(f'docs/handouts/{name}.json')))
    work = out / f'{name}_work'
    work.mkdir(parents=True, exist_ok=True)
    lua = work / 'unlink.lua'
    lua.write_text('function Link(el) return el.content end\n', encoding='utf-8')

    chapters = []
    for i, ch in enumerate(conf['chapters']):
        kinds = [k for k in ('md', 'schematic', 'code') if k in ch]
        if len(kinds) != 1:
            raise HandoutError(f'章 {ch.get("num")}: md・schematic・code のどれか 1 つを指定する')
        kind, src = kinds[0], ch[kinds[0]]
        path = repo_path(src)
        title, body = ch.get('title'), ''
        if kind == 'md':
            md = read_text(path)
            first, _, rest = md.partition('\n')
            if first.startswith('# '):
                title = title or first[2:].strip()
                md = rest
            image_uris = set()
            md = absolutize_images(expand_includes(md, image_uris), path.parent, image_uris=image_uris)
            body = pandoc(md, f'c{i}-', lua)
            validate_html_images(body, image_uris)
        elif kind == 'code':
            body = f'<pre><code>{html.escape(read_text(path).rstrip())}</code></pre>'
        else:
            cropped = work / (path.stem + '_crop.svg')
            crop_svg(path, cropped)
            note = f'<p class="schem-note">{html.escape(ch["note"])}</p>' if ch.get('note') else ''
            body = f'{note}<img class="schem-img" src="{cropped.resolve().as_uri()}" alt="{html.escape(title or "回路図")}">'
        if not title:
            raise HandoutError(f'章 {ch.get("num")}: 題が無い（title を書くか、先頭を # 見出しにする）')
        if 'figure_before' in ch:
            body = figure(ch['figure_before']['src'], ch['figure_before']['caption']) + body
        chapters.append((ch.get('num', str(i + 1)), title, ch.get('source_label', src), body, kind == 'schematic'))

    toc = []
    for i, (num, title, _, body, _) in enumerate(chapters):
        subs = ''.join(f'<li><a href="#{a}">{s}</a></li>' for a, s in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body))
        toc.append(f'<div class="toc-ch"><div class="toc-h"><span class="num">{html.escape(num)}</span>'
                   f'<a href="#ch{i}">{html.escape(title)}</a></div>' + (f'<ol class="toc-sub">{subs}</ol>' if subs else '') + '</div>')
    parts = []
    for i, (num, title, label, body, wide) in enumerate(chapters):
        parts.append(f'<section class="chapter{" schem" if wide else ""}"><header class="chap-head">'
                     f'<div class="chap-num">{html.escape(num)}</div><h1 id="ch{i}">{html.escape(title)}</h1>'
                     f'<div class="chap-src">{html.escape(label)}</div></header>{body}</section>')

    cover_img = f'<img class="cover-img" src="{repo_path(conf["cover_image"]).as_uri()}" alt="">' if conf.get('cover_image') else ''
    meta = [('状態', html.escape(conf.get('status', ''))), ('基準', git_state()),
            ('作成日', date), ('収録', html.escape(conf.get('contents', '')))]
    cover = ('<section class="cover"><div class="eyebrow">7400SeriesProcessor</div>'
             f'<h1 class="cover-title">{html.escape(conf["title"])}</h1>'
             f'<p class="cover-sub">{html.escape(conf.get("subtitle", ""))}</p>{cover_img}'
             '<table class="meta">' + ''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in meta) + '</table>'
             + (f'<p class="cover-note">{html.escape(conf["note"])}</p>' if conf.get('note') else '') + '</section>')
    header = f'{conf["title"]}（{date}）'.replace('"', '\\"')
    doc = (f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>{html.escape(conf["title"])}</title>'
           f'<style>{CSS.replace("__HEADER__", header)}</style></head><body>{cover}'
           f'<section class="toc"><h1>目次</h1>{"".join(toc)}</section>{"".join(parts)}</body></html>')
    page = work / f'{name}.html'
    page.write_text(doc, encoding='utf-8')

    pdf = (out / f'{name}_{date}.pdf').resolve()
    cmd = [find_chrome(chrome), '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
           '--generate-pdf-document-outline', f'--user-data-dir={(work / "chrome-profile").resolve()}',
           '--virtual-time-budget=10000', f'--print-to-pdf={pdf}', page.resolve().as_uri()]
    if os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() == 0:
        cmd.insert(1, '--no-sandbox')
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode or not pdf.is_file():
        raise HandoutError('PDF の書き出しに失敗: ' + r.stderr.decode('utf-8', 'replace')[-800:])
    if not keep_html:
        shutil.rmtree(work, ignore_errors=True)
    return pdf


def main() -> int:
    ap = argparse.ArgumentParser(description='公開用の資料（docs/handouts/<名前>.json）を PDF に組む')
    ap.add_argument('name', help='構成ファイルの名前（docs/handouts/<名前>.json）')
    ap.add_argument('--date', default=datetime.date.today().isoformat(), help='表紙と頁の見出しの日付（既定は今日）')
    ap.add_argument('--out', default=str(ROOT / '.temp' / 'handouts'), help='出力先（既定は .temp/handouts）')
    ap.add_argument('--chrome', help='Chrome か Edge の実行ファイル（既定は自動で探す）')
    ap.add_argument('--keep-html', action='store_true', help='組版前の HTML と作業ファイルを残す')
    a = ap.parse_args()
    try:
        pdf = build(a.name, a.date, Path(a.out), a.chrome, a.keep_html)
    except HandoutError as e:
        print(f'[error] {e}', file=sys.stderr)
        return 1
    print(f'[ok] {pdf}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
