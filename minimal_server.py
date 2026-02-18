"""Minimal health check server for Render deployment verification."""
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "service": "raincheck-api"}).encode())
    
    def log_message(self, format, *args):
        print(f"[REQUEST] {args[0]}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting minimal server on port {port}")
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Server listening on 0.0.0.0:{port}")
    server.serve_forever()
