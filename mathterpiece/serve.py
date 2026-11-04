"""mtp serve (docs/data-model.md, "The mtp command"): builds a figure, serves its page on the
author's machine, and builds again and reloads the page whenever the source file is saved. A build
that fails shows its error on the page until the next save."""

import html
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mathterpiece.build import BuildError, about, build, page
from mathterpiece.compiler import CompileError
from mathterpiece.parse import ParseError

# The page asks for the build's number and reloads when it changes.
RELOAD = """<script>
  let seen = null;
  setInterval(async () => {
    try {
      const now = await (await fetch("/version")).text();
      if (seen !== null && now !== seen) location.reload();
      seen = now;
    } catch {}
  }, 400);
</script>"""


class Server:
    def __init__(self, path: Path, port: int = 8000):
        self.path = Path(path)
        self.version = 0
        self.html = ""
        self.mtime = -1.0
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                with server.lock:
                    body = str(server.version) if self.path == "/version" else server.html
                data = body.encode()
                self.send_response(200)
                self.send_header(
                    "Content-Type", "text/plain" if self.path == "/version" else "text/html"
                )
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, format, *args):
                pass

        self.http = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.port = self.http.server_address[1]
        self.check()

    def check(self) -> None:
        """Builds again if the source changed since the last build."""
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            return
        with self.lock:
            if mtime == self.mtime:
                return
            self.mtime = mtime
            try:
                out = build(self.path)
                mtpc = (out / f"{self.path.stem}.mtpc").read_text(encoding="utf-8")
                js = (out / "mathterpiece.js").read_text(encoding="utf-8")
                text = about(self.path.read_text(encoding="utf-8"))
                self.html = page(self.path.stem, mtpc, js, text, RELOAD)
            except (ParseError, CompileError, BuildError, OSError) as e:
                self.html = _error_page(self.path.name, f"{self.path.name}:{e}")
            self.version += 1

    def start(self) -> None:
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        threading.Thread(target=self._watch, daemon=True).start()

    def _watch(self) -> None:
        while not self.stopped.wait(0.25):
            self.check()

    def stop(self) -> None:
        self.stopped.set()
        self.http.shutdown()
        self.http.server_close()


def _error_page(name: str, message: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(name)}</title></head>
<body style="font-family: system-ui, sans-serif; margin: 2rem">
<h1>{html.escape(name)}</h1>
<pre style="color: #a33; white-space: pre-wrap">{html.escape(message, quote=False)}</pre>
<p>Save the file again to build it.</p>
{RELOAD}
</body></html>
"""
