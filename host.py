#!/usr/bin/env python3
# Q-BU 簡易ホスト
#   - アプリ配信（GET, 静的ファイル）
#   - 送信受け口（POST /submit → submissions/ にJSON保存）
#   - AR用USDZ保存（POST /ar）
#   - LAN情報（GET /lan）= QR表示ページ用
#   - HTTPS配信（自己署名証明書を自動生成）= カメラAR(getUserMedia)に必須
# 標準ライブラリのみ・依存ゼロ（証明書生成だけ openssl を使用）。
#   起動:  python3 host.py
import json, os, time, socket, mimetypes, ssl, subprocess, tempfile
from urllib.parse import urlsplit, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)                                   # 配信元をこのファイルの場所に固定
SAVE_DIR = os.path.join(ROOT, "submissions")
AR_DIR = os.path.join(ROOT, "ar_tmp")            # AR用USDZの一時置き場
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(AR_DIR, exist_ok=True)
mimetypes.add_type("model/vnd.usdz+zip", ".usdz")  # iOSのAR Quick Lookが認識するMIME
mimetypes.add_type("application/x-x509-ca-cert", ".pem")  # iOSが証明書を「インストール」と認識するMIME
PORT = 8000

CERT = os.path.join(ROOT, "cert.pem")
KEY  = os.path.join(ROOT, "key.pem")
CERT_IP = os.path.join(ROOT, ".cert_ip")         # 証明書を発行したIPを記録（IP変更で再発行）
SCHEME = "http"                                  # 起動時に https / http を確定

def lan_ip():
    """会場LANでこのMacに振られているIPを推定する（インターネット接続は不要）。
    8.8.8.8 へ "つなぐ用意" をするだけで実際の通信はしない＝ローカルIPが取れる。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"                         # 取れなければループバック
    finally:
        s.close()
    return ip

def ensure_cert(ip):
    """自己署名CA証明書(cert.pem/key.pem)を用意する。現在のLAN IPをSANに含める。
    既に同じIP用があれば再利用。openssl が無ければ False（→http配信にフォールバック）。"""
    if all(os.path.exists(p) for p in (CERT, KEY, CERT_IP)):
        try:
            if open(CERT_IP).read().strip() == ip:
                return True
        except Exception:
            pass
    cnf = ("[req]\ndistinguished_name = dn\nx509_extensions = v3\nprompt = no\n"
           "[dn]\nCN = Q-BU Local\n"
           "[v3]\nbasicConstraints = critical, CA:TRUE\n"
           "keyUsage = critical, keyCertSign, digitalSignature\n"
           "subjectAltName = IP:%s, IP:127.0.0.1, DNS:localhost\n" % ip)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False)
    tmp.write(cnf); tmp.close()
    try:
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                        "-keyout", KEY, "-out", CERT, "-days", "825", "-config", tmp.name],
                       check=True, capture_output=True)
        with open(CERT_IP, "w") as f:
            f.write(ip)
        return True
    except Exception as e:
        print("  証明書の生成に失敗（http配信にします）:", e)
        return False
    finally:
        os.unlink(tmp.name)

class Handler(SimpleHTTPRequestHandler):
    # --- POST: /submit（作品JSON保存） と /ar（AR用USDZ保存） ---
    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/submit":
            self._do_submit()
        elif path == "/ar":
            self._do_ar()
        else:
            self.send_error(404, "not found")

    def _do_submit(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self.send_error(400, "bad json"); return
        sid = str(data.get("id", data.get("creator", {}).get("id", "noid"))).replace("/", "_").replace("\\", "_")
        ts = time.strftime("%Y%m%d-%H%M%S")
        fname = "%s_%s.json" % (sid, ts)
        # 受信JSONは「そのまま」保存する＝未知フィールドも保持（前方互換の肝）
        with open(os.path.join(SAVE_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        blocks = (data.get("model") or {}).get("blocks", data.get("blocks", []))
        print("  受信 →", fname, "| blocks:", len(blocks))
        self._json(200, {"ok": True, "saved": fname})

    def _do_ar(self):
        # iPhone AR Quick Look 用の USDZ を一時保存し、本物のURLを返す（blob:より確実）
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        q = parse_qs(urlsplit(self.path).query)
        sid = str(q.get("id", ["model"])[0]).replace("/", "_").replace("\\", "_")
        fname = sid + ".usdz"
        with open(os.path.join(AR_DIR, fname), "wb") as f:
            f.write(raw)
        self._json(200, {"ok": True, "url": "/ar_tmp/" + fname})

    # --- GET: /lan は LAN情報、秘密鍵は配信拒否、それ以外は静的ファイル配信 ---
    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/key.pem", "/.cert_ip"):
            self.send_error(403, "forbidden"); return       # 秘密鍵は絶対に渡さない
        if path == "/lan":
            ip = lan_ip()
            self._json(200, {"ip": ip, "port": PORT, "scheme": SCHEME,
                             "appUrl": "%s://%s:%d/mock.html" % (SCHEME, ip, PORT)})
            return
        super().do_GET()

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
    ip = lan_ip()
    SCHEME = "https" if ensure_cert(ip) else "http"
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    if SCHEME == "https":
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT, KEY)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    line = "=" * 56
    print(line)
    print("  Q-BU host 起動中  (%s)" % SCHEME.upper())
    print(line)
    print("  ▼ 先生用（このMacの画面でQRを出す）")
    print("      %s://%s:%d/admin.html" % (SCHEME, ip, PORT))
    print()
    print("  ▼ 子ども用（QRを読むとここが開く / 直接入力もOK）")
    print("      %s://%s:%d/mock.html" % (SCHEME, ip, PORT))
    if SCHEME == "https":
        print()
        print("  ▼ カメラAR用：iPhoneで最初に証明書をインストール")
        print("      %s://%s:%d/cert.pem" % (SCHEME, ip, PORT))
        print("      （プロファイル導入 → 設定>一般>情報>証明書信頼設定 で信頼をON）")
        print()
        print("  ※ 初回は「安全ではない接続」警告が出ます（自己署名のため）。")
    print()
    print("  受信データ : ./submissions/ に1人1ファイルで保存")
    print("  終了する   : Ctrl + C")
    print(line)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  停止しました。")
