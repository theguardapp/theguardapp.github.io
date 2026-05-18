#!/usr/bin/env python3
"""
QA full-page screenshot tool for theguardapp.github.io.

Captures the site at any viewport width using Chromium's DevTools Protocol.
Bypasses Chromium-on-Linux's ~500 px minimum window-size by using
`Emulation.setDeviceMetricsOverride`, so we can verify true 320/360 px
phone layouts. Lazy-loaded images are force-eager'd and IntersectionObserver
reveal targets are pre-visible so the resulting PNG shows the FULL page in
its final state (not the entry animation).

Usage:
    scripts/qa_screenshot.py <width> <url> <out.png>
    scripts/qa_screenshot.py 360 http://127.0.0.1:8765/index.html /tmp/idx_360.png
    scripts/qa_screenshot.py 1440 http://127.0.0.1:8765/about.html /tmp/about_desktop.png

Requirements:
    - chromium (or google-chrome) on PATH
    - python3-websockets (Debian/Kali) or `pip install websockets`

The script picks an unused debug port automatically and cleans up the
profile dir on exit.
"""
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

try:
    import websockets
except ImportError:
    sys.exit("missing dependency: install with `apt install python3-websockets` "
             "or `pip install websockets`")


def _free_port() -> int:
    """Find an unused TCP port on localhost."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def capture(width: int, url: str, out_path: str,
                  *, height: int = 800, max_height: int = 14000,
                  settle_seconds: float = 3.0) -> None:
    """Capture a full-page PNG of `url` rendered at `width` × `height`."""
    port = _free_port()
    profile = f"/tmp/chrome-qa-{os.getpid()}"
    chrome = subprocess.Popen(
        [
            "chromium", "--headless=new", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}", "about:blank",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        # Wait for the debug endpoint to be reachable
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=0.5)
                break
            except Exception:
                await asyncio.sleep(0.2)

        info = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json").read())
        target = next(t for t in info if t.get("type") == "page")
        ws_url = target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=20 * 1024 * 1024) as ws:
            mid = [0]

            async def call(method: str, params: dict | None = None):
                mid[0] += 1
                this_id = mid[0]
                await ws.send(json.dumps({"id": this_id, "method": method, "params": params or {}}))
                while True:
                    msg = json.loads(await ws.recv())
                    if msg.get("id") == this_id:
                        return msg

            await call("Emulation.setDeviceMetricsOverride", {
                "width": width, "height": height,
                "deviceScaleFactor": 1, "mobile": True,
                "screenWidth": width, "screenHeight": height,
            })
            await call("Page.enable")
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(settle_seconds)

            # Force lazy images to load eagerly + mark every reveal target as
            # visible so the screenshot captures the page's resting layout.
            # IMPORTANT: do NOT reset img.src — that breaks <picture> source
            # selection (the browser will load the JPEG fallback instead of
            # the AVIF/WebP that <picture><source type=...> would have picked).
            # Just flipping loading="eager" is enough to trigger the load.
            await call("Runtime.evaluate", {"expression": (
                'document.querySelectorAll(\'img[loading="lazy"]\').forEach('
                'i => { i.loading = "eager"; });'
                'document.querySelectorAll(".reveal,.features-grid,.use-grid,'
                '.principles,.spotlight-row").forEach(e => e.classList.add("visible"));'
            )})

            # Wait until every image is fully decoded. AVIF decoding inside
            # <picture> is async on Chromium headless, so we also explicitly
            # await `img.decode()` for each image and then settle one extra
            # animation frame before snapping.
            for _ in range(40):
                r = await call("Runtime.evaluate", {
                    "expression": "Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)",
                    "returnByValue": True,
                })
                if r["result"]["result"]["value"]:
                    break
                await asyncio.sleep(0.3)
            await call("Runtime.evaluate", {
                "expression": "Promise.all(Array.from(document.images).map(i => i.decode().catch(() => {})))",
                "awaitPromise": True,
            })
            # Two animation frames to let the paint pipeline catch up.
            await call("Runtime.evaluate", {
                "expression": "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))",
                "awaitPromise": True,
            })
            await asyncio.sleep(0.4)

            r = await call("Runtime.evaluate", {
                "expression": "document.documentElement.scrollHeight",
                "returnByValue": True,
            })
            doc_h = min(r["result"]["result"]["value"], max_height)

            res = await call("Page.captureScreenshot", {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {"x": 0, "y": 0, "width": width, "height": doc_h, "scale": 1},
            })
            with open(out_path, "wb") as fh:
                fh.write(base64.b64decode(res["result"]["data"]))
            print(f"OK {out_path} ({width}x{doc_h})")
    finally:
        chrome.terminate()
        chrome.wait()
        subprocess.call(["rm", "-rf", profile])


def _main() -> None:
    if len(sys.argv) < 4:
        sys.exit(f"usage: {sys.argv[0]} <width> <url> <out.png>")
    width = int(sys.argv[1])
    url = sys.argv[2]
    out_path = sys.argv[3]
    asyncio.run(capture(width, url, out_path))


if __name__ == "__main__":
    _main()
