import importlib
import json
from pathlib import Path
import pytest

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('PLACES_DB_PATH', str(tmp_path/'places.sqlite3'))
    import app
    return importlib.reload(app).app.test_client()


def test_planned_range_single_day_and_conversion(client):
    payload={'country':'GE','place':'Mestia','status':'planned','start_date':'2028-02-28','end_date':'2028-03-02'}
    result=client.post('/api/places',json=payload)
    assert result.status_code==201
    record=result.json['place']
    days=client.get('/api/calendar/2028').json['days']
    assert len(days)==4 and days['2028-02-29'][0]['status']=='planned'
    single=client.post('/api/places',json={**payload,'country':'TR','start_date':'2028-02-29','end_date':''})
    assert single.json['place']['end_date']=='2028-02-29'
    assert len(client.get('/api/calendar/2028').json['days']['2028-02-29'])==2
    update=client.put(f"/api/places/{record['id']}",json={**record,'status':'visited'})
    assert update.status_code==200 and update.json['place']['status']=='visited'
    assert client.delete(f"/api/places/{record['id']}").status_code==204
    assert len(client.get('/api/calendar/2028').json['days'])==1


def test_plans_need_dates_wishlist_stays_off_calendar(client):
    payload={'country':'GB','status':'planned'}
    assert client.post('/api/places',json=payload).status_code==400
    assert client.post('/api/places',json={**payload,'status':'wishlist','start_date':'2028-01-01'}).status_code==201
    assert client.get('/api/calendar/2028').json['days']=={}


def test_map_asset_is_bundled_and_home_defaults_to_map(client):
    import xml.etree.ElementTree as ET
    svg=client.get('/static/places-world.svg')
    assert svg.status_code==200
    codes={p.attrib['data-code'] for p in ET.fromstring(svg.data)}
    assert {'GE','GB','TR'} <= codes
    home=client.get('/').data
    assert b'id="map-view" class="view active"' in home
    assert b'id="calendar-view" class="view" hidden' in home
    assert b'planner-month' in home and b'planner-year' in home
