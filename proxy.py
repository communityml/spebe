#!/usr/bin/env python3
"""
Spelling Bee Proxy (spebe)
- Reads ANTHROPIC_API_KEY from environment variable
- Serves the HTML file and forwards /api/claude requests to Anthropic
- Works locally and on Render

Local usage:
    set ANTHROPIC_API_KEY=sk-ant-...   (Windows)
    export ANTHROPIC_API_KEY=sk-ant-... (Mac/Linux)
    python proxy.py

On Render:
    Set ANTHROPIC_API_KEY in the Render dashboard environment variables.
    Render sets PORT automatically; this script reads it.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.error
import json
import os

PORT = int(os.environ.get("PORT", 8080))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY environment variable is not set!")
    print("  Windows: set ANTHROPIC_API_KEY=sk-ant-...")
    print("  Mac/Linux: export ANTHROPIC_API_KEY=sk-ant-...")


class ProxyHandler(SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        if args and str(args[1]) not in ('200', '304'):
            print(f"  {args[0]} -> {args[1]}")

    def do_GET(self):
        if self.path == '/':
            self.send_response(302)
            self.send_header('Location', '/spelling-bee.html')
            self.end_headers()
        else:
            super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/claude":
            self._proxy_to_anthropic()
        else:
            self.send_error(404)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _proxy_to_anthropic(self):
        if not ANTHROPIC_API_KEY:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "ANTHROPIC_API_KEY not set"}).encode())
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        req = urllib.request.Request(
            ANTHROPIC_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(data)
                print(f"  ✓ Anthropic API call succeeded")

        except urllib.error.HTTPError as e:
            error_body = e.read()
            print(f"  ✗ Anthropic API error {e.code}: {error_body.decode()}")
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(error_body)

        except Exception as e:
            print(f"  ✗ Proxy error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print(f"\n🐝 Spelling Bee Proxy (spebe)")
    print(f"   Port:      {PORT}")
    print(f"   API key:   {'✓ set' if ANTHROPIC_API_KEY else '✗ NOT SET'}")
    print(f"   Files:     {os.getcwd()}")
    print(f"   Open:      http://localhost:{PORT}/")
    print(f"   Press Ctrl+C to stop.\n")

    server = HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
