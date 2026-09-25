import requests
from pystac_client import Client

def check_catalogs():
    print("Connecting to Element84 STAC catalog...")
    cat = Client.open("https://earth-search.aws.element84.com/v1")
    
    # Bounding box for Meghalaya and Mizoram (89.0E to 94.0E, 21.0N to 27.0N)
    bbox = [89.0, 21.0, 94.0, 27.0]
    
    search = cat.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime="2024-11-01/2025-04-30",
        query={"eo:cloud_cover": {"lt": 5}}
    )
    items = list(search.items())
    print(f"Total Sentinel-2 L2A items found (<5% cloud cover): {len(items)}")
    
    # Group by MGRS tile code
    mgrs_tiles = {}
    for item in items:
        grid_code = item.properties.get("grid:code") or item.properties.get("mgrs:utm_zone", "")
        # Extract tile ID from item id (e.g. S2A_46RGS_20241205_0_L2A -> 46RGS)
        tile_id = item.id.split("_")[1] if "_" in item.id else item.id
        if tile_id not in mgrs_tiles:
            mgrs_tiles[tile_id] = []
        mgrs_tiles[tile_id].append(item)
        
    print(f"\nUnique MGRS Tiles identified: {len(mgrs_tiles)}")
    for t_id, t_items in list(mgrs_tiles.items())[:10]:
        best = min(t_items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
        print(f"  Tile {t_id}: Best Scene = {best.id} | Date = {best.datetime.strftime('%Y-%m-%d')} | Cloud = {best.properties.get('eo:cloud_cover'):.2f}%")

if __name__ == "__main__":
    check_catalogs()
