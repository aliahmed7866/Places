import base64
import importlib
import pytest

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('PLACES_DB_PATH', str(tmp_path/'places.sqlite3'))
    import app
    return importlib.reload(app).app.test_client()

def test_country_photo_link_and_export_preserve_places(client):
    entry={'country':'JP','place':'Tokyo','status':'visited','notes':'A memory'}
    assert client.post('/api/places',json=entry).status_code==201
    image=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aH9sAAAAASUVORK5CYII=')
    response=client.put('/api/countries/JP',json={'instagram_url':'https://instagram.com/stories/highlights/123/?igsh=abc','photo_base64':base64.b64encode(image).decode()})
    assert response.status_code==200
    profile=response.json
    assert profile['instagram_url']=='https://www.instagram.com/stories/highlights/123/'
    photo=client.get(profile['photo_url'])
    assert photo.data==image and photo.content_type=='image/png'
    assert photo.headers['X-Content-Type-Options']=='nosniff'
    exported=client.get('/api/export').json
    assert exported['places'][0]['notes']=='A memory'
    assert base64.b64decode(exported['country_profiles'][0]['photo_base64'])==image
    # Omitted fields stay intact; removal is explicit and independent.
    client.put('/api/countries/JP',json={'instagram_url':''})
    assert client.get('/api/countries/JP').json['photo_url']==profile['photo_url']
    client.put('/api/countries/JP',json={'photo_base64':None})
    assert client.get('/api/countries/JP/photo').status_code==404
    assert len(client.get('/api/places').json['places'])==1

@pytest.mark.parametrize('url',['javascript:alert(1)','https://evil.example/','https://www.instagram.com.evil.example/user','https://[bad','https://www.instagram.com/p/123/'])
def test_rejects_unsafe_or_unsupported_links(client,url):
    assert client.put('/api/countries/JP',json={'instagram_url':url}).status_code==400

def test_invalid_photos_and_unknown_country(client):
    assert client.put('/api/countries/QQ',json={}).status_code==404
    for photo in ['not base64',base64.b64encode(b'<svg onload="alert(1)"/>').decode(),'a'*2800001]:
        assert client.put('/api/countries/JP',json={'photo_base64':photo}).status_code==400
    assert client.get('/api/countries/JP').json['photo_url'] is None
