"""
Extract this team's 1,000 rows (4000-4999) from the course CSV into team_rows_4000_4999.csv (row,narrative).

Used by the accuracy test (joins golden_set/golden_set.csv by row) and by JMeter (CSV Data Set Config).
Usage:  python make_team_rows.py path/to/ict3113_tickets.csv
"""
import csv, sys

FIRST, LAST = 4000, 4999
OUT = "team_rows_4000_4999.csv"

if len(sys.argv) != 2:
    sys.exit(__doc__)

csv.field_size_limit(10**9)
rows = []
with open(sys.argv[1], encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        if FIRST <= int(r["row"]) <= LAST:
            rows.append((int(r["row"]), r["narrative"]))

rows.sort()
assert [r for r, _ in rows] == list(range(FIRST, LAST + 1)), "missing or duplicate rows"

with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["row", "narrative"])
    w.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUT}")
