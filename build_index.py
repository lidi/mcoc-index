#!/usr/bin/env python3
"""Build index.md from mcoc.gg's public champion data files."""
import json, sys, time, urllib.request
from datetime import datetime, timezone

BASE = "https://mcoc.gg/json/"
COLUMNS_END = "| reacts to | tags\n\n"  # end of header; body follows
UA = {"User-Agent": "mcoc-index-bot (+https://github.com/lidi/mcoc-index)"}


def get(name):
    url = f"{BASE}{name}.json?v={int(time.time())}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    # files are either [ {...}, ... ] or [ [ {...}, ... ] ]
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

    rows = []
    for c in champs:
        rows.append(" | ".join(clean(x) for x in [
            c.get("name", ""),
            c.get("alias", "") or "",
            c.get("image", ""),
            classes.get(str(c.get("class")), c.get("class", "")),
            c.get("date", ""),
            ", ".join(abilities[str(i)] for i in c.get("ability", []) if str(i) in abilities),
            ", ".join(immun.get(i, i) for i in c.get("immune", [])),
            ", ".join(immun.get(i, i) for i in c.get("react", [])),
            ", ".join(tags[t] for t in c.get("tags", []) if t in tags),
        ]))

    if len(rows) < 300:
        sys.exit(f"Only {len(rows)} champions parsed - refusing to overwrite index.md")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    header = (
        f"# MCOC Champion Index\n\n"
        f"Source: mcoc.gg public data files. Champions: {len(rows)}. Last data change detected: {today} (UTC).\n\n"
        "Full ability text for a champion: https://mcoc.gg/json/champions/<file>.json (use the \"file\" column).\n\n"
        "Columns: name | alias | file | class | release date | effects (as listed by mcoc.gg) | "
        "immunities & resistances (mcoc.gg labels: potency / conditional / duration) " + COLUMNS_END
    )
    body = "\n".join(rows) + "\n"

    try:
        old = open("index.md", encoding="utf-8").read()
        if old.split(COLUMNS_END, 1)[-1] == body:
            print("No data change")
            return
    except FileNotFoundError:
        pass
    with open("index.md", "w", encoding="utf-8") as f:
        f.write(header + body)
    print(f"Wrote index.md with {len(rows)} champions")


if __name__ == "__main__":
    main()
