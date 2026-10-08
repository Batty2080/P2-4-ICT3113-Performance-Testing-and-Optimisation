"""
Prepare the data files JMeter reads (written to jmeter/):

  team_rows_bodies.tsv  row <TAB> ready-made JSON request body for POST /tickets, for rows 4000-4999 in order.
                        The narrative is JSON-escaped (newlines, quotes, non-ASCII), so every line is one safe line.
  search_terms.csv      the fixed list of 20 search words for GET /search (R3): the 20 words that appear in the
                        most narratives of rows 4000-4999 after removing stop words and the dataset's XXXX redactions.

Usage (from the repo root):  python scripts/make_jmeter_data.py
Input: team_rows_4000_4999.csv (see scripts/make_team_rows.py). Standard library only.
"""
import csv, json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "jmeter"

STOP = set("""
about above after again against all also always among and any are because been before being below between both but
can cannot could did does doing down during each even ever every few for from further had has have having her here
hers him his how into its itself just like made make many may me more most much must myself neither nor not now off
once one only other our out over own same she should since some such than that the their them then there these they
this those through too under until upon very was way were what when where which while who whom why will with within
without would you your yours yourself said told call called back going went get got want wanted still never
""".split())


def main():
    rows = []
    with open(ROOT / "team_rows_4000_4999.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append((int(r["row"]), r["narrative"]))
    rows.sort()
    assert [r for r, _ in rows] == list(range(4000, 5000)), "expected rows 4000-4999"

    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_DIR / "team_rows_bodies.tsv", "w", encoding="utf-8", newline="") as f:
        f.write("row\tbody\n")
        for row, text in rows:
            body = json.dumps({"narrative": text}, ensure_ascii=True)  # ASCII-only, no raw tabs/newlines
            assert "\t" not in body and "\n" not in body and "\r" not in body
            f.write(f"{row}\t{body}\n")

    doc_freq = Counter()
    for _, text in rows:
        words = {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4 and w not in STOP and not set(w) <= {"x"}}
        doc_freq.update(words)
    terms = [w for w, _ in doc_freq.most_common(20)]
    with open(OUT_DIR / "search_terms.csv", "w", encoding="utf-8", newline="") as f:
        f.write("term\n" + "\n".join(terms) + "\n")

    print(f"Wrote {len(rows)} ticket bodies to jmeter/team_rows_bodies.tsv")
    print("Search terms (word: number of narratives containing it):")
    for w in terms:
        print(f"  {w}: {doc_freq[w]}")


if __name__ == "__main__":
    main()
