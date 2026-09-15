#!/usr/bin/env python3
"""Re-run EDB batch map for missing chars with fixed regex + folder logic.

Fix 1: regex `([\\d-]+)` missed folders like `4001-ZC` (letters) -> all
       chars with ID > 4000 were wrongly marked 'missing'.
Fix 2: download folder for ID > 4000 is '4001-ZC', not '4001-5000'.
"""
import re, json, os, sys, time
import urllib.request, urllib.parse
import concurrent.futures
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)



HDRS = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0'}

def folder_for(idv):
    if idv > 4000:
        return '4001-ZC'
    lo = ((idv - 1) // 1000) * 1000 + 1
    hi = lo + 999
    return f'{lo:04d}-{hi:04d}'

def fetch_id(ch):
    data = urllib.parse.urlencode({'searchMethod': 'direct', 'searchCriteria': ch, 'submit': ''}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request('https://www.edbchinese.hk/lexlist_ch/result.jsp', data=data, headers=HDRS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                txt = resp.read().decode('utf-8', 'replace')
            m = re.search(r'stkdemo_js/([^/"\']+)/(\d+)\.html', txt)
            return ch, (int(m.group(2)) if m else None), None
        except Exception as e:
            if attempt == 2:
                return ch, None, str(e)[:50]
            time.sleep(0.8)

def dl_js(ch, idv):
    fn = fwpath('edb_strokes', '{idv:04d}.js')
    if os.path.exists(fn) and os.path.getsize(fn) > 100:
        return idv, 'cached'
    url = f'https://www.edbchinese.hk/EmbziciwebRes/stkdemo_js/{folder_for(idv)}/{idv:04d}.js'
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                b = resp.read()
            if len(b) < 100:
                return idv, f'empty:{len(b)}'
            open(fn, 'wb').write(b)
            return idv, 'ok'
        except Exception as e:
            if attempt == 2:
                return idv, f'err:{str(e)[:40]}'
            time.sleep(0.6)

def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'map'
    d = json.load(open(wpath('edb_id_map.json')))
    mapping, missing, errors = d['mapping'], d['missing'], d.get('errors', [])

    if stage in ('map', 'all'):
        todo = [c for c in missing if c not in mapping]
        print(f'to map: {len(todo)}', flush=True)
        new_map, still_missing, errs = {}, [], []
        if todo:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                futs = {ex.submit(fetch_id, c): c for c in todo}
                n = 0
                for fut in concurrent.futures.as_completed(futs):
                    ch, idv, err = fut.result()
                    n += 1
                    if n % 100 == 0:
                        print(f'  mapped {n}/{len(todo)}...', flush=True)
                    if err:
                        errs.append((ch, err))
                    elif idv is not None:
                        new_map[ch] = idv
                    else:
                        still_missing.append(ch)
        mapping.update(new_map)
        missing = [c for c in missing if c not in new_map]
        final = {'mapping': mapping, 'missing': missing, 'errors': errors + errs}
        json.dump(final, open(wpath('edb_id_map.json'), 'w'), ensure_ascii=False)
        print(f'newly mapped: {len(new_map)}, still missing: {len(missing)}, errors: {len(errs)}', flush=True)

    if stage in ('dl', 'all'):
        todo = [(ch, idv) for ch, idv in mapping.items()
                if not (os.path.exists(fwpath('edb_strokes', '{idv:04d}.js'))
                        and os.path.getsize(fwpath('edb_strokes', '{idv:04d}.js')) > 100)]
        print(f'to download: {len(todo)}', flush=True)
        ok = 0
        for ch, idv in todo:
            _, st = dl_js(ch, idv)
            if st in ('ok', 'cached'):
                ok += 1
            else:
                print(f'  DL fail {ch} id={idv} {st}', flush=True)
        print(f'downloaded: {ok}/{len(todo)}', flush=True)

if __name__ == '__main__':
    main()