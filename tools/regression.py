#!/usr/bin/env python3
"""Regression suite for chineseword.we1co.me (single-file worksheet app).

Runs a local static server, drives headless Chromium with Playwright, and asserts
DOM facts for the worksheet matrix (layouts / grid styles / tracing formats /
per-row / big demo / stroke page / dictation mode / variant glyphs / s2t / print).

Usage:
    ~/venvs/chinese-worksheet-tools/bin/python tools/regression.py [-v]

Exit code 0 = all pass.
"""
import functools
import http.server
import json
import os
import socket
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = '/usr/local/bin/chromium'
VERBOSE = '-v' in sys.argv
RESULTS = []


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def serve(port):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', port), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def check(name, actual, expected, extra=''):
    ok = actual == expected
    RESULTS.append((name, ok, actual, expected, extra))
    if not ok or VERBOSE:
        print(('  PASS ' if ok else '  FAIL ') + name +
              ('' if ok else '  expected=%r actual=%r %s' % (expected, actual, extra)))
    return ok


def check_true(name, cond, extra=''):
    RESULTS.append((name, bool(cond), cond, True, extra))
    if not cond or VERBOSE:
        print(('  PASS ' if cond else '  FAIL ') + name + ('' if cond else '  ' + str(extra)))
    return bool(cond)


class Harness:
    def __init__(self, browser, base):
        self.browser = browser
        self.base = base
        self.errors = []
        self.http_errors = []

    def page(self, **opts):
        ctx = self.browser.new_context(**opts)
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: self.errors.append('pageerror:' + str(e)[:160]))
        pg.on('console', lambda m: self.errors.append('console:' + m.text[:160])
              if m.type == 'error' else None)
        pg.on('response', lambda r: self.http_errors.append((r.status, r.url.split('/')[-1]))
              if r.status >= 400 else None)
        pg.goto(self.base + '/index.html?t=%d' % id(pg), wait_until='load')
        pg.wait_for_timeout(300)
        return pg

    def set_opts(self, pg, opts):
        pg.evaluate("""(o) => {
          for (const [id, v] of Object.entries(o)) {
            const el = document.getElementById(id);
            if (!el) throw new Error('missing control #' + id);
            if (el.type === 'checkbox') el.checked = !!v; else el.value = String(v);
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new Event('input', {bubbles: true}));
          }
        }""", opts)

    def generate(self, pg, text, opts=None, wait=2400, fresh=True):
        """fresh=True reloads with clean localStorage so cases can't leak state into each other."""
        if fresh:
            pg.evaluate("() => { try { localStorage.removeItem('chinese-ws-settings'); } catch (e) {} }")
            pg.reload(wait_until='load')
            pg.wait_for_timeout(400)
        pg.evaluate("(t) => { const el = document.getElementById('inputText'); el.value = t;"
                    " el.dispatchEvent(new Event('input', {bubbles: true})); }", text)
        if opts:
            self.set_opts(pg, opts)
        pg.evaluate("""() => {
          const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('生成'));
          b.click();
        }""")
        pg.wait_for_function("() => document.querySelectorAll('.char-card, .sentence-block').length > 0",
                             timeout=8000)
        pg.wait_for_timeout(wait)

    def stats(self, pg):
        return pg.evaluate("""() => {
          const cards = [...document.querySelectorAll('.char-card')];
          return {
            cards: cards.length,
            charGlyphs: document.querySelectorAll('.char-glyph svg').length,
            nums: document.querySelectorAll('.stroke-num-cell text').length,
            arrows: document.querySelectorAll('.stroke-arrow').length,
            guideGlyphs: document.querySelectorAll('.guide-glyph').length,
            sentenceBlocks: document.querySelectorAll('.sentence-block').length,
            sentenceCells: document.querySelectorAll('.sentence-cell').length,
            strokeBlocks: document.querySelectorAll('.stroke-page-block').length,
            stepCells: document.querySelectorAll('.stroke-step-cell').length,
            maxStep: Math.max(0, ...[...document.querySelectorAll('.stroke-step-cell')]
                              .map(e => +e.dataset.stepK || 0)),
            wsClasses: document.getElementById('worksheet').className,
            contentClasses: document.getElementById('wsContent').className,
          };
        }""")

    def overflow(self, pg):
        return pg.evaluate("""() => {
          let worst = 0, who = '';
          for (const el of document.querySelectorAll('#worksheet *')) {
            const d = el.scrollWidth - el.clientWidth;
            if (d > worst) { worst = d; who = String(el.className.baseVal || el.className).slice(0, 40); }
          }
          return {worst: Math.round(worst), who};
        }""")

    def visible(self, pg, sel):
        return pg.evaluate("""(s) => [...document.querySelectorAll(s)]
          .filter(e => getComputedStyle(e).display !== 'none').length""", sel)


def main():
    port = free_port()
    serve(port)
    base = 'http://127.0.0.1:%d' % port
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True,
                                    env={**os.environ, 'TMPDIR': '/tmp'},
                                    args=['--no-sandbox', '--disable-dev-shm-usage'])
        h = Harness(browser, base)

        # ---------- 1. basic word worksheet ----------
        pg = h.page(viewport={'width': 1280, 'height': 1000})
        h.generate(pg, '山水')
        s = h.stats(pg)
        check('1 basic: cards', s['cards'], 2)
        check('1 basic: one char glyph per card', s['charGlyphs'], 2)
        check('1 basic: stroke numbers (山3+水4)', s['nums'], 7)
        o = h.overflow(pg)
        check('1 basic: no horizontal overflow', o['worst'] <= 2, True, o)

        # ---------- 2. sentence + punctuation ----------
        h.generate(pg, '我愛香港。真好。', {'optLayout': 'sentence', 'optSentenceTimes': 2})
        s = h.stats(pg)
        check('2 sentence: blocks', s['sentenceBlocks'], 2)
        punct = pg.evaluate("""() => [...document.querySelectorAll('.sentence-cell')]
          .filter(c => /[，。！？：；、]/.test((c.textContent || '').trim())).length""")
        check('2 sentence: punctuation occupies cells', punct, 2)

        # ---------- 3. word + sentence ----------
        h.generate(pg, '花開', {'optLayout': 'word+sentence'})
        s = h.stats(pg)
        check('3 word+sentence: cards', s['cards'], 2)
        check('3 word+sentence: sentence block', s['sentenceBlocks'], 1)

        # ---------- 4. grid styles ----------
        expect = {'mizi': ['guide-mizi'], 'tian': ['guide-tian'], 'jiugong': ['guide-jiugong'],
                  'jingzi': ['guide-grid3'], 'caoni': ['guide-caoni'],
                  'caoni-color': ['guide-caoni', 'guide-caoni-color'], 'blank': ['guide-blank']}
        for style, classes in expect.items():
            h.generate(pg, '天', {'optGuideStyle': style}, wait=900)
            got = h.stats(pg)['wsClasses'].split()
            check('4 style %s: classes' % style, all(c in got for c in classes), True, got)
            guides = pg.evaluate("() => document.querySelectorAll('.cell-guides').length")
            check_true('4 style %s: guide svg present' % style, guides > 0, guides)

        # ---------- 5. tracing row counts (天 4 practice rows) ----------
        for gc, want in [('none', 0), ('1', 1), ('2', 2), ('all', 4)]:
            h.generate(pg, '天', {'optGuideStyle': 'mizi', 'optGuideCount': gc}, wait=1200)
            check('5 guideCount %s: .guide-glyph' % gc, h.stats(pg)['guideGlyphs'], want)

        # ---------- 6. demo/trace format matrix (天 = 4 strokes) ----------
        matrix = [('num+arrow', 'num', (4, 4), (4, 0)),
                  ('num+arrow', 'num+arrow', (4, 4), (4, 4)),
                  ('num+arrow', 'plain', (4, 4), (0, 0)),
                  ('plain', 'num', (0, 0), (4, 0)),
                  ('num', 'plain', (4, 0), (0, 0))]
        for demo, trace, demoExp, traceExp in matrix:
            h.generate(pg, '天', {'optGuideCount': '1', 'optDemoFormat': demo,
                                  'optTraceFormat': trace}, wait=2200)
            c = pg.evaluate("""() => {
              const card = document.querySelector('.char-card');
              const rows = [...card.querySelectorAll('.practice-row')];
              const per = r => ({nums: r.querySelectorAll('text').length,
                                 arrows: r.querySelectorAll('.stroke-arrow').length});
              return {first: per(rows[0]), rest: rows.slice(1).map(per)};
            }""")
            check('6 %s/%s: demo (nums,arrows)' % (demo, trace),
                  (c['first']['nums'], c['first']['arrows']), demoExp)
            tot = (sum(r['nums'] for r in c['rest']), sum(r['arrows'] for r in c['rest']))
            n = len(c['rest'])
            check('6 %s/%s: practice totals' % (demo, trace), tot,
                  (traceExp[0] * n, traceExp[1] * n))

        # ---------- 7. perRow font/cell ratio ----------
        h.generate(pg, '天', {'optGuideCount': '1', 'optPerRow': '4', 'optSize': 'medium',
                              'optBigDemo': 'no'}, wait=2200)
        ratio = pg.evaluate("""() => {
          const cell = document.querySelector('.practice-row[data-perrow] .practice-cell');
          const svg = cell && cell.querySelector('.guide-glyph svg');
          if (!svg) return null;
          const b = svg.getBoundingClientRect(), c = cell.getBoundingClientRect();
          return {ratio: +(b.width / c.width).toFixed(3), cell: Math.round(c.width)};
        }""")
        check_true('7 perRow=4: glyph/cell ratio ≈ 0.82 (%s)' % ratio,
                   ratio and 0.78 <= ratio['ratio'] <= 0.86, ratio)

        # ---------- 8. big demo sizes ----------
        for mode, expect_ratio, expect_first in [('no', 1.0, 96), ('big', 2.0, 192), ('all', 1.0, 192)]:
            h.generate(pg, '天', {'optBigDemo': mode, 'optPerRow': 'auto', 'optGuideCount': '1'},
                       wait=2200)
            w = pg.evaluate("""() => {
              const cells = [...document.querySelectorAll('.char-card .practice-cell')];
              return [Math.round(cells[0].getBoundingClientRect().width),
                      Math.round(cells[1].getBoundingClientRect().width)];
            }""")
            check('8 bigDemo %s: first cell width' % mode, w[0], expect_first, w)
            check('8 bigDemo %s: first/other ratio' % mode, round(w[0] / w[1], 1), expect_ratio)

        # ---------- 9. stroke order worksheet ----------
        h.generate(pg, '花', {'optStrokePage': True, 'optBigDemo': 'no'}, wait=3200)
        s = h.stats(pg)
        check('9 strokePage: blocks', s['strokeBlocks'], 1)
        check('9 strokePage: last step = stroke count (花 8)', s['maxStep'], 8)

        # ---------- 10. stroke count consistency for HanziWriter-fallback chars ----------
        h.generate(pg, '蒔', {'optStrokePage': True}, wait=3200)
        s = h.stats(pg)
        card_s = pg.evaluate("""() => {
          const m = document.querySelector('.char-card').textContent.match(/(\\d+)\\s*畫/);
          return m ? +m[1] : null;
        }""")
        check('10 蒔 card stroke count == HW stroke count', card_s, 14)
        check('10 蒔 stroke worksheet cells', s['maxStep'], card_s)

        # ---------- 11. dictation mode hides every answer layer ----------
        h.generate(pg, '花開', {'optLayout': 'word+sentence', 'optStrokePage': True,
                                'optGuideCount': '1'}, wait=3000)
        before = {k: h.visible(pg, sel) for k, sel in
                  [('guide', '.guide-char'), ('sentence', '.sentence-cell .guide-char'),
                   ('strokePage', '.stroke-page'), ('numbers', '.stroke-num-cell text')]}
        check_true('11 練習版: guides visible', before['guide'] > 0 and before['strokePage'] == 1, before)
        pg.evaluate("() => document.getElementById('btnQuizMode').click()")
        pg.wait_for_timeout(600)
        after = {k: h.visible(pg, sel) for k, sel in
                 [('guide', '.guide-char'), ('sentence', '.sentence-cell .guide-char'),
                  ('strokePage', '.stroke-page'), ('numbers', '.stroke-num-cell text')]}
        check('11 默書版: all tracing hidden', after, {'guide': 0, 'sentence': 0,
                                                       'strokePage': 0, 'numbers': 0})
        check('11 默書版: content carries quiz-mode',
              'quiz-mode' in h.stats(pg)['contentClasses'], True)
        pg.evaluate("() => document.getElementById('btnQuizMode').click()")
        pg.wait_for_timeout(600)
        back = h.visible(pg, '.guide-char')
        check_true('11 切回練習版: guides return', back > 0, back)

        # ---------- 12. variant glyphs ----------
        std = json.load(open(os.path.join(ROOT, 'glyphs/5cf0.json')))['s'][0][:40]
        var = json.load(open(os.path.join(ROOT, 'glyphs/variants/5cf0.json')))['s'][0][:40]
        shuo_std = json.load(open(os.path.join(ROOT, 'glyphs/8aaa.json')))['s'][0][:40]
        shuo_var = json.load(open(os.path.join(ROOT, 'glyphs/variants/8aaa.json')))['s'][0][:40]
        for variant, want, label in [(False, std, 'standard'), (True, var, 'variant')]:
            h.generate(pg, '峰峯說', {'optVariant': variant, 'optStrokePage': False}, wait=2600)
            got = pg.evaluate("""() => [...document.querySelectorAll('.char-card')].map(c => {
              const p = c.querySelector('.char-glyph svg path');
              return p ? p.getAttribute('d').slice(0, 40) : null; })""")
            check('12 variant=%s: 峰 uses %s glyph' % (variant, label), got[0], want, got)
            check('12 variant=%s: 峯 keeps HK glyph' % variant, got[1], std)
            check('12 variant=%s: 說 uses %s glyph' % (variant, label),
                  got[2], shuo_var if variant else shuo_std, got)
        # 香港正字（説）永遠用 EDB 字形，唔會被 HanziWriter 版本取代
        shuo_hk = json.load(open(os.path.join(ROOT, 'glyphs/%x.json' % ord('説'))))['s'][0][:40]
        h.generate(pg, '説', {'optVariant': True}, wait=2000)
        got = pg.evaluate("""() => { const p = document.querySelector('.char-glyph svg path');
          return p ? p.getAttribute('d').slice(0, 40) : null; }""")
        check('12 variant mode: HK 正字説 keeps EDB glyph', got, shuo_hk)

        # ---------- 12b. 字形語意層：來源碼、筆數層級、另一寫法行 ----------
        h.generate(pg, '峰蒔', {'optVariant': False}, wait=2600)
        labels = pg.evaluate("""() => {
          const card = c => ({
            meta: (c.querySelector('.meta-row') || {}).textContent || '',
            badge: [...c.querySelectorAll('.src-badge')].map(b => b.dataset.src),
            form: (c.querySelector('.form-row') || {}).textContent || ''
          });
          return {
            option: document.querySelector('label[for=optVariant]').textContent,
            cards: [...document.querySelectorAll('.char-card')].map(card)
          };
        }""")
        check('12b option label', labels['option'].strip(), '顯示我輸入的寫法')
        check('12b EDB card meta', '香港教育標準' in labels['cards'][0]['meta'], True, labels['cards'][0])
        check('12b EDB badge', labels['cards'][0]['badge'], ['EDB'])
        check('12b fallback card uses 參考字形',
              '參考字形' in labels['cards'][1]['meta'], True, labels['cards'][1])
        check('12b fallback badge', labels['cards'][1]['badge'], ['HW'])
        check('12b 峰 form row (standard shown)',
              labels['cards'][0]['form'], '字形：峯（香港教育標準）｜峰（你的輸入）')
        h.generate(pg, '峰', {'optVariant': True}, wait=2400)
        on_form = pg.evaluate("""() => (document.querySelector('.form-row') || {}).textContent || ''""")
        check('12b 峰 form row (own form shown)',
              on_form, '字形：峰（你的寫法）｜峯（香港教育標準）')
        # ---------- 12c. 又讀折疊（顧問 Q6） ----------
        h.generate(pg, '說睇', {'optVariant': False}, wait=2600)
        alt = pg.evaluate("""() => {
          const cards = [...document.querySelectorAll('.char-card')];
          return cards.map(c => {
            const d = c.querySelector('.alt-readings');
            return {ch: c.dataset.char, has: !!d, open: d ? d.open : null,
                    text: d ? (d.querySelector('div') || {}).textContent || '' : '',
                    inline: c.querySelectorAll('.reading-alt').length};
          });
        }""")
        check('12c 又讀 block exists', [c['has'] for c in alt], [True, True])
        check('12c 又讀 collapsed by default', [c['open'] for c in alt], [False, False])
        check('12c 又讀 no inline duplicates', [c['inline'] for c in alt], [0, 0])
        check_true('12c 又讀 text', '粵拼又讀' in alt[0]['text'], alt[0]['text'])
        opened = pg.evaluate("""() => { const d = document.querySelector('.alt-readings');
          d.open = true; return d.open; }""")
        check('12c 又讀 opens', opened, True)
        pg.emulate_media(media='print')
        pg.wait_for_timeout(300)
        check('12c 又讀 hidden in print',
              pg.evaluate("() => getComputedStyle(document.querySelector('.alt-readings')).display"),
              'none')
        pg.emulate_media(media='screen')

        h.generate(pg, '发展头发干杯皇后什么', {'optS2T': True, 'optVariant': False}, wait=1500)
        conv = pg.evaluate("() => document.getElementById('inputText').value")
        check('13 s2t conversion', conv, '發展頭髮乾杯皇后什麼', conv)

        # ---------- 14. dedup ----------
        h.generate(pg, '天天向上', {'optDedup': True}, wait=1500)
        check('14 dedup: cards', h.stats(pg)['cards'], 3)

        # ---------- 15. localStorage round-trip ----------
        h.set_opts(pg, {'optGuideCount': 'all', 'optBigDemo': 'big', 'optVariant': True,
                        'optGuideStyle': 'caoni-color'})
        pg.wait_for_timeout(700)
        pg.reload(wait_until='load')
        pg.wait_for_timeout(900)
        restored = pg.evaluate("""() => ({
          guideCount: document.getElementById('optGuideCount').value,
          bigDemo: document.getElementById('optBigDemo').value,
          variant: document.getElementById('optVariant').checked,
          style: document.getElementById('optGuideStyle').value})""")
        check('15 localStorage round-trip', restored,
              {'guideCount': 'all', 'bigDemo': 'big', 'variant': True, 'style': 'caoni-color'})

        # ---------- 16. print layout ----------
        h.generate(pg, '永遠', {'optPrintSize': '2.2cm', 'optGuideCount': '1', 'optPerRow': 'auto',
                                'optBigDemo': 'no'}, wait=2600)
        pg.emulate_media(media='print')
        pg.wait_for_timeout(500)
        pr = pg.evaluate("""() => {
          const cells = [...document.querySelectorAll('.char-card .practice-cell')];
          const widths = cells.map(c => Math.round(c.getBoundingClientRect().width * 10) / 10);
          const svg = cells[0].querySelector('.hk-glyph-svg, .guide-glyph svg');
          return {widths, unique: [...new Set(widths)].length,
                  ratio: svg ? +(svg.getBoundingClientRect().width /
                                 cells[0].getBoundingClientRect().width).toFixed(3) : null};
        }""")
        check('16 print: uniform cell width', pr['unique'], 1, pr['widths'])
        check('16 print: cell = 2.2cm (≈83px)', round(pr['widths'][0]), 83)
        check_true('16 print: glyph/cell ratio ≈ 0.82 (%s)' % pr['ratio'],
                   pr['ratio'] and 0.75 <= pr['ratio'] <= 0.88, pr)
        po = h.overflow(pg)
        check('16 print: no horizontal overflow', po['worst'] <= 2, True, po)
        pg.emulate_media(media='screen')

        # ---------- 17. mobile viewport ----------
        mob = h.page(viewport={'width': 390, 'height': 844}, is_mobile=True,
                     device_scale_factor=3, has_touch=True)
        h.generate(mob, '山水花開永遠香港', {'optGuideCount': '1'}, wait=3200)
        ms = h.stats(mob)
        check('17 mobile: cards', ms['cards'], 8)
        mv = mob.evaluate("""() => ({doc: document.documentElement.scrollWidth,
          win: window.innerWidth,
          widest: Math.max(...[...document.querySelectorAll('#worksheet *')]
            .map(e => e.getBoundingClientRect().right))})""")
        check_true('17 mobile: no page-level overflow (%s)' % mv,
                   mv['doc'] <= mv['win'] + 2, mv)

        # ---------- 18. large input ----------
        h.generate(pg, '一二三四五六七八九十百千', {'optGuideCount': '1'}, wait=3000)
        check('18 large input: cards', h.stats(pg)['cards'], 12)
        lo = h.overflow(pg)
        check('18 large input: no overflow', lo['worst'] <= 2, True, lo)

        # ---------- 19. errors ----------
        import re as _re
        punct_404 = [x for x in h.http_errors
                     if _re.match(r'^(3002|3001|ff0c|ff01|ff1f|ff1b|ff1a|ff08|ff09)\.json', x[1])]
        check('17 punctuation must not request glyph data', punct_404, [])
        unexpected = [x for x in h.http_errors if not _re.match(r'^[0-9a-f]{4,5}\.json', x[1])]
        check('17 no unexpected 4xx/5xx', unexpected, [], unexpected[:5])
        real = [e for e in h.errors if not e.startswith('console:')]
        check('17 no JS errors', real, [], real[:4])

        browser.close()

    fails = [r for r in RESULTS if not r[1]]
    print('\n%d checks, %d failed' % (len(RESULTS), len(fails)))
    for name, _, actual, expected, extra in fails:
        print('  FAIL %s: expected %r got %r %s' % (name, expected, actual, extra))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
