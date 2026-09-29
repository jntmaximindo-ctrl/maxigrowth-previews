#!/usr/bin/env python3
"""Cek otomatis hasil kerja Codex (tanpa AI). Dipakai oleh .github/workflows/codex-check.yml.

  detect <changed.txt>        → cetak dir=… dan stage=riset|cekfakta|none (format GITHUB_OUTPUT)
  check  <dir> <stage>        → validasi; keluar 1 bila gagal (pesan dikirim balik ke Codex)
  finish <dir> <stage>        → setelah merge: tulis status.json (+ tandai ✎ verifikasi dari cek fakta)
"""
import json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
JOB_RE = re.compile(r"^(batches/B\d+/[^/]+)/(riset|konten|cekfakta)\.json$")


def detect(changed_file):
    dirs, files = set(), set()
    for line in pathlib.Path(changed_file).read_text().split():
        m = JOB_RE.match(line.strip())
        if m:
            dirs.add(m.group(1)); files.add(m.group(2))
    if len(dirs) != 1:
        print("dir="); print("stage=none"); return 0
    stage = "cekfakta" if "cekfakta" in files else "riset"
    print(f"dir={dirs.pop()}"); print(f"stage={stage}")
    return 0


def load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"file tidak ada: {p.relative_to(ROOT)}"
    except Exception as e:
        return None, f"JSON tidak valid di {p.relative_to(ROOT)}: {e}"


def schema_errors(obj, name):
    import jsonschema
    schema = json.loads((ROOT / "schemas" / name).read_text())
    v = jsonschema.Draft202012Validator(schema)
    return [f"{name} → {'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in v.iter_errors(obj)][:25]


def check(d, stage):
    d = ROOT / d
    errs = []
    if stage == "riset":
        for name in ("riset", "konten"):
            obj, e = load(d / f"{name}.json")
            if e:
                errs.append(e); continue
            errs += schema_errors(obj, f"{name}.schema.json")
            if name == "riset":
                # fakta berisi nilai tapi tanpa sumber = kemungkinan dikarang
                def walk(o, path=""):
                    if isinstance(o, dict):
                        if "v" in o and "src" in o and o.get("v") not in (None, "", []) and not o.get("src"):
                            errs.append(f"riset.json → {path}: ada nilai tapi src kosong (wajib URL sumber atau v=null)")
                        for k, val in o.items():
                            walk(val, f"{path}/{k}")
                    elif isinstance(o, list):
                        for i, val in enumerate(o):
                            walk(val, f"{path}/{i}")
                walk(obj)
        if (d / "konten.json").exists():
            r = subprocess.run([sys.executable, str(ROOT / "scripts/lint_permenkes.py"), str(d / "konten.json")],
                               capture_output=True, text=True)
            print(r.stdout)
            if r.returncode != 0:
                errs.append("konten.json melanggar aturan Permenkes (lihat daftar ✗ di atas)")
    elif stage == "cekfakta":
        obj, e = load(d / "cekfakta.json")
        if e:
            errs.append(e)
        else:
            for k in ("diperiksa", "beda", "kritis_ok"):
                if k not in obj:
                    errs.append(f"cekfakta.json: field '{k}' wajib ada")
            if not isinstance(obj.get("beda", []), list):
                errs.append("cekfakta.json: 'beda' harus list")
            if isinstance(obj.get("diperiksa"), int) and obj["diperiksa"] < 5:
                errs.append("cekfakta.json: terlalu sedikit fakta diperiksa (<5) — buka ulang semua src di riset.json")
    else:
        errs.append(f"tahap tidak dikenal: {stage}")
    for e in errs:
        print("✗", e)
    print("LULUS" if not errs else f"GAGAL ({len(errs)} masalah)")
    return 1 if errs else 0


def finish(d, stage, oleh="codex"):
    d = ROOT / d
    if stage == "riset":
        status = "Menunggu cek fakta"
    else:
        cek = json.loads((d / "cekfakta.json").read_text(encoding="utf-8"))
        riset = json.loads((d / "riset.json").read_text(encoding="utf-8"))
        if not cek.get("kritis_ok", False) or cek.get("beda"):
            # sama seperti research.py: fakta dipersoalkan tidak memblokir, tapi tampil sebagai ✎ verifikasi
            riset["verifikasi_manual"] = [
                {"path": b.get("path"), "tercatat": b.get("tercatat"), "catatan": b.get("di_sumber") or b.get("catatan")}
                for b in cek.get("beda", [])]
            (d / "riset.json").write_text(json.dumps(riset, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "Siap rakit"
    (d / "status.json").write_text(json.dumps({"status": status, "oleh": oleh}, ensure_ascii=False), encoding="utf-8")
    print("status:", status)
    return 0


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    sys.exit({"detect": detect, "check": check, "finish": finish}[cmd](*a))
