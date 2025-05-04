import json
with open('output/merged_all_monsters.json', encoding='utf-8') as f:
    data = json.load(f)
print(len(data['monsters']))
