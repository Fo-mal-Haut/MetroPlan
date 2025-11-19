import json
import sys

def check_train(train_id):
    try:
        with open('schedule_list.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("schedule_list.json not found.")
        return

    trains = data.get('train', [])
    target_train = None
    for t in trains:
        if t['id'] == train_id:
            target_train = t
            break
    
    if not target_train:
        print(f"Train {train_id} not found in schedule_list.json")
        return

    print(f"Train: {target_train['id']}")
    print(f"Start: {target_train['start_station']}")
    print(f"End: {target_train['end_station']}")
    print("Stations:")
    for s in target_train['stations']:
        print(f"  {s['name']}: {s['time']}")

if __name__ == "__main__":
    check_train("S4802")
