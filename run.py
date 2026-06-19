#!/usr/bin/env python3
"""transcrub launcher: `python3 run.py` — builds your index if sources.json exists,
serves on localhost only, and opens your browser. No dependencies."""
import os, sys, http.server, socketserver, webbrowser, threading, functools, subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists("sources.json"):
    print("[transcrub] building index from sources.json …")
    subprocess.run([sys.executable, "scan.py"])
else:
    print("[transcrub] no sources.json — using bundled example data")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
url = f"http://localhost:{PORT}/coread.html"
print(f"[transcrub] {url}  (127.0.0.1 only — Ctrl-C to stop)")
threading.Timer(0.8, lambda: webbrowser.open(url)).start()
Handler = functools.partial(http.server.SimpleHTTPRequestHandler)
with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    try: httpd.serve_forever()
    except KeyboardInterrupt: print("\n[transcrub] stopped")
