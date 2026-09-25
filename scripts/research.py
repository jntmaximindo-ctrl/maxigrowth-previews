#!/usr/bin/env python3
"""Riset + konten + cek fakta satu klinik lewat OpenAI Responses API (dengan web search).

usage: python scripts/research.py batches/B01/W14
Butuh env OPENAI_API_KEY. Model bisa diganti lewat OPENAI_MODEL (default di bawah).
Menulis: riset.json, konten.json, cekfakta.json, research-log.json di folder job.
Keluar dengan kode 2 jika validasi skema gagal atau cek fakta menandai beda kritis.
"""
import json, os, re, sys, time, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL = os.environ.get("OPENAI_MODEL", "gpt-6-sol")
API = "https://api.openai.com/v1/responses"


def call(prompt: str, web: bool = True) -> tuple[str, dict]:
    body = {"model": MODEL, "input": prompt}
    if web:
        body["tools"] = [{"type": "web_search"}]
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.load(r)
            break
        except Exception as e:  # rate limit / network: back off
            if attempt == 3:
                raise
            time.sleep(20 * (attempt + 1))
    text = data.get("output_text") or "".join(
        c.get("text", "") for o in data.get("output", []) if o.get("type") == "message" for c in o.get("content", []))
    return text, data.get("usage", {})


def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("tidak ada JSON di jawaban model")
    return json.loads(m.group(0))


def validate(obj: dict, schema_name: str) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return []
    schema = json.loads((ROOT / "schemas" / schema_name).read_text())
    v = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(obj)]


def fill(tpl: str, **kw) -> str:
    for k, v in kw.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    return tpl


def main(job_dir: str) -> int:
    d = pathlib.Path(job_dir)
    job = json.loads((d / "job.json").read_text())
    log = {"model": MODEL, "usage": {}}
    prompts = ROOT / "prompts"

    # 1. riset (maks. 2 percobaan bila skema gagal)
    errs, riset = ["belum"], {}
    for _ in range(2):
        text, u = call(fill((prompts / "riset.md").read_text(), JOB_JSON=json.dumps(job, ensure_ascii=False)))
        log["usage"]["riset"] = u
        try:
            riset = extract_json(text)
            errs = validate(riset, "riset.schema.json")
        except Exception as e:
            errs = [str(e)]
        if not errs:
            break
    (d / "riset.json").write_text(json.dumps(riset, ensure_ascii=False, indent=2))
    if errs:
        print("SKEMA RISET GAGAL:", *errs[:20], sep="\n  ")
        return 2

    # 2. cek fakta silang (prompt terpisah, konteks segar)
    text, u = call(fill((prompts / "cekfakta.md").read_text(), RISET_JSON=json.dumps(riset, ensure_ascii=False)))
    log["usage"]["cekfakta"] = u
    cek = extract_json(text)
    (d / "cekfakta.json").write_text(json.dumps(cek, ensure_ascii=False, indent=2))

    # 3. konten ID/EN + outreach (tanpa web search)
    text, u = call(fill((prompts / "konten.md").read_text(), RISET_JSON=json.dumps(riset, ensure_ascii=False),
                        SLUG=job.get("slug", job["id"].lower())), web=False)
    log["usage"]["konten"] = u
    konten = extract_json(text)
    kerr = validate(konten, "konten.schema.json")
    (d / "konten.json").write_text(json.dumps(konten, ensure_ascii=False, indent=2))
    (d / "research-log.json").write_text(json.dumps(log, indent=2))

    if kerr:
        print("SKEMA KONTEN GAGAL:", *kerr[:20], sep="\n  ")
        return 2
    if not cek.get("kritis_ok", False):
        print("CEK FAKTA: ada beda kritis → perlu ditinjau", json.dumps(cek.get("beda", [])[:10], ensure_ascii=False))
        return 2
    print("OK", job["id"], "beda non-kritis:", len(cek.get("beda", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
