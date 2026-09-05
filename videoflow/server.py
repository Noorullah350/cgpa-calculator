from http.server import BaseHTTPRequestHandler, HTTPServer
import json, subprocess, urllib.parse, os

HOST = "127.0.0.1"
PORT = 8765
DOWNLOAD_DIR = os.path.expanduser("~/storage/downloads")

class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/":
            self.send_json({"success": True, "service": "VideoFlow", "status": "running"})
            return

        if parsed.path == "/info":
            url = params.get("url", [""])[0]

            if not url:
                self.send_json({"success": False, "message": "URL is required."}, 400)
                return

            try:
                result = subprocess.run(
                    ["yt-dlp", "--dump-single-json", "--skip-download", "--no-playlist", url],
                    capture_output=True, text=True, timeout=60
                )

                if result.returncode != 0:
                    self.send_json({"success": False, "message": result.stderr[-2000:]}, 400)
                    return

                data = json.loads(result.stdout)

                heights = sorted(set(
                    int(f["height"])
                    for f in data.get("formats", [])
                    if f.get("height")
                ))

                self.send_json({
                    "success": True,
                    "title": data.get("title", "Video"),
                    "thumbnail": data.get("thumbnail", ""),
                    "source": data.get("extractor_key", "Unknown"),
                    "format": data.get("ext", "video"),
                    "duration": data.get("duration", 0),
                    "qualities": [{"quality": f"{h}p"} for h in heights]
                })

            except subprocess.TimeoutExpired:
                self.send_json({"success": False, "message": "Request timed out."}, 504)

            except Exception as e:
                self.send_json({"success": False, "message": str(e)}, 500)

            return

        if parsed.path == "/download":
            url = params.get("url", [""])[0]
            quality = params.get("quality", ["best"])[0]

            if not url:
                self.send_json({"success": False, "message": "URL is required."}, 400)
                return

            os.makedirs(DOWNLOAD_DIR, exist_ok=True)

            if quality == "best":
                fmt = "bv*+ba/b"
            else:
                try:
                    height = int(quality.replace("p", ""))
                    fmt = f"bv*[height<={height}]+ba/b[height<={height}]"
                except:
                    fmt = "bv*+ba/b"

            output = os.path.join(
                DOWNLOAD_DIR,
                "VideoFlow_%(title)s.%(ext)s"
            )

            try:
                result = subprocess.run(
                    [
                        "yt-dlp",
                        "--no-playlist",
                        "-f", fmt,
                        "--merge-output-format", "mp4",
                        "-o", output,
                        url
                    ],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode != 0:
                    self.send_json({
                        "success": False,
                        "message": result.stderr[-2500:]
                    }, 500)
                    return

                self.send_json({
                    "success": True,
                    "message": "Download completed.",
                    "folder": DOWNLOAD_DIR
                })

            except subprocess.TimeoutExpired:
                self.send_json({
                    "success": False,
                    "message": "Download timed out."
                }, 504)

            except Exception as e:
                self.send_json({
                    "success": False,
                    "message": str(e)
                }, 500)

            return

        self.send_json({
            "success": False,
            "message": "Endpoint not found."
        }, 404)

    def log_message(self, format, *args):
        print(format % args)

print(f"VideoFlow bridge running on http://{HOST}:{PORT}")

server = HTTPServer((HOST, PORT), Handler)
server.serve_forever()
