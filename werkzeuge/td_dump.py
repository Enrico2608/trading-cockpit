import json, sys, datetime
sys.path.insert(0, 'werkzeuge')
import termine
von, bis = termine.zeitraum(datetime.datetime.now(datetime.timezone.utc))
json.dump(termine.td_laden(von, bis), open('dump/td_roh.json', 'w'), ensure_ascii=False)
print('ok')
