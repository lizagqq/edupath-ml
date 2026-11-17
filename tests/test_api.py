"""HTTP handler routing checks without opening sockets (blocked in this sandbox)."""
import io
import json
import unittest
from scripts.smoke_server import Handler
from src.api.service import Service

def call(path):
    h=Handler.__new__(Handler);h.path=path;h.wfile=io.BytesIO();result={}
    h.send_response=lambda code:result.update(status=code)
    h.send_header=lambda key,value:None
    h.end_headers=lambda:None
    h.do_GET()
    return result['status'],h.wfile.getvalue()

class APITests(unittest.TestCase):
    def test_endpoints(self):
        uid=Service().students(1)[0]
        self.assertEqual(json.loads(call('/health')[1])['status'],'ok')
        self.assertGreater(len(json.loads(call('/skills')[1])),0)
        self.assertEqual(len(json.loads(call('/students?limit=2')[1])),2)
        self.assertGreater(len(json.loads(call(f'/students/{uid}/profile')[1])['skills']),0)
        self.assertGreater(len(json.loads(call(f'/students/{uid}/trajectory')[1])['trajectory']),0)
        skill='47' if Service().info()['dataset'].startswith('ASSISTments') else 'percent'
        self.assertTrue(json.loads(call(f'/materials?skill={skill}')[1]))
        self.assertIn('metrics',json.loads(call('/model/info')[1]))
    def test_invalid_requests(self):
        self.assertEqual(call('/students/missing/profile')[0],404)
        self.assertEqual(call('/students?limit=abc')[0],422)
        self.assertEqual(call('/nope')[0],404)
    def test_web_ui_and_docs(self):
        self.assertIn(b'EduPath ML',call('/')[1])
        self.assertIn(b'/health',call('/docs')[1])

if __name__=='__main__':unittest.main()
