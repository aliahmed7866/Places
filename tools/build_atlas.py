"""Build the bundled 50m atlas: python tools/build_atlas.py /path/to/ne_50m_admin_0_countries.geojson.
Requires shapely for build only; the phone needs no GIS dependencies.
"""
import json,sys,html
from pathlib import Path
from shapely.geometry import shape
source=json.loads(Path(sys.argv[1]).read_text())
paths=[];meta={}
for f in source['features']:
    p=f['properties'];code=p.get('ISO_A2_EH') or p.get('ISO_A2')
    if code=='-99':code={'Kosovo':'XK'}.get(p['ADMIN'])
    if not code or len(code)!=2:continue
    geo=shape(f['geometry']).simplify(.025,preserve_topology=True)
    polygons=[geo] if geo.geom_type=='Polygon' else list(geo.geoms)
    def xy(lon,lat):return round((lon+180)*2.5,2),round((90-lat)*2.5,2)
    commands=[]
    for polygon in polygons:
        for ring in [polygon.exterior,*polygon.interiors]:
            points=[xy(*c[:2]) for c in ring.coords]
            commands.append('M'+'L'.join(f'{x:g},{y:g}' for x,y in points)+'Z')
    main=max(polygons,key=lambda x:x.area);a,b,c,d=main.bounds
    x,y=xy(a,d);xx,yy=xy(c,b)
    label=main.representative_point();lx,ly=xy(label.x,label.y)
    meta[code]={'name':p['ADMIN'],'continent':p['CONTINENT'],'bounds':[x,y,xx-x,yy-y],'label':[lx,ly]}
    paths.append(f'<path data-code="{code}" tabindex="0" role="button" aria-label="{html.escape(p["ADMIN"],quote=True)}" fill-rule="evenodd" d="{"".join(commands)}"/>')
root=Path(__file__).resolve().parents[1]/'static'
(root/'places-world.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" class="world-svg" viewBox="0 10 900 410" role="group" aria-label="Interactive world map">'+''.join(paths)+'</svg>')
(root/'atlas-countries.json').write_text(json.dumps(meta,separators=(',',':'),ensure_ascii=False))
print('Countries/territories:',len(meta),'SVG bytes:',(root/'places-world.svg').stat().st_size)
