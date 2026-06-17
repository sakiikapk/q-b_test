#!/usr/bin/env python3
# Q-BU 簡易ホスト
#   - アプリ配信（GET, 静的ファイル）
#   - 送信受け口（POST /submit → submissions/ にJSON保存）
# を1ファイルで両方やる。標準ライブラリのみ・依存ゼロ。
#   起動:  python3 host.py
import json, os, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)                                   # 配信元をこのファイルの場所に固定
SAVE_DIR = os.path.join(ROOT, "submissions")
os.makedirs(SAVE_DIR, exist_ok=True)
PORT = 8000

class Handler(SimpleHTTPRequestHandler):
    # --- 送信受け口 ---
    def do_POST(self):
        if self.path != "/submit":
            self.send_error(404, "not found"); return
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self.send_error(400, "bad json"); return
        sid = str(data.get("id", "noid")).replace("/", "_").replace("\\", "_")
        ts = time.strftime("%Y%m%d-%H%M%S")
        fname = "%s_%s.json" % (sid, ts)
        # 受信JSONは「そのまま」保存する＝未知フィールドも保持（前方互換の肝）
        with open(os.path.join(SAVE_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        blocks = (data.get("model") or {}).get("blocks", data.get("blocks", []))
        print("  受信 →", fname, "| blocks:", len(blocks))
        self._json(200, {"ok": True, "saved": fname})

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")   # 常に最新を配信（リロード地獄を防ぐ）
        super().end_headers()

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print("Q-BU host 起動")
    print("  アプリ : http://localhost:%d/mock.html" % PORT)
    print("  受信   : POST /submit  → 保存先 ./submissions/")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
