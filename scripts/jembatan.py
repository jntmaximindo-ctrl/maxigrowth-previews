#!/usr/bin/env python3
"""Jembatan Claude ⇄ repo lewat Google Drive (supaya pemilik tidak perlu menyentuh GitHub).

Claude menaruh file perintah (JSON) di Drive "07 Klinik-Bus/08 Perintah Claude (repo)".
Orkestrator mengunduhnya ke folder lokal lalu:
  terapkan <folder>   → menulis/menghapus file repo, mencatat variable & workflow yang diminta
  laporan             → menulis laporan kondisi robot (run terakhir, error, PR, variable, antrean Sheet)

Format perintah (satu file .json/.txt, isi JSON):
{
  "id": "2026-09-30-01",                 # bebas, untuk laporan
  "pesan": "commit message",
  "tulis": {"path/di/repo": "isi file teks", ...},
  "hapus": ["path/di/repo", ...],
  "variabel": {"RAKIT_ENGINE": "codex"},
  "jalankan": [{"workflow": "orkestrator.yml", "input": {}}]
}
Keluaran untuk langkah workflow berikutnya: /tmp/jb/vars.tsv, /tmp/jb/runs.jsonl, /tmp/jb/pesan.txt, /tmp/jb/hasil.md
"""
import datetime, json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path("/tmp/jb")
DILARANG = (".git/",)  # jalur yang tidak boleh disentuh
VAR_BOLEH = {"RAKIT_ENGINE", "RISET_ENGINE", "SHEET_ID"}  # variable non-rahasia yang boleh diubah Claude


def aman(p):
    p = p.replace("\\", "/").lstrip("/")
    full = (ROOT / p).resolve()
    if not str(full).startswith(str(ROOT)) or any(p.startswith(d) for d in DILARANG) or ".." in p.split("/"):
        raise ValueError(f"jalur ditolak: {p}")
    return p, full


def terapkan(folder):
    OUT.mkdir(exist_ok=True)
    vars_, runs, pesan, hasil = [], [], [], []
    for f in sorted(pathlib.Path(folder).glob("*")):
        if not f.is_file():
            continue
        try:
            raw = f.read_text(encoding="utf-8-sig").strip()
            if raw.startswith("```"):
                raw = raw.strip("`").split("\n", 1)[1]
            cmd = json.loads(raw)
            ok = []
            for p, isi in (cmd.get("tulis") or {}).items():
                p, full = aman(p)
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_text(isi, encoding="utf-8")
                ok.append(f"tulis {p} ({len(isi)} B)")
            for p in cmd.get("hapus") or []:
                p, full = aman(p)
                if full.is_file():
                    full.unlink(); ok.append(f"hapus {p}")
            for k, v in (cmd.get("variabel") or {}).items():
                if k not in VAR_BOLEH:
                    raise ValueError(f"variable {k} tidak diizinkan")
                vars_.append(f"{k}\t{v}"); ok.append(f"variable {k}={v}")
            for r in cmd.get("jalankan") or []:
                runs.append(json.dumps(r)); ok.append(f"jalankan {r.get('workflow')}")
            pesan.append(cmd.get("pesan") or cmd.get("id") or f.name)
            hasil.append(f"- ✅ {f.name} ({cmd.get('id','')}): " + "; ".join(ok))
        except Exception as e:  # satu perintah gagal tidak menghentikan yang lain
            hasil.append(f"- ❌ {f.name}: {e}")
    (OUT / "vars.tsv").write_text("\n".join(vars_))
    (OUT / "runs.jsonl").write_text("\n".join(runs))
    (OUT / "pesan.txt").write_text("claude: " + " | ".join(pesan)[:300] if pesan else "")
    (OUT / "hasil.md").write_text("\n".join(hasil))
    print("\n".join(hasil) or "tidak ada perintah")


def sh(*a):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=60).stdout
    except Exception as e:
        return f"(gagal: {e})"


def laporan():
    now = datetime.datetime.utcnow()
    wib = (now + datetime.timedelta(hours=7)).strftime("%Y-%m-%d %H:%M WIB")
    L = [f"# Laporan robot — {wib}", ""]
    if (OUT / "hasil.md").exists() and (OUT / "hasil.md").read_text().strip():
        L += ["## Perintah Claude yang diterapkan run ini", (OUT / "hasil.md").read_text(), ""]
    try:
        k = (ROOT / "data" / "kontrol.json").read_text()
    except Exception:
        k = "(tidak ada)"
    L += ["## Saklar (data/kontrol.json)", "```", k.strip(), "```", ""]
    L += ["## Variable", "```", sh("gh", "variable", "list").strip(), "```", ""]
    runs = json.loads(sh("gh", "run", "list", "--limit", "25", "--json",
                         "databaseId,workflowName,status,conclusion,createdAt,displayTitle") or "[]")
    L += ["## 25 run terakhir", "| waktu (UTC) | workflow | hasil | judul |", "|---|---|---|---|"]
    for r in runs:
        L.append(f"| {r['createdAt'][5:16]} | {r['workflowName']} | {r.get('conclusion') or r['status']} | {r['displayTitle'][:60]} |")
    batas = (now - datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    gagal = [r for r in runs if r.get("conclusion") == "failure" and r["createdAt"] > batas][:4]
    if gagal:
        L += ["", "## Log error (run gagal 3 jam terakhir)"]
        for r in gagal:
            log = sh("gh", "run", "view", str(r["databaseId"]), "--log-failed")
            L += [f"### {r['workflowName']} #{r['databaseId']}", "```", "\n".join(log.strip().splitlines()[-40:]), "```"]
    prs = json.loads(sh("gh", "pr", "list", "--state", "open", "--limit", "30", "--json",
                        "number,title,createdAt,headRefName,comments,commits") or "[]")
    L += ["", "## PR terbuka", "| # | judul | dibuat | commit | komentar terakhir |", "|---|---|---|---|---|"]
    for p in prs:
        last = (p.get("comments") or [{}])[-1].get("body", "")[:120].replace("\n", " ").replace("|", "/")
        L.append(f"| {p['number']} | {p['title'][:50]} | {p['createdAt'][5:16]} | {len(p.get('commits') or [])} | {last} |")
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from sheet import svc, read
        _, _, recs = read(svc())
        from collections import Counter
        c = Counter(str(r.get("Status", "")).strip() or "(kosong)" for r in recs)
        L += ["", "## Antrean Sheet", ", ".join(f"{k}: {v}" for k, v in c.most_common())]
    except Exception as e:
        L += ["", f"## Antrean Sheet\n(gagal dibaca: {e})"]
    OUT.mkdir(exist_ok=True)
    (OUT / "laporan.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L)[:3000])


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    {"terapkan": terapkan, "laporan": laporan}[cmd](*a)
