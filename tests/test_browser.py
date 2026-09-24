import base64
import re
import importlib
import os
from pathlib import Path
import threading
import pytest

playwright=pytest.importorskip('playwright.sync_api')

@pytest.mark.parametrize('width',[390,1280])
def test_map_and_date_range_planner(tmp_path,monkeypatch,width):
    monkeypatch.setenv('PLACES_DB_PATH',str(tmp_path/'places.sqlite3'))
    import app
    app=importlib.reload(app)
    from werkzeug.serving import make_server
    server=make_server('127.0.0.1',0,app.app,threaded=True)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        with playwright.sync_playwright() as pw:
            browser=pw.chromium.launch()
            page=browser.new_page(viewport={'width':width,'height':900})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            expect=playwright.expect
            expect(page.locator('#map-view')).to_be_visible()
            expect(page.locator('#calendar-view')).to_be_hidden()
            globe=page.locator('.world-svg')
            page.locator('#border-contrast').select_option('strong')
            expect(page.locator('#atlas-layout')).to_have_attribute('data-borders','strong')
            assert page.locator('path[data-code]').first.evaluate('(el)=>getComputedStyle(el).strokeWidth') == '1.7px'
            page.locator('#border-contrast').select_option('clear')
            expect(globe).to_have_attribute('data-detail','continents')
            expect(page.locator('.globe-labels button[data-code]')).to_have_count(0)
            expect(page.get_by_role('button',name='Explore Africa',exact=True)).to_be_visible()
            folder=os.environ.get('BROWSER_ARTIFACT_DIR')
            if folder:
                Path(folder).mkdir(parents=True,exist_ok=True)
                page.locator('.atlas-stage').screenshot(path=str(Path(folder)/f'continents-{width}.png'))
            page.get_by_role('button',name='Explore Africa',exact=True).click()
            expect(page.locator('#atlas-region')).to_have_value('Africa')
            expect(globe).to_have_attribute('data-detail','countries')
            expect(page.locator('.continent-label')).to_have_count(0)
            page.locator('#zoom-reset').click()
            expect(globe).to_have_attribute('data-detail','continents')
            page.locator('#zoom-in').click()
            expect(globe).to_have_attribute('data-detail','countries')
            page.locator('#zoom-out').click()
            expect(globe).to_have_attribute('data-detail','continents')
            page.locator('#atlas-region').select_option('Antarctica')
            expect(globe).to_have_attribute('data-detail','countries')
            expect(page.locator('#atlas-progress')).to_contain_text('Antarctica')
            page.locator('#zoom-reset').click()
            georgia=page.locator('path[data-code="GE"]')
            georgia.focus();page.keyboard.press('Enter')
            expect(page.locator('#country-panel h2')).to_contain_text('Georgia')
            page.locator('#country-panel').get_by_role('button',name='＋ Add a place',exact=True).click()
            expect(page.locator('select[name=country]')).to_have_value('GE')
            page.locator('#close-dialog').click()
            page.get_by_role('button',name='Planner',exact=True).click()
            page.locator('#planner-year').fill('2028');page.locator('#planner-year').press('Tab')
            page.locator('#planner-month').select_option('1')
            page.locator('[data-date="2028-02-28"]').click()
            page.locator('select[name=country]').select_option('GE')
            page.locator('input[name=end_date]').fill('2028-03-02')
            page.locator('#save-place').click()
            expect(page.locator('#place-dialog')).not_to_be_visible()
            expect(page.locator('[data-date="2028-02-29"] .flags')).to_have_text('🇬🇪')
            page.get_by_role('button',name='Year overview',exact=True).click()
            expect(page.locator('[data-date="2028-03-02"] .flags')).to_have_text('🇬🇪')
            page.locator('[data-date="2028-02-29"]').click()
            page.locator('#day-entries button').click()
            page.locator('select[name=status]').select_option('visited')
            page.locator('#save-place').click()
            expect(page.locator('#place-dialog')).not_to_be_visible()
            page.get_by_role('button',name='Map',exact=True).click()
            expect(georgia).to_have_class(re.compile(r'\bvisited\b'))
            expect(page.locator('#countries-total')).to_have_text('1')
            page.locator('#atlas-search').fill('Japan')
            page.locator('#atlas-results button').click()
            expect(page.locator('#country-panel h2')).to_contain_text('Japan')
            globe=page.locator('.world-svg')
            page.wait_for_function("document.querySelector('.globe-labels .selected')?.textContent === 'Japan'")
            label=page.locator('.globe-labels .selected')
            assert label.evaluate('(el)=>getComputedStyle(el).fontSize') == '15px'
            before=globe.get_attribute('data-zoom')
            page.locator('#zoom-in').click()
            expect(globe).not_to_have_attribute('data-zoom',before)
            assert label.evaluate('(el)=>getComputedStyle(el).fontSize') == '15px'

            # Crowded microstates, islands, long names and dateline countries must
            # remain identifiable at both mobile and desktop widths.
            for code, name in [('MC','Monaco'),('SG','Singapore'),('FJ','Fiji'),('CD','DR Congo'),('KR','South Korea')]:
                page.locator('#atlas-search').fill(code)
                page.locator('#atlas-results button').first.click()
                chosen=page.locator(f'.globe-labels button[data-code="{code}"]')
                expect(chosen).to_be_visible()
                expect(chosen).to_have_text(name)
                expect(page.locator('#country-panel h2')).to_contain_text(name)
            page.locator('#label-size').select_option('21')
            page.wait_for_function("getComputedStyle(document.querySelector('.globe-labels .selected')).fontSize === '21px'")
            page.locator('#map-expand').click()
            expect(page.locator('#map-expand')).to_have_attribute('aria-pressed','true')
            page.wait_for_timeout(100)
            boxes=page.locator('.globe-labels button').evaluate_all('(els)=>els.map(el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}})')
            for i,a in enumerate(boxes):
                for b in boxes[i+1:]:
                    assert not (a['x']<b['right'] and a['right']>b['x'] and a['y']<b['bottom'] and a['bottom']>b['y'])
            page.locator('#visible-count').click()
            expect(page.locator('#visible-countries')).to_be_visible()
            page.locator('#visible-countries').get_by_role('button',name='South Korea',exact=False).click()
            expect(page.locator('#country-panel h2')).to_contain_text('South Korea')
            page.locator('#map-expand').click()
            page.locator('#label-size').select_option('15')

            page.locator('#zoom-reset').click()
            expect(globe).to_have_attribute('data-zoom','1.000')
            expect(globe).to_have_attribute('data-detail','continents')
            expect(page.locator('.globe-labels button[data-code]')).to_have_count(0)
            surface=page.locator('#map-window')
            surface.focus()
            page.keyboard.press('ArrowRight')
            expect(globe).not_to_have_attribute('data-rotation','0,-20,0')
            rect=surface.bounding_box()
            before=globe.get_attribute('data-rotation')
            page.mouse.move(rect['x']+rect['width']*.5,rect['y']+rect['height']*.5)
            page.mouse.down()
            page.mouse.move(rect['x']+rect['width']*.65,rect['y']+rect['height']*.55,steps=8)
            page.mouse.up()
            expect(globe).not_to_have_attribute('data-rotation',before)
            page.locator('#atlas-region').select_option('Asia')
            expect(page.locator('#atlas-progress')).to_contain_text('Asia')
            expect(page.locator('.globe-labels button[data-code=CN]')).to_be_visible()
            expect(page.locator('.globe-labels button[data-code=RU]')).to_be_visible()
            page.locator('#country-panel input[type=url]').fill('https://www.instagram.com/stories/highlights/123456789/')
            page.get_by_role('button',name='Save link',exact=True).click()
            expect(page.get_by_role('link',name='Open Instagram ↗')).to_have_attribute('href','https://www.instagram.com/stories/highlights/123456789/')
            image_data=page.evaluate("""() => {const c=document.createElement('canvas');c.width=64;c.height=40;const ctx=c.getContext('2d');ctx.fillStyle='#2f775a';ctx.fillRect(0,0,64,40);return c.toDataURL('image/png').split(',')[1];}""")
            page.locator('#country-panel input[type=file]').set_input_files({'name':'country.png','mimeType':'image/png','buffer':base64.b64decode(image_data)})
            expect(page.locator('#country-panel img')).to_be_visible()
            page.wait_for_function("document.querySelector('#country-panel img').naturalWidth > 0")
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            folder=os.environ.get('BROWSER_ARTIFACT_DIR')
            if folder:
                Path(folder).mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(Path(folder)/f'map-{width}.png'),full_page=True)
                page.get_by_role('button',name='Planner',exact=True).click()
                page.get_by_role('button',name='Month view',exact=True).click()
                page.screenshot(path=str(Path(folder)/f'planner-{width}.png'),full_page=True)
            page.get_by_role('button',name='Journal',exact=True).click()
            page.locator('#cards .card').click()
            page.on('dialog',lambda dialog:dialog.accept())
            page.locator('#delete-place').click()
            expect(page.locator('#cards .card')).to_have_count(0)
            assert not errors
            browser.close()
    finally:
        server.shutdown();worker.join(timeout=5)


@pytest.mark.parametrize('width', [390, 1280])
def test_flat_map_shares_records_and_remembers_view(tmp_path, monkeypatch, width):
    monkeypatch.setenv('PLACES_DB_PATH', str(tmp_path/'flat.sqlite3'))
    import app
    app = importlib.reload(app)
    client = app.app.test_client()
    for code, status in [('GE', 'visited'), ('JP', 'planned'), ('BR', 'wishlist')]:
        assert client.post('/api/places', json=dict(country=code, status=status, place='', notes='',
                           start_date='2026-09-25', end_date='2026-09-27')).status_code == 201
    from werkzeug.serving import make_server
    server = make_server('127.0.0.1', 0, app.app, threaded=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': width, 'height': 900})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            url = f'http://127.0.0.1:{server.server_port}'
            page.goto(url)
            expect = playwright.expect
            svg = page.locator('.world-svg')
            expect(svg).to_have_attribute('data-view', 'globe')
            page.get_by_role('button', name='Flat map', exact=True).click()
            expect(svg).to_have_attribute('data-view', 'flat')
            expect(page.get_by_role('button', name='Flat map', exact=True)).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('#globe-ocean')).to_be_hidden()
            for code, status in [('GE', 'visited'), ('JP', 'planned'), ('BR', 'wishlist')]:
                expect(page.locator(f'path[data-code="{code}"]')).to_have_class(re.compile(status))
            # Opposite sides of the world are available together in the flat view.
            for code in ['US', 'NZ', 'JP', 'BR']:
                assert page.locator(f'path[data-code="{code}"]').get_attribute('d')
            folder = os.environ.get('BROWSER_ARTIFACT_DIR')
            if folder:
                Path(folder).mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(Path(folder)/f'flat-world-{width}.png'), full_page=True)
            for code, name in [('JP', 'Japan'), ('FJ', 'Fiji'), ('MC', 'Monaco')]:
                page.locator('#atlas-search').fill(code)
                page.locator('#atlas-results button').first.click()
                expect(page.locator('#country-panel h2')).to_contain_text(name)
                expect(page.locator('.globe-labels .selected')).to_have_text(name)
                expect(page.locator(f'path[data-code="{code}"]')).to_have_class(re.compile('selected'))
            page.locator('#country-panel').get_by_role('button', name='＋ Add a place', exact=True).click()
            expect(page.locator('select[name=country]')).to_have_value('MC')
            page.locator('#close-dialog').click()
            page.locator('#atlas-region').select_option('Europe')
            expect(svg).to_have_attribute('data-zoom', '2.400')
            before = svg.get_attribute('data-pan')
            surface = page.locator('#map-window')
            surface.focus()
            page.keyboard.press('ArrowRight')
            expect(svg).not_to_have_attribute('data-pan', before)
            rect = surface.bounding_box()
            before = svg.get_attribute('data-pan')
            page.mouse.move(rect['x']+rect['width']*.5, rect['y']+rect['height']*.7)
            page.mouse.down()
            page.mouse.move(rect['x']+rect['width']*.65, rect['y']+rect['height']*.72, steps=8)
            page.mouse.up()
            expect(svg).not_to_have_attribute('data-pan', before)
            zoom = svg.get_attribute('data-zoom')
            page.locator('#zoom-in').click()
            expect(svg).not_to_have_attribute('data-zoom', zoom)
            flat_zoom = svg.get_attribute('data-zoom')
            page.get_by_role('button', name='Globe', exact=True).click()
            expect(svg).to_have_attribute('data-view', 'globe')
            expect(page.locator('#globe-ocean')).to_be_visible()
            expect(page.locator('path[data-code=GE]')).to_have_class(re.compile('visited'))
            page.get_by_role('button', name='Flat map', exact=True).click()
            expect(svg).to_have_attribute('data-zoom', flat_zoom)
            page.locator('#zoom-reset').click()
            expect(svg).to_have_attribute('data-zoom', '1.000')
            expect(svg).to_have_attribute('data-pan', '0,0')
            page.reload()
            expect(svg).to_have_attribute('data-view', 'flat')
            expect(page.locator('#countries-total')).to_have_text('1')
            page.locator('#atlas-search').fill('JP')
            page.locator('#atlas-results button').first.click()
            page.wait_for_function("document.querySelector('.globe-labels .selected')?.textContent === 'Japan'")
            if folder:
                page.screenshot(path=str(Path(folder)/f'flat-country-{width}.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            # Preference failures must not prevent either map from rendering.
            page.add_init_script("Storage.prototype.getItem = function(){throw new Error('blocked')}; Storage.prototype.setItem = function(){throw new Error('blocked')};")
            page.reload()
            expect(svg).to_have_attribute('data-view', 'globe')
            page.get_by_role('button', name='Flat map', exact=True).click()
            expect(svg).to_have_attribute('data-view', 'flat')
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        worker.join(timeout=5)
