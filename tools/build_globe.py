"""Build globe geometry from Natural Earth's 50m admin-0 GeoJSON (Shapely required)."""
import json
import sys
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.geometry.polygon import orient

source=json.loads(Path(sys.argv[1]).read_text())
features={}
metadata={}
areas={}
for feature in source['features']:
    p=feature['properties']
    code=p.get('ISO_A2_EH') or p.get('ISO_A2')
    if code=='-99': code={'Kosovo':'XK'}.get(p['ADMIN'])
    if not code or len(code)!=2: continue
    geo=shape(feature['geometry']).simplify(.025,preserve_topology=True)
    polygons=[geo] if geo.geom_type=='Polygon' else list(geo.geoms)
    # D3 expects clockwise exterior rings. Merge shared country codes (AU's territories).
    item=features.setdefault(code,{'type':'Feature','properties':{'code':code},'geometry':{'type':'MultiPolygon','coordinates':[]}})
    item['geometry']['coordinates'].extend(mapping(orient(poly,sign=-1))['coordinates'] for poly in polygons)
    main=max(polygons,key=lambda poly:poly.area)
    if main.area>areas.get(code,0):
        areas[code]=main.area
        a,b,c,d=main.bounds
        point=main.representative_point()
        metadata[code]={'name':p['ADMIN'],'continent':p['CONTINENT'],'bounds':[(a+180)*2.5,(90-d)*2.5,(c-a)*2.5,(d-b)*2.5],'label':[(point.x+180)*2.5,(90-point.y)*2.5]}

def rounded(value):
    if isinstance(value,float): return round(value,4)
    if isinstance(value,(list,tuple)): return [rounded(x) for x in value]
    if isinstance(value,dict): return {k:rounded(v) for k,v in value.items()}
    return value

root=Path(__file__).resolve().parents[1]/'static'
(root/'globe-countries.json').write_text(json.dumps(rounded({'type':'FeatureCollection','features':list(features.values())}),separators=(',',':')))
(root/'atlas-countries.json').write_text(json.dumps(rounded(metadata),separators=(',',':')))
