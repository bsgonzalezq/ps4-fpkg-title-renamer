#!/usr/bin/env python3
"""Rename PS4 pkgs to <ID>_base / _patch / _<DLC title>_dlc .pkg (type read from param.sfo),
move loose pkgs into their game folder, and replace title IDs (CUSA12345, ...) with game titles.

Usage:
  ps4_rename.py [PATH]              dry run in PATH (default: current directory)
  ps4_rename.py [PATH] --apply      perform the renames (writes rename_undo.log)
  ps4_rename.py [PATH] --undo       revert renames recorded in rename_undo.log
  ps4_rename.py [PATH] --build-db   create/update the db from *.pkg files

--build-db looks up an English name online (English Wikipedia, then Wikidata)
for any title in Japanese/Korean/Chinese and stores it in the db.

IDs missing from the db are added automatically (as --build-db) before renaming.

Logs are kept in the script's folder: every rename/undo run writes
rename_results_<action>_<timestamp>.log (CHANGED, NOT CHANGED + reason, ERRORS),
and --apply records renames in rename_undo.log for --undo. Only the 5 newest results
logs are kept; older ones are deleted automatically (rename_undo.log is never deleted).
  ps4_rename.py [PATH] --clean-logs delete rename_results_*.log (keeps rename_undo.log)

The script keeps itself, its db (ps4_titles.db) and its logs in a folder named
ps4-title-renamer; run from anywhere else, it creates ./ps4-title-renamer and moves there.

DB format (plain text, one per line, '#' comments):  ID|Title|Region
"""
import argparse, json, os, re, shutil, struct, subprocess, sys, time, unicodedata
import urllib.error, urllib.parse, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.realpath(__file__))   # real script folder, even when run via a symlink
UNDO_LOG = os.path.join(HERE, 'rename_undo.log')
DB_FILE = os.path.join(HERE, 'ps4_titles.db')
TOOL_DIR = 'ps4-title-renamer'   # folder the script (with its db and logs) always lives in
MAX_LOGS = 5                     # results logs kept in the script folder; older ones are rotated out
ID_RE = re.compile(r'(?<![A-Z])([A-Z]{4}\d{5})(?!\d)')
SKIP = {'System Volume Information', '$RECYCLE.BIN', '.Trash-1000', '.git', 'ps4-title-renamer'}
REGIONS = {'UP': 'USA', 'EP': 'EUR', 'JP': 'JPN', 'HP': 'ASIA', 'KP': 'KOR'}
# chars not allowed on exFAT/NTFS
BAD = str.maketrans({':': ' - ', '/': '-', '\\': '-', '*': '', '?': '', '"': "'",
                     '<': '', '>': '', '|': '-', '・': '-', '™': '', '®': '', '©': ''})


def load_db(path):
    db = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            gid, title, region = (p.strip() for p in line.split('|', 2))
            db[gid.upper()] = (title, region)
    return db


def read_sfo(pkg):
    """Return (content_id, {key: value}) from a PS4 PKG's param.sfo, or None."""
    with open(pkg, 'rb') as f:
        h = f.read(0x100)
        if h[:4] != b'\x7fCNT':
            return None
        count, = struct.unpack('>I', h[0x10:0x14])
        table, = struct.unpack('>I', h[0x18:0x1C])
        cid = h[0x40:0x64].decode('ascii', 'replace')
        f.seek(table)
        entries = f.read(count * 32)
        for i in range(count):
            eid, _, _, _, off, size = struct.unpack('>6I', entries[i * 32:i * 32 + 24])
            if eid != 0x1000:  # param.sfo
                continue
            f.seek(off)
            d = f.read(size)
            keys, data, n = struct.unpack('<III', d[8:20])
            out = {}
            for j in range(n):
                ko, fmt, ln, _, do = struct.unpack('<HHIII', d[20 + j * 16:36 + j * 16])
                k = d[keys + ko:d.index(b'\0', keys + ko)].decode()
                v = d[data + do:data + do + ln]
                out[k] = struct.unpack('<I', v[:4])[0] if fmt == 0x0404 else v.rstrip(b'\0').decode('utf-8', 'replace')
            return cid, out
    return None


FOREIGN = re.compile(r'[぀-ヺー-ヿ㐀-䶿一-鿿가-힯ᄀ-ᇿ㄰-㆏]')
SEGMENT = re.compile(r'[぀-ヺー-ヿ㐀-䶿一-鿿가-힯ᄀ-ᇿ㄰-㆏]'
                     r'[぀-ヺー-ヿ㐀-䶿一-鿿가-힯ᄀ-ᇿ㄰-㆏\s]*')
USER_AGENT = 'ps4_rename/1.0 (PS4 PKG title lookup; python-urllib)'
_last_request = [0.0]


def is_foreign(title):
    return bool(FOREIGN.search(title))


def http_json(url, params):
    """GET a Wikimedia API as JSON, max 1 request/sec, retrying on rate limits."""
    for attempt in range(4):
        wait = 1.5 - (time.monotonic() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        _last_request[0] = time.monotonic()
        req = urllib.request.Request(url + '?' + urllib.parse.urlencode(params),
                                     headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 3:
                raise
            time.sleep(int(e.headers.get('Retry-After') or 0) or 5 * (attempt + 1))
        except (urllib.error.URLError, OSError):
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))  # transient network error
    return {}


def search_english(query):
    """Find the English name of a game from its Japanese/Korean/Chinese name, or None."""
    lang = 'ko' if re.search(r'[가-힯]', query) else 'ja'
    try:
        # English Wikipedia articles usually quote the original-language title
        r = http_json('https://en.wikipedia.org/w/api.php', {
            'action': 'query', 'generator': 'search', 'gsrsearch': query, 'gsrlimit': 5,
            'prop': 'description', 'format': 'json', 'formatversion': 2})
        pages = sorted(r.get('query', {}).get('pages', []), key=lambda p: p.get('index', 99))
        for p in pages:
            if 'game' in p.get('description', '').lower():
                return p['title']
        # Wikidata: search the native-language label, return the English label
        r = http_json('https://www.wikidata.org/w/api.php', {
            'action': 'wbsearchentities', 'search': query, 'language': lang,
            'uselang': 'en', 'type': 'item', 'limit': 5, 'format': 'json'})
        for item in r.get('search', []):
            label = item.get('label', '')
            if 'game' in item.get('description', '').lower() and label and not is_foreign(label):
                return label
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f'    lookup failed for "{query}": {e}', file=sys.stderr)
    return None


def translate_title(title):
    """Return an English version of a non-English title (looked up online), or None."""
    t = unicodedata.normalize('NFKC', title).replace('・', ' ').replace('~', ' ')
    t = re.sub(r'\s+', ' ', t).strip()
    segments = [s.strip() for s in SEGMENT.findall(t)]
    latin = [s.strip() for s in SEGMENT.split(t) if s.strip()]

    def with_extras(name):
        # keep parts of the original that were already English (e.g. "Rev.2016", "Ψ")
        key = re.sub(r'\W', '', name).lower()
        extra = [s for s in latin if re.sub(r'\W', '', s).lower() not in key]
        return ' '.join([name] + extra)

    name = search_english(t)
    if name:
        return with_extras(name)
    # whole title not found: translate each non-English part on its own,
    # falling back to single words when a multi-word part isn't found
    parts = []
    for seg in sorted(segments, key=len, reverse=True):
        hit = search_english(seg) if seg != t else None
        if not hit and ' ' in seg:
            hits = [search_english(w) for w in sorted(seg.split(), key=len, reverse=True)]
            hit = next((h for h in hits if h), None)
        if hit:
            parts.append(hit)
    if not parts:
        return None
    # the longest segment is usually the game name; other hits add to it if new
    name = parts[0]
    for p in parts[1:]:
        if p.lower() not in name.lower():
            name += ' ' + p
    return with_extras(name)


def write_db(db, path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# PS4 title DB: ID|Title|Region  (USA/EUR/JPN/ASIA, HB = homebrew)\n')
        for gid in sorted(db):
            f.write(f'{gid}|{db[gid][0]}|{db[gid][1]}\n')


def translate_db(db, offline):
    """Replace non-English titles in db with English names found online."""
    foreign = [g for g in sorted(db) if is_foreign(db[g][0])]
    if not foreign:
        return
    if offline:
        print(f'{len(foreign)} non-English title(s) left as-is (--offline)')
        return
    print(f'Looking up English names for {len(foreign)} title(s)...')
    for gid in foreign:
        title, region = db[gid]
        en = translate_title(title)
        if en:
            db[gid] = (en, region)
            print(f'  ~ {gid}: {title}  ->  {en}')
        else:
            print(f'  ! {gid}: no English name found, keeping "{title}"')


def build_db(root, path, rebuild=False, offline=False):
    db = load_db(path) if os.path.exists(path) and not rebuild else {}
    found = {}  # gid -> (priority, title, content_id); base game/app beats patch
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            if not fn.lower().endswith('.pkg'):
                continue
            try:
                r = read_sfo(os.path.join(dp, fn))
            except (OSError, ValueError, struct.error):
                r = None
            # base games/apps; patches carry the game title too, used when no base pkg is present
            prio = {'gd': 0, 'gde': 0, 'gp': 1}.get(r[1].get('CATEGORY')) if r else None
            if prio is None:
                continue
            cid, sfo = r
            gid = sfo.get('TITLE_ID', cid[7:16])
            if gid in db:
                continue  # keep existing (possibly hand-edited) entries
            title = sfo.get('TITLE_01') or sfo.get('TITLE', gid)  # prefer English title
            if gid not in found or prio < found[gid][0]:
                found[gid] = (prio, title, cid)
    for gid, (_, title, cid) in sorted(found.items()):
        region = REGIONS.get(cid[:2], 'HB' if cid[:1] in 'IE' else '??')
        db[gid] = (title, region)
        print(f'  + {gid}|{title}|{region}')
    translate_db(db, offline)
    write_db(db, path)
    print(f'{len(found)} new entries, {len(db)} total -> {path}')


def missing_ids(root, db):
    """Title IDs of base/patch pkgs in PATH that aren't in db yet (the ones --build-db can add)."""
    ids = set()
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            if fn.lower().endswith('.pkg'):
                info = pkg_info(os.path.join(dp, fn))
                if info and info[1] != 'dlc':
                    ids.add(info[0])
    return ids - set(db)


TAG_RE = re.compile(r'(\s*)\[([A-Z]{4}\d{5})\]')                 # "[CUSA00900]" as added by --keep-id
BARE_ID_RE = re.compile(r'(?<![A-Z\[])([A-Z]{4}\d{5})(?![\d\]])')


def _alnum(s):
    return re.sub(r'[\W_]', '', unicodedata.normalize('NFKC', s)).lower()


def safe_title(db, gid):
    return re.sub(r'\s+', ' ', db[gid][0].translate(BAD)).strip()


def new_name(name, db, keep_id, unknown):
    def tag(m):
        # "Title [ID]" from an earlier run: keep it (--keep-id) or drop the tag,
        # instead of replacing the ID again ("Title [Title]")
        gid = m.group(2)
        if gid not in db:
            unknown.add(gid)
            return m.group(0)
        t = safe_title(db, gid)
        if _alnum(t) in _alnum(name.replace(m.group(0), '')):
            return m.group(0) if keep_id else ''
        return f'{m.group(1)}{t} [{gid}]' if keep_id else f'{m.group(1)}{t}'

    def sub(m):
        gid = m.group(1)
        if gid not in db:
            unknown.add(gid)
            return gid
        t = safe_title(db, gid)
        return f'{t} [{gid}]' if keep_id else t
    return BARE_ID_RE.sub(sub, TAG_RE.sub(tag, name)).rstrip(' .')


PKG_KINDS = {'gd': 'base', 'gde': 'base', 'gp': 'patch', 'ac': 'dlc'}   # param.sfo CATEGORY


def strip_prefix(text, prefix):
    """Remove prefix from text, comparing letters/digits only ("ELDEN RING™ X" - "ELDEN RING" = "X")."""
    key = _alnum(prefix)
    if not key or not _alnum(text).startswith(key):
        return text
    count, i = 0, 0
    while i < len(text) and count < len(key):
        count += len(_alnum(text[i]))
        i += 1
    return text[i:]


def pkg_info(path):
    """Return (title_id, kind, dlc_title) from a pkg's param.sfo, or None if unreadable/unknown."""
    try:
        r = read_sfo(path)
    except (OSError, ValueError, struct.error):
        return None
    if not r:
        return None
    cid, sfo = r
    kind = PKG_KINDS.get(sfo.get('CATEGORY'))
    if not kind:
        return None
    gid = sfo.get('TITLE_ID') or cid[7:16]
    dlc = (sfo.get('TITLE_01') or sfo.get('TITLE') or cid[20:]) if kind == 'dlc' else ''
    return gid, kind, dlc


def pkg_name(info, db, keep_id, unknown):
    """File name in the <TITLE_ID>_base / _patch / _<DLC title>_dlc .pkg scheme, with the ID
    then replaced by the game title as for any other name."""
    gid, kind, dlc = info
    if kind != 'dlc':
        return new_name(f'{gid}_{kind}.pkg', db, keep_id, unknown)
    dlc = re.sub(r'\s+', ' ', dlc.translate(BAD)).strip()
    if gid in db:
        # drop the game title from the DLC title, the name already starts with it
        dlc = strip_prefix(dlc, safe_title(db, gid)).strip(' -–_.') or dlc
    return new_name(f'{gid}_{dlc}_dlc.pkg', db, keep_id, unknown)


class ResultLog:
    """Collects changed / not changed / error entries and writes them to a log file."""

    def __init__(self, path, action):
        self.path, self.action = path, action
        self.changed, self.unchanged, self.errors = [], [], []

    def change(self, src, dst):
        self.changed.append(f'{src}  ->  {dst}')

    def keep(self, path, reason):
        self.unchanged.append(f'{path}  ({reason})')

    def error(self, path, reason):
        self.errors.append(f'{path}  ({reason})')
        print(f'ERROR: {path} ({reason})', file=sys.stderr)

    def write(self):
        sections = [('CHANGED', self.changed), ('NOT CHANGED', self.unchanged), ('ERRORS', self.errors)]
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(f'# ps4_rename.py {self.action}  {datetime.now():%Y-%m-%d %H:%M:%S}\n')
            f.write('# ' + ', '.join(f'{t.lower()}: {len(l)}' for t, l in sections) + '\n')
            for title, lines in sections:
                f.write(f'\n=== {title} ({len(lines)}) ===\n')
                f.writelines(l + '\n' for l in lines)
        print(f'\nChanged: {len(self.changed)}, not changed: {len(self.unchanged)}, '
              f'errors: {len(self.errors)}\nLog: {self.path}')


def game_dir(root, gid, db, keep_id, planned):
    """Folder in root for a loose pkg: an existing folder for the ID, else a new one."""
    if gid in planned:  # already being created in this run
        return planned[gid], False
    wanted = new_name(gid, db, keep_id, set())
    names = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)) and d not in SKIP]
    for d in names:  # "CUSA00900", "Bloodborne [CUSA00900]", ...
        if gid in ID_RE.findall(d):
            return d, False
    if wanted in names:  # "Bloodborne" (renamed without --keep-id)
        return wanted, False
    planned[gid] = wanted
    return wanted, True


def rename_all(root, db, keep_id, apply, undo_log, log):
    unknown, done, planned = set(), [], {}
    own = {'ps4_titles.db', 'ps4_rename.py', os.path.basename(undo_log)}
    # bottom-up so files are renamed before their parent directories
    for dp, dns, fns in os.walk(root, topdown=False):
        rel = os.path.relpath(dp, root)
        if any(part in SKIP for part in rel.split(os.sep)):
            continue
        for name in fns + dns:
            if name in SKIP or name in own or name.startswith(('rename_results_', 'rename_undo.log')):
                continue
            relpath = os.path.normpath(os.path.join(rel, name))
            missing = set()
            info = pkg_info(os.path.join(dp, name)) if name in fns and name.lower().endswith('.pkg') else None
            if info:
                # PS4 pkg: name it from its param.sfo, <ID>_base / _patch / _<DLC>_dlc .pkg
                nn = pkg_name(info, db, keep_id, missing)
                reason = f'ID {info[0]} (from pkg) not in db' if missing else 'already named'
            elif ID_RE.search(name):
                nn = new_name(name, db, keep_id, missing)
                reason = ('ID not in db: ' + ', '.join(sorted(missing))) if missing else 'already named'
            else:
                nn, reason = name, 'no game ID in name'
            unknown |= missing
            # a pkg sitting directly in root goes into its game's folder
            subdir, create = game_dir(root, info[0], db, keep_id, planned) if info and dp == root else ('', False)
            if nn == name and not subdir:
                log.keep(relpath, reason)
                continue
            src, dst = os.path.join(dp, name), os.path.join(dp, subdir, nn)
            target = os.path.join(subdir, nn) if subdir else nn
            if os.path.exists(dst):
                log.error(relpath, f'target already exists: {target}')
                continue
            print(f'{relpath}  ->  {target}' + (f'   (new folder "{subdir}")' if create else ''))
            if apply:
                try:
                    if create:
                        os.mkdir(os.path.join(root, subdir))
                        done.append(('MKDIR', os.path.join(root, subdir)))
                    os.rename(src, dst)
                except OSError as e:
                    log.error(relpath, f'rename to "{target}" failed: {e.strerror}')
                    continue
                done.append((src, dst))
            log.change(relpath, target + (f'  (new folder "{subdir}")' if create else ''))
    if apply and done:
        with open(undo_log, 'a', encoding='utf-8') as f:
            f.write(f'# {datetime.now().isoformat()}\n')
            for s, d in done:
                f.write(f'{s}\t{d}\n')
    if unknown:
        print('IDs not in db (no base/patch pkg to read a title from; add them to the db manually):',
              ', '.join(sorted(unknown)))
    if not apply:
        print('Dry run only. Re-run with --apply to rename.')


def _under(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def migrate_undo_log(root):
    """Move a rename_undo.log left in PATH by older versions into the script folder."""
    old = os.path.join(root, 'rename_undo.log')
    if os.path.abspath(old) == UNDO_LOG or not os.path.isfile(old):
        return
    with open(old, encoding='utf-8') as f:
        data = f.read()
    with open(UNDO_LOG, 'a', encoding='utf-8') as f:
        f.write(f'# migrated from {old}\n' + data + ('' if data.endswith('\n') else '\n'))
    os.remove(old)
    print(f'Moved undo history from {old} to {UNDO_LOG}\n')


def undo(root, undo_log, log):
    if not os.path.exists(undo_log):
        sys.exit(f'No undo log: {undo_log}')
    with open(undo_log, encoding='utf-8') as f:
        pairs = [l.rstrip('\n').split('\t') for l in f if l.strip() and not l.startswith('#')]
    # the log is shared by every PATH the script was run on: only undo entries under this one
    mine = [p for p in pairs if _under(p[1], root)]
    others = [p for p in pairs if not _under(p[1], root)]
    if not mine:
        sys.exit(f'Nothing to undo under {root} in {undo_log}')
    failed = []
    # reverse order: parents renamed last are restored first
    for src, dst in reversed(mine):
        if src == 'MKDIR':  # folder created for a loose pkg: remove it once empty again
            try:
                os.rmdir(dst)
                print(f'removed folder {dst}')
                log.change(dst, '(folder removed)')
            except OSError as e:
                log.keep(dst, f'created folder not removed: {e.strerror}')
            continue
        if not os.path.exists(dst):
            log.error(dst, 'renamed item no longer exists')
            failed.append((src, dst))
        elif os.path.exists(src):
            log.keep(dst, f'original name already in use: {src}')
        else:
            try:
                os.rename(dst, src)
            except OSError as e:
                log.error(dst, f'restore failed: {e.strerror}')
                failed.append((src, dst))
                continue
            print(f'{dst} -> {src}')
            log.change(dst, src)
    # keep entries for other folders (and failed ones, to retry); archive the rest
    with open(undo_log + '.done', 'a', encoding='utf-8') as f:
        f.write(f'# undone {datetime.now().isoformat()} under {root}\n')
        f.writelines(f'{s}\t{d}\n' for s, d in mine)
    keep = others + list(reversed(failed))
    if keep:
        with open(undo_log, 'w', encoding='utf-8') as f:
            f.writelines(f'{s}\t{d}\n' for s, d in keep)
    else:
        os.remove(undo_log)


def rotate_logs():
    """Keep only the MAX_LOGS newest rename_results_*.log in the script folder (never rename_undo.log)."""
    logs = [os.path.join(HERE, fn) for fn in os.listdir(HERE)
            if fn.startswith('rename_results_') and fn.endswith('.log')]
    logs.sort(key=lambda p: (os.path.getmtime(p), p), reverse=True)
    for p in logs[MAX_LOGS:]:
        try:
            os.remove(p)
            print(f'Rotated out old log {os.path.basename(p)}')
        except OSError as e:
            print(f'could not delete old log {p}: {e.strerror}', file=sys.stderr)


def clean_logs(root):
    """Delete results logs (script folder, plus old ones left in PATH); never rename_undo.log."""
    found = set()
    for d in {HERE, root}:
        for fn in os.listdir(d):
            if fn.startswith('rename_results_') and fn.endswith('.log'):
                found.add(os.path.join(d, fn))
    for p in sorted(found):
        try:
            os.remove(p)
            print(f'deleted {p}')
        except OSError as e:
            print(f'could not delete {p}: {e.strerror}', file=sys.stderr)
    print(f'{len(found)} log file(s) deleted; {UNDO_LOG} kept' if found else 'No results logs to delete.')


def merge_db(src, dst):
    """Add entries of db file src that dst lacks (dst entries win), write dst, delete src."""
    db = load_db(dst) if os.path.exists(dst) else {}
    added = {g: v for g, v in load_db(src).items() if g not in db}
    db.update(added)
    write_db(db, dst)
    os.remove(src)
    return len(added)


def relocate():
    """Keep the script in a folder named ps4-title-renamer: if it isn't in one, create
    ./ps4-title-renamer under the current directory, move the script plus its db and logs
    there, and re-run from the new location. Returns False if it stayed where it is."""
    if os.path.basename(HERE) == TOOL_DIR:
        return False
    if os.path.isdir(os.path.join(HERE, '.git')):
        print(f'Note: script folder "{HERE}" is a git clone, not moving it into {TOOL_DIR}/\n')
        return False
    cwd = os.getcwd()
    target = cwd if os.path.basename(cwd) == TOOL_DIR else os.path.join(cwd, TOOL_DIR)
    script = os.path.join(target, 'ps4_rename.py')
    if os.path.exists(script):
        print(f'Note: {script} already exists, not replacing it; running from {HERE}\n')
        return False
    os.makedirs(target, exist_ok=True)
    print(f'Moving script to {target}/')
    shutil.move(os.path.realpath(__file__), script)
    # bring the db and logs along
    for fn in sorted(os.listdir(HERE)):
        src, dst = os.path.join(HERE, fn), os.path.join(target, fn)
        if fn == 'ps4_titles.db':
            if os.path.exists(dst):
                print(f'  merged {merge_db(src, dst)} db entries into {dst}')
            else:
                shutil.move(src, dst)
                print(f'  moved {fn}')
        elif fn in ('rename_undo.log', 'rename_undo.log.done'):
            with open(src, encoding='utf-8') as f, open(dst, 'a', encoding='utf-8') as out:
                out.write(f.read())
            os.remove(src)
            print(f'  moved {fn}')
        elif fn.startswith('rename_results_') and fn.endswith('.log') and not os.path.exists(dst):
            shutil.move(src, dst)
    try:
        os.rmdir(HERE)  # old folder, only if nothing else is left in it
        print(f'  removed empty folder {HERE}')
    except OSError:
        pass
    print(flush=True)
    sys.exit(subprocess.call([sys.executable, script] + sys.argv[1:]))


def migrate_db(root, db_path):
    """Merge a ps4_titles.db left in PATH by older versions into the db next to the script."""
    old = os.path.join(root, 'ps4_titles.db')
    if os.path.isfile(old) and os.path.abspath(old) != os.path.abspath(db_path):
        n = merge_db(old, db_path)
        print(f'Merged {old} into {db_path} ({n} new entries)\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', nargs='?', default='.', metavar='PATH',
                    help='directory to process (default: current directory)')
    ap.add_argument('--apply', action='store_true', help='perform the renames (default is a dry run)')
    ap.add_argument('--undo', action='store_true', help='revert renames under PATH recorded in rename_undo.log')
    ap.add_argument('--keep-id', action='store_true', help='keep the ID after the title, e.g. "Bloodborne [CUSA00900]"')
    ap.add_argument('--build-db', action='store_true', help='add games to the db from param.sfo inside *.pkg files')
    ap.add_argument('--rebuild', action='store_true', help='with --build-db: start a fresh db (drops old entries)')
    ap.add_argument('--offline', action='store_true', help="don't look up English names online when building the db")
    ap.add_argument('--no-auto-db', action='store_true',
                    help="don't run --build-db automatically when IDs are missing from the db")
    ap.add_argument('--db', metavar='FILE', help='db file (default: ps4_titles.db next to the script)')
    ap.add_argument('--log', metavar='FILE',
                    help='results log path (default: rename_results_<action>_<timestamp>.log in the script folder)')
    ap.add_argument('--clean-logs', action='store_true',
                    help='delete rename_results_*.log files (rename_undo.log is kept) and exit')
    a = ap.parse_args()
    a.root = os.path.abspath(a.root)
    if not os.path.isdir(a.root):
        ap.error(f'not a directory: {a.root}')
    relocate()
    if not a.db:
        a.db = DB_FILE
        migrate_db(a.root, a.db)
    print(f'Directory: {a.root}\nScript folder: {HERE}\nDB: {a.db}\n')
    undo_log = UNDO_LOG
    if a.clean_logs:
        clean_logs(a.root)
        return
    if a.build_db:
        build_db(a.root, a.db, a.rebuild, a.offline)
        return
    migrate_undo_log(a.root)
    action = 'undo' if a.undo else 'apply' if a.apply else 'dryrun'
    log_path = a.log
    if not log_path:
        base = os.path.join(HERE, f'rename_results_{action}_{datetime.now():%Y%m%d_%H%M%S}')
        log_path, n = base + '.log', 1
        while os.path.exists(log_path):  # several runs in the same second
            n += 1
            log_path = f'{base}_{n}.log'
    log = ResultLog(log_path, action)
    try:
        if a.undo:
            undo(a.root, undo_log, log)
        else:
            db = load_db(a.db) if os.path.exists(a.db) else {}
            new = missing_ids(a.root, db)
            if not a.no_auto_db and (new or not db):
                # new games found: add them to the db first (same as --build-db)
                print(f'{len(new)} ID(s) not in db: {", ".join(sorted(new))}\nRunning --build-db...')
                build_db(a.root, a.db, offline=a.offline)
                db = load_db(a.db)
                print()
            rename_all(a.root, db, a.keep_id, a.apply, undo_log, log)
    finally:
        log.write()
        rotate_logs()


if __name__ == '__main__':
    main()
