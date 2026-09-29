#!/usr/bin/env python3
"""Klinik-Bus: jembatan repo ↔ Drive "07 Klinik-Bus" (dikerjakan scheduled task ChatGPT, kuota Plus).

  rclone-conf            → tulis ~/.config/rclone/rclone.conf, remote "bus:" berakar di folder Klinik-Bus
  pull <dir_riset> <dir_cekfakta>
                         → baca hasil GPT yang sudah diunduh (Google Docs diekspor .txt), pasang ke batches/,
                           cek otomatis, tulis status. Mencetak rencana aksi Drive ke bus-actions.txt:
                             ARSIP <pola>              pindahkan file bus yang cocok ke "99 Arsip"
                             REVISI <key> <file_catatan>  tulis ulang surat tugas + catatan kesalahan
"""
import json, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUS_ROOT = "1wIb7ZfR3BA0tNVRjxQXy6CkmFBBgHMwH"   # Drive: "07 Klinik-Bus (GPT scheduled task)"
MAKS_PERCOBAAN = 2


def rclone_conf():
    tok = json.loads(os.environ["RCLONE_DRIVE_TOKEN"])
    p = pathlib.Path(os.path.expanduser("~/.config/rclone/rclone.conf"))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"[bus]\ntype = drive\nscope = drive\nroot_folder_id = {BUS_ROOT}\ntoken = {json.dumps(tok)}\n")
    return 0


def parse(text):
    """JSON dari Google Docs/teks: buang BOM, pagar ```, escape markdown."""
    t = text.lstrip("\ufeff").strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("tidak ada objek JSON")
    t = t[a:b + 1]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return json.loads(re.sub(r"\\([_\[\]&*#()])", r"\1", t))


def files_by_key(folder):
    out = {}
    for f in pathlib.Path(folder).glob("*"):
        m = re.match(r"^(B\d+-W[^_]+)_(riset|konten|cekfakta)", f.name)
        if m:
            out.setdefault(m.group(1), {})[m.group(2)] = f
    return out


def status_of(d):
    try:
        return json.loads((d / "status.json").read_text())
    except Exception:
        return {}


def write_status(d, **kw):
    st = status_of(d); st.update(kw)
    (d / "status.json").write_text(json.dumps(st, ensure_ascii=False))


def run_check(d, stage):
    r = subprocess.run([sys.executable, str(ROOT / "scripts/codex_check.py"), "check", str(d.relative_to(ROOT)), stage],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode == 0, (r.stdout + r.stderr)[-3000:]


def pull(dir_riset, dir_cek):
    riset, cek = files_by_key(dir_riset), files_by_key(dir_cek)
    acts, log = [], []
    notes = ROOT / "bus-notes"; notes.mkdir(exist_ok=True)
    for key, fs in sorted(riset.items()):
        b, w = key.split("-", 1)
        d = ROOT / "batches" / b / w
        if not (d / "job.json").exists():
            log.append(f"{key}: job tidak ada di repo, dilewati"); continue
        st = status_of(d).get("status", "")
        # --- tahap riset ---
        if st == "Riset di GPT" and "riset" in fs and "konten" in fs:
            try:
                (d / "riset.json").write_text(json.dumps(parse(fs["riset"].read_text()), ensure_ascii=False, indent=2))
                (d / "konten.json").write_text(json.dumps(parse(fs["konten"].read_text()), ensure_ascii=False, indent=2))
                ok, out = run_check(d, "riset")
            except Exception as e:
                ok, out = False, f"✗ JSON tidak bisa dibaca: {e}"
            if ok:
                write_status(d, status="Menunggu cek fakta", oleh="gpt-bus")
                log.append(f"{key}: riset LULUS → menunggu GPT-B")
            else:
                n = status_of(d).get("percobaan", 0) + 1
                for f in ("riset.json", "konten.json"):
                    (d / f).unlink(missing_ok=True)
                acts.append(f"ARSIP {key}_riset* {key}_konten*")
                if n >= MAKS_PERCOBAAN:
                    write_status(d, status="Butuh cek riset", percobaan=n)
                    log.append(f"{key}: riset GAGAL {n}x → Butuh cek riset\n{out}")
                else:
                    write_status(d, percobaan=n)
                    (notes / key).write_text(f"REVISI ke-{n}: hasil sebelumnya ditolak cek otomatis. Perbaiki hal berikut lalu kerjakan ulang dari awal:\n{out}\n")
                    acts.append(f"REVISI {key} bus-notes/{key}")
                    log.append(f"{key}: riset GAGAL → dikembalikan ke GPT-A\n{out}")
            continue
        # --- tahap cek fakta ---
        if st == "Menunggu cek fakta" and key in cek and "cekfakta" in cek[key]:
            try:
                (d / "cekfakta.json").write_text(json.dumps(parse(cek[key]["cekfakta"].read_text()), ensure_ascii=False, indent=2))
                ok, out = run_check(d, "cekfakta")
            except Exception as e:
                ok, out = False, f"✗ JSON tidak bisa dibaca: {e}"
            if ok:
                subprocess.run([sys.executable, str(ROOT / "scripts/codex_check.py"), "finish",
                                str(d.relative_to(ROOT)), "cekfakta", "gpt-bus"], check=True, cwd=ROOT)
                acts.append(f"ARSIP {key}_*")
                log.append(f"{key}: cek fakta LULUS → Siap rakit")
            else:
                (d / "cekfakta.json").unlink(missing_ok=True)
                acts.append(f"ARSIP {key}_cekfakta*")
                log.append(f"{key}: cek fakta GAGAL → GPT-B mengulang\n{out}")
    (ROOT / "bus-actions.txt").write_text("\n".join(acts) + ("\n" if acts else ""))
    print("\n".join(log) or "Tidak ada hasil baru.")
    return 0


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    sys.exit({"rclone-conf": rclone_conf, "pull": pull}[cmd](*a))
