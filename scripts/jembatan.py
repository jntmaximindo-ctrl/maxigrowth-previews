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


def valid(p, isi):
    if p.endswith((".yml", ".yaml")):
        try:
            import yaml
        except ImportError:
            return
        yaml.safe_load(isi)
    elif p.endswith(".py"):
        compile(isi, p, "exec")
    elif p.endswith(".json"):
        json.loads(isi)


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
                valid(p, isi)  # sintaks salah → perintah ditolak utuh, repo tidak disentuh
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
    (OUT / "vars.tsv").write_text("".join(v + "\n" for v in vars_))
    (OUT / "runs.jsonl").write_text("".join(r + "\n" for r in runs))
    (OUT / "pesan.txt").write_text("claude: " + " | ".join(pesan)[:300] if pesan else "")
    (OUT / "hasil.md").write_text("\n".join(hasil))
    print("\n".join(hasil) or "tidak ada perintah")


def sh(*a):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=60).stdout
    except Exception as e:
        return f"(gagal: {e})"


def js(*a):
    try:
        return json.loads(sh(*a) or "[]")
    except Exception:
        return []


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
    runs = js("gh", "run", "list", "--limit", "25", "--json",
               "databaseId,workflowName,status,conclusion,createdAt,displayTitle")
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
    prs = js("gh", "pr", "list", "--state", "open", "--limit", "30", "--json",
              "number,title,createdAt,headRefName,comments,commits")
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
    # --- ALARM ---
    alarm = []  # (tingkat, pesan) tingkat: claude = Claude memperbaiki sendiri; manusia = butuh pemilik
    ork = [r for r in runs if r["workflowName"] == "orkestrator" and r.get("conclusion") in ("success", "failure")][:4]
    if len(ork) >= 2 and all(r["conclusion"] == "failure" for r in ork[:2]):
        alarm.append(("claude", "orkestrator gagal 2x berturut-turut"))
    for p in prs:
        if p["headRefName"].startswith("codex/") and p["createdAt"] < (now - datetime.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ"):
            alarm.append(("claude", f"PR #{p['number']} terbuka > 6 jam: {p['title'][:50]}"))
    pool = sh("python3", str(ROOT / "scripts" / "codex_pool.py"), "status")
    L += ["", "## Codex pool", pool.strip() or "(tidak terbaca)"]
    try:
        pst = json.loads((ROOT / "data" / "codex-pool-state.json").read_text())
        for sid, x in pst.items():
            if x.get("gagal_berturut", 0) >= 3:
                alarm.append(("manusia", f"Codex slot {sid} gagal {x['gagal_berturut']}x berturut-turut (bukan kuota) — kemungkinan environment/koneksi GitHub akun itu bermasalah"))
    except Exception:
        pass
    exp = sh("bash", "-c", "curl -sI -H \"Authorization: Bearer $GH_TOKEN\" https://api.github.com/repos/$GITHUB_REPOSITORY | grep -i token-expiration | cut -d' ' -f2-")
    if exp.strip():
        try:
            sisa = (datetime.datetime.strptime(exp.strip()[:19], "%Y-%m-%d %H:%M:%S") - now).days
            L += ["", f"## Token CLAUDE_PAT kedaluwarsa: {exp.strip()} (sisa {sisa} hari)"]
            if sisa <= 30:
                alarm.append(("manusia", f"Token CLAUDE_PAT kedaluwarsa dalam {sisa} hari — perlu diperpanjang"))
        except Exception:
            pass
    tingkat = "MERAH" if any(a[0] == "manusia" for a in alarm) else "KUNING" if alarm else "HIJAU"
    L.insert(1, f"STATUS: {tingkat}" + "".join(f"\n- [{a[0]}] {a[1]}" for a in alarm))
    (OUT / "alarm-manusia.md").write_text("\n".join(f"- {a[1]}" for a in alarm if a[0] == "manusia"))
    OUT.mkdir(exist_ok=True)
    (OUT / "laporan.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L)[:3000])


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    {"terapkan": terapkan, "laporan": laporan}[cmd](*a)
