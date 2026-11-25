"""Offline design evidence. Reads only odd tuning rows; never scores the test set.
Run from any directory: python scripts/analyse_cascade_tuning.py
"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRICT = {'Mortgage', 'Bank account or service', 'Money transfer or service'}
SETTINGS = {'strict': STRICT, 'relaxed': STRICT | {'Debt collection', 'Consumer loan'}}
SMALL = ROOT/'results/accuracy/acc-qwen2.5-1.5b-20261009-033439/predictions.csv'
LARGE = ROOT/'results/accuracy/acc-qwen2.5-7b-20261009-035613/predictions.csv'
TUNING = ROOT/'golden_set/tuning.csv'


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def predictions(path, tuning):
    selected = {}
    for r in read(path):
        row = int(r['row'])
        if row not in tuning:
            continue
        if row in selected:
            raise ValueError(f'Duplicate tuning row {row} in {path}')
        if r['golden'] != tuning[row]:
            raise ValueError(f'Changed golden label for {row}')
        selected[row] = r['predicted'] if r['http_status'] == '201' else ''
    if set(selected) != set(tuning):
        raise ValueError('Missing tuning predictions')
    return selected


def main():
    records = read(TUNING)
    tuning = {int(r['row']): r['label'] for r in records}
    if len(records) != len(tuning) or len(tuning) != 75 or any(r % 2 != 1 for r in tuning):
        raise ValueError('Expected 75 unique odd tuning rows')
    small, large = predictions(SMALL, tuning), predictions(LARGE, tuning)
    precision = {}
    for category in sorted(set(small.values())):
        ids = [r for r in tuning if small[r] == category]
        correct = sum(small[r] == tuning[r] for r in ids)
        precision[category or 'ERROR'] = {'correct': correct, 'predictions': len(ids),
                                           'precision': correct / len(ids)}
    output = {'kind': 'offline_tuning_simulation_not_benchmark', 'n': len(tuning),
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (TUNING, SMALL, LARGE)},
              'small_correct': sum(small[r] == tuning[r] for r in tuning),
              'large_correct': sum(large[r] == tuning[r] for r in tuning),
              'predicted_category_precision': precision, 'settings': {}}
    for setting, allowed in SETTINGS.items():
        accepted = {r for r in tuning if small[r] in allowed}
        escalated = set(tuning) - accepted
        final = {r: small[r] if r in accepted else large[r] for r in tuning}
        output['settings'][setting] = {
            'accept_categories': sorted(allowed), 'accepted': len(accepted),
            'wrong_accepted': sum(small[r] != tuning[r] for r in accepted),
            'escalated': len(escalated), 'escalation_fraction': len(escalated)/len(tuning),
            'correct': sum(final[r] == tuning[r] for r in tuning),
            'per_category': {c: {'correct': sum(final[r] == c for r in tuning if tuning[r] == c),
                                 'total': sum(tuning[r] == c for r in tuning)}
                             for c in sorted(set(tuning.values()))},
        }
    dest = ROOT/'results/a2/cascade_tuning.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(output['settings'], indent=2))
    print('Saved', dest)


if __name__ == '__main__':
    main()
