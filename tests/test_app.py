import os
import tempfile
import unittest

class PlacesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ['PLACES_DB_PATH'] = os.path.join(self.tmp.name, 'places.sqlite3')
        import importlib, app
        self.appmod = importlib.reload(app)
        self.client = self.appmod.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])

    def test_trip_populates_calendar_range(self):
        payload = {
            'country':'GE','place':'Mestia','status':'visited',
            'start_date':'2026-09-28','end_date':'2026-09-30','notes':'Svaneti'
        }
        response = self.client.post('/api/places', json=payload)
        self.assertEqual(response.status_code, 201)
        calendar = self.client.get('/api/calendar/2026').get_json()['days']
        self.assertEqual(set(calendar), {'2026-09-28','2026-09-29','2026-09-30'})
        self.assertEqual(calendar['2026-09-29'][0]['country'], 'GE')

    def test_wishlist_has_no_calendar_days(self):
        payload = {'country':'JP','place':'Tokyo','status':'wishlist','start_date':'2026-01-01','end_date':'2026-01-04','notes':''}
        self.assertEqual(self.client.post('/api/places', json=payload).status_code, 201)
        self.assertEqual(self.client.get('/api/calendar/2026').get_json()['days'], {})

if __name__ == '__main__':
    unittest.main()
