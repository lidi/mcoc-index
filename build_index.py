#!/usr/bin/env python3
"""Build a small index + size-limited detail files from mcoc.gg's public champion data.

index.md          name | alias | file | class | release date | details file   (all champions, small)
details/NN.md     full rows: effects, immunities, reacts-to, tags            (each kept under MAX_BYTES)
Ability text itself is NOT copied: it lives at https://mcoc.gg/json/champions/<file>.json
"""
import json, os, sys, time, urllib.request

BASE = "https://mcoc.gg/json/"
UA = {"User-Agent": "mcoc-index-bot (+https://github.com/lidi/mcoc-index)"}
RAW = "https://raw.githubusercontent.com/lidi/mcoc-index/main/"
MAX_BYTES = 30000


def get(name):
    url = f"{BASE}{name}.json?v={int(time.time())}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    if isinstance(data, list) and data and isinstance(data[0], list):
        data = data[0]
    if isinstance(data, dict):
        data = next(iter(data.values()))
    return data


def clean(v):
    return str(v).replace("|", "/").replace("\n", " ").strip()


def main():
    champs = get("champions")
    classes = {str(c["id"]): c["name"] for c in get("class")}
    abilities = {str(a["id"]): a["name"] for a in get("abilities")}
    immun = {i["id"]: i["name"] + (f" ({i['NOTE'].lower()})" if i.get("NOTE") else "") for i in get("immunities")}
    tags = {t["id"]: t["tag"] for t in get("tags")}

    champs = sorted(champs, key=lambda c: c.get("name", "").lower())
    if len(champs) < 300:
        sys.exit(f"Only {len(champs)} champions parsed - refusing to overwrite")

    recs = []
    for c in champs:
        base = [clean(c.get("name", "")), clean(c.get("alias", "") or ""), clean(c.get("image", "")),
                clean(classes.get(str(c.get("class")), c.get("class", ""))), clean(c.get("date", ""))]
        detail = " | ".join(base[:3] + [
            clean(", ".join(abilities[str(i)] for i in c.get("ability", []) if str(i) in abilities)),
            clean(", ".join(immun.get(i, i) for i in c.get("immune", []))),
            clean(", ".join(immun.get(i, i) for i in c.get("react", []))),
            clean(", ".join(tags[t] for t in c.get("tags", []) if t in tags)),
        ])
        recs.append((base, detail))

    # split detail rows into files under MAX_BYTES
    chunks, cur, size = [], [], 0
    for base, detail in recs:
        n = len(detail.encode()) + 1
        if cur and size + n > MAX_BYTES:
            chunks.append(cur); cur, size = [], 0
        cur.append((base, detail)); size += n
    if cur:
        chunks.append(cur)

    os.makedirs("details", exist_ok=True)
    for f in os.listdir("details"):
        os.remove(os.path.join("details", f))

    index_rows, ranges = [], []
    for n, chunk in enumerate(chunks, 1):
        fname = f"details/{n:02d}.md"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"# MCOC champion details {n:02d}/{len(chunks):02d}: {chunk[0][0][0]} - {chunk[-1][0][0]}\n\n"
                    "Columns: name | alias | file | effects (as listed by mcoc.gg) | "
                    "immunities & resistances (mcoc.gg labels: potency / conditional / duration) | reacts to | tags\n\n")
            f.write("\n".join(d for _, d in chunk) + "\n")
        ranges.append(f"- {RAW}{fname} : {chunk[0][0][0]} - {chunk[-1][0][0]}")
        index_rows += [" | ".join(b + [f"{n:02d}"]) for b, _ in chunk]

    with open("index.md", "w", encoding="utf-8") as f:
        f.write(
            f"# MCOC Champion Index ({len(recs)} champions, source: mcoc.gg public data, refreshed daily)\n\n"
            "Ability text: https://mcoc.gg/json/champions/<file>.json\n\n"
            "Detail files (effects, immunities, reacts-to, tags):\n" + "\n".join(ranges) + "\n\n"
            "Columns: name | alias | file | class | release date | details file\n\n"
            + "\n".join(index_rows) + "\n")
    print(f"{len(recs)} champions, {len(chunks)} detail files")


if __name__ == "__main__":
    main()
