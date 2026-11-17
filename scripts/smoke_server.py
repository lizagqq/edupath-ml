"""Dependency-free HTTP fallback for environments where FastAPI cannot be installed."""
import json
import sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.api.service import Service

service=Service()
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlsplit(self.path);path=parsed.path;q=parse_qs(parsed.query)
        try:
            if path=='/':
                data=(Path(__file__).resolve().parents[1]/'ui/fallback.html').read_bytes()
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if path=='/docs':
                data=b'<h1>EduPath ML fallback API</h1><p>GET /health, /students, /students/{id}/profile, /students/{id}/trajectory, /skills, /materials, /model/info</p><p>Swagger UI requires FastAPI dependencies.</p>'
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if path=='/health':body=service.health()
            elif not service.ready():self.send_json(503,{'detail':'Сначала выполните scripts/build_project.py'});return
            elif path=='/students':body=service.students(min(100,max(1,int(q.get('limit',['20'])[0]))))
            elif path=='/skills':body=service.skills()
            elif path=='/materials':body=service.materials(q.get('skill',[None])[0],q.get('query',[''])[0],min(50,max(1,int(q.get('limit',['3'])[0]))))
            elif path=='/model/info':body=service.info()
            elif path.startswith('/students/') and path.endswith('/profile'):body=service.profile(path.split('/')[2])
            elif path.startswith('/students/') and path.endswith('/trajectory'):body=service.trajectory(path.split('/')[2])
            else:self.send_json(404,{'detail':'Not found'});return
            self.send_json(200,body)
        except KeyError:self.send_json(404,{'detail':'Ученик не найден'})
        except (ValueError,OverflowError):self.send_json(422,{'detail':'Некорректный параметр'})
    def send_json(self,status,obj):
        b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)))
        self.end_headers();self.wfile.write(b)
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
