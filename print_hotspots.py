import urllib.request, json

hotspots = json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/monitoring/hotspots').read())
print('--- MEGHALAYA HOTSPOTS ---')
for h in hotspots['features']:
    p = h['properties']
    c = h['geometry']['coordinates']
    if p['state'] == 'Meghalaya':
        print(f"{p['event_id']}: lon={c[0]:.4f}, lat={c[1]:.4f}, dist={p['district']}, tier={p['fused_tier']}")
print('--- MIZORAM HOTSPOTS ---')
for h in hotspots['features']:
    p = h['properties']
    c = h['geometry']['coordinates']
    if p['state'] == 'Mizoram':
        print(f"{p['event_id']}: lon={c[0]:.4f}, lat={c[1]:.4f}, dist={p['district']}, tier={p['fused_tier']}")
