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
            georgia=page.locator('path[data-code="GE"]')
            georgia.focus();page.keyboard.press('Enter')
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
            expect(georgia).to_have_class('visited')
            expect(page.locator('#countries-total')).to_have_text('1')
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
