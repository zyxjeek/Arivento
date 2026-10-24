from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import socket,webbrowser,argparse

parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=8765)
parser.add_argument('--bind',default='0.0.0.0')
parser.add_argument('--no-browser',action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parent
file=root/'source.html'
data=file.read_bytes()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split('?')[0] not in ['/', '/index.html']:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data)
    def log_message(self,*args):pass

try:server=ThreadingHTTPServer((args.bind,args.port),Handler)
except OSError as e:raise SystemExit('Port unavailable. Close the other server or use --port 8766. '+str(e))
try:addresses={x[4][0] for x in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET)}
except socket.gaierror:addresses=set()
print('AriventoCreator local editor',flush=True)
print(f'PC: http://127.0.0.1:{args.port}/',flush=True)
for address in sorted(addresses):
    if not address.startswith('127.'):
        print(f'iPad on the same Wi-Fi: http://{address}:{args.port}/',flush=True)
print('Keep this window open. Ctrl+C stops the server.',flush=True)
if not args.no_browser:webbrowser.open(f'http://127.0.0.1:{args.port}/')
try:server.serve_forever()
except KeyboardInterrupt:pass
finally:server.server_close()
