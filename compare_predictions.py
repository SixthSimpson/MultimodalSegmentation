import json

with open('data/predictions/test_001_baseline.json') as f:
    pred = json.load(f)
with open('data/source_of_truth_flat/test_001.json') as f:
    truth = json.load(f)

print("PREDICTED ADS:")
for s in pred['segments']:
    if s['label'] == 'advertisement':
        print(f"  [{s['start']:7.1f} - {s['end']:7.1f}]  ({s['end']-s['start']:.1f}s)")

print("\nTRUE ADS:")
for s in truth['segments']:
    if s['label'] == 'advertisement':
        print(f"  [{s['start']:7.1f} - {s['end']:7.1f}]  ({s['end']-s['start']:.1f}s)")
