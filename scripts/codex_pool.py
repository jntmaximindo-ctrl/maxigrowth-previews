#!/usr/bin/env python3
"""Codex pool: beberapa akun ChatGPT Plus (lewat PAT GitHub masing-masing) dipakai bergantian.

  pilih [HINDARI]   → cetak "ID SECRET" slot sehat pertama (kosong bila semua habis)
  pindai            → periksa PR codex/* terbuka; slot yang kena limit ditandai habis,
                      tugas dipindah ke slot lain di PR yang sama. Tulis /tmp/pool/aksi.tsv:
                      "<pr>\t<slot>\t<secret>\t<file-komentar>"
  status            → ringkasan slot (untuk laporan)
Status disimpan di data/codex-pool-state.json (di-commit orkestrator).
Setiap komentar @codex dari robot membawa penanda <!-- slot=X t=ISO -->.
"""
import datetime, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONF, STATE = ROOT / "data" / "codex-pool.json", ROOT / "data" / "codex-pool-state.json"
OUT = pathlib.Path("/tmp/pool")
JEDA_JAM = 5            # lama slot dianggap habis bila Codex tidak menyebut jam reset
DIAM_MENIT = 75         # Codex diam (tanpa balasan & tanpa commit) selama ini → pindah slot
MAKS_PANGGIL = 3        # total panggilan @codex per PR sebelum diserahkan ke Claude
LIMIT_RE = re.compile(r"usage limit|reached your codex usage|out of codex|rate limit", re.I)
GAGAL_RE = re.compile(r"couldn.t complete|environment setup failed|try again later", re.I)
MARK_RE = re.compile(r"<!-- slot=(\w+) t=([\dT:\-Z]+) -->")


def now():
    return datetime.datetime.utcnow().replace(microsecond=0)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s):
    return datetime.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")


def conf():
    return [s for s in json.loads(CONF.read_text())["slot"] if s.get("aktif", True)]


def state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save(st):
    STATE.write_text(json.dumps(st, indent=1, sort_keys=True))


def sehat(slot, st):
    h = st.get(slot["id"], {}).get("habis_sampai")
    return not h or parse(h) <= now()


def pilih(hindari=""):
    st = state()
    cand = [s for s in conf() if sehat(s, st)]
    pref = [s for s in cand if s["id"] != hindari] or cand
    print(f"{pref[0]['id']} {pref[0]['secret']}" if pref else "")


def gh(*a):
    return subprocess.run(("gh",) + a, capture_output=True, text=True).stdout


def pindai():
    OUT.mkdir(exist_ok=True)
    st, slots = state(), conf()
    by_id = {s["id"]: s for s in slots}
    prs = json.loads(gh("pr", "list", "--state", "open", "--limit", "60", "--json",
                        "number,headRefName,createdAt,comments,commits") or "[]")
    aksi, log = [], []
    for p in prs:
        if not p["headRefName"].startswith("codex/"):
            continue
        cs = p.get("comments") or []
        panggil = [(i, c) for i, c in enumerate(cs) if "@codex" in c.get("body", "") and "Kerjakan tugas" in c.get("body", "")
                   or MARK_RE.search(c.get("body", ""))]
        if not panggil:
            continue
        i, last = panggil[-1]
        m = MARK_RE.search(last["body"])
        slot, t = (m.group(1), parse(m.group(2))) if m else ("A", parse(last.get("createdAt") or p["createdAt"]))
        sesudah = cs[i + 1:]
        dari_codex = [c for c in sesudah if "codex" in (c.get("author", {}) or {}).get("login", "").lower()]
        balas = " ".join(c.get("body", "") for c in dari_codex)
        t_balas = parse(dari_codex[-1].get("createdAt") or iso(now())) if dari_codex else now()
        commit_baru = any(parse(c.get("committedDate") or c.get("authoredDate") or "1970-01-01T00:00:00") > t
                          for c in (p.get("commits") or []))
        alasan = None
        key = f"{p['number']}@{iso(t)}"
        baru = key not in st.setdefault("_diproses", {})
        if LIMIT_RE.search(balas):
            if baru and sehat({"id": slot}, st):  # tandai sekali per panggilan; jangan geser jam pulih yang sudah tercatat
                st.setdefault(slot, {})["habis_sampai"] = iso(max(now(), t_balas + datetime.timedelta(hours=JEDA_JAM)))
            alasan = "limit"
        elif GAGAL_RE.search(balas):
            if baru:
                st.setdefault(slot, {})["gagal_berturut"] = st.get(slot, {}).get("gagal_berturut", 0) + 1
            alasan = "gagal"
        elif not balas and not commit_baru and now() - t > datetime.timedelta(minutes=DIAM_MENIT):
            alasan = "diam"
        elif commit_baru:
            st.setdefault(slot, {})["gagal_berturut"] = 0
        if not alasan:
            continue
        st["_diproses"][key] = alasan
        if len(panggil) >= MAKS_PANGGIL:
            log.append(f"PR #{p['number']}: sudah {len(panggil)}x dipanggil ({alasan}) → serahkan ke Claude")
            aksi.append(f"{p['number']}\t-\t-\tbutuh-claude")
            continue
        # utamakan akun lain; akun yang sama boleh lagi bila sudah pulih (limit) atau alasannya bukan limit
        cand = [s for s in slots if sehat(s, st) and s["id"] != slot] or [s for s in slots if sehat(s, st)]
        if not cand:
            log.append(f"PR #{p['number']}: slot {slot} {alasan}, semua slot lain habis → tunggu")
            continue
        s = cand[0]
        body = re.sub(r"<!-- slot=\w+ t=[\dT:\-Z]+ -->\s*", "", last["body"]).strip()
        if "@codex" not in body:
            body = "@codex " + body
        f = OUT / f"pr{p['number']}.md"
        f.write_text(f"<!-- slot={s['id']} t={iso(now())} -->\n{body}\n\n(dipindah dari slot {slot}: {alasan})")
        aksi.append(f"{p['number']}\t{s['id']}\t{s['secret']}\t{f}")
        log.append(f"PR #{p['number']}: slot {slot} {alasan} → pindah ke slot {s['id']}")
    st["_diproses"] = dict(list(st.get("_diproses", {}).items())[-300:])
    save(st)
    (OUT / "aksi.tsv").write_text("".join(a + "\n" for a in aksi))
    print("\n".join(log) or "pool: tidak ada yang perlu dipindah")


def status():
    st = state()
    out = []
    for s in conf():
        x = st.get(s["id"], {})  # noqa
        kondisi = "SEHAT" if sehat(s, st) else f"HABIS s/d {x.get('habis_sampai')} UTC"
        out.append(f"- slot {s['id']} ({s['akun']}): {kondisi}; gagal berturut: {x.get('gagal_berturut', 0)}")
    print("\n".join(out))


if __name__ == "__main__":
    cmd, *a = sys.argv[1:] or ["status"]
    {"pilih": pilih, "pindai": pindai, "status": status}[cmd](*a)
