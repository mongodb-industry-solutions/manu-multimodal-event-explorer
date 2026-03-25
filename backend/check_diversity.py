"""Quick script to check dataset diversity before ingestion."""
from datasets import load_dataset

print("Loading dataset metadata only (no images)...")
ds = load_dataset(
    'jongwonryu/MIST-autonomous-driving-dataset', 
    split='test', 
    streaming=True
).select_columns(['text'])  # Only load text, skip images!

seen = {}
samples_per_condition = 5

count = 0
for idx, s in enumerate(ds):
    if count >= 100:
        break
    
    text = s.get('text', '')
    
    if text in seen:
        if seen[text] >= samples_per_condition:
            continue
        seen[text] += 1
    else:
        seen[text] = 1
    
    count += 1

print()
print('=' * 50)
print('DIVERSITY CHECK (simulating 100 samples)')
print('=' * 50)
print(f'Unique conditions found: {len(seen)}')
print(f'Total samples would be loaded: {count}')
print()
print('Conditions breakdown:')
for text, c in sorted(seen.items(), key=lambda x: -x[1]):
    print(f'  [{c:2d}] {text}')
print('=' * 50)
