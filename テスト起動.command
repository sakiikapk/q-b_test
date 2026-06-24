#!/bin/bash
# Q-BU テスト起動（トンネル）— Mac用・ダブルクリックで起動
#   host.py + cloudflaredトンネルを立ち上げ、
#   ① 子ども用QR(admin) ② 受信監視(data) ③ ARマーカー画像(hiro.jpg) をまとめて開く。
#   → カメラARを「iPhoneでの証明書インストールなし」で実機テストするための起動セット。
#   ※インターネット必須。オフライン会場では start.command（LAN/自己署名）を使う。
cd "$(dirname "$0")" || exit 1

echo "============================================"
echo "  Q-BU テスト起動（トンネル）"
echo "============================================"

# 多重起動・ポート衝突を防ぐため、前回の host / tunnel を掃除
pkill -f "host.py"            2>/dev/null
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 1

# 終了処理：Ctrl+C / このウィンドウを閉じる で host と tunnel を止める
trap 'printf "\n停止中...\n"; kill "$HOST_PID" "$TUN_PID" 2>/dev/null; exit 0' INT TERM HUP

# 1) host.py（HTTPS配信）を起動
python3 -u host.py > host.log 2>&1 &
HOST_PID=$!

# 2) cloudflared が無ければ LAN(自己署名) で開いて終了
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared が未インストール → LAN(自己署名)で開きます。"
  echo "（証明書なしテストにするには: brew install cloudflared）"
  ( sleep 1.5
    open "https://localhost:8000/admin.html"
    open "https://localhost:8000/data.html"
    open "vendor/arjs/hiro.jpg" ) &
  echo "停止: このウィンドウで Ctrl+C"
  wait "$HOST_PID"
  exit 0
fi

# 3) トンネル起動 → 公開URL（*.trycloudflare.com）が出るまで待つ（最大30秒）
: > tunnel.log
cloudflared tunnel --url https://localhost:8000 --no-tls-verify > tunnel.log 2>&1 &
TUN_PID=$!

printf "トンネル準備中"
URL=""
for i in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' tunnel.log | head -1)
  [ -n "$URL" ] && break
  printf "."; sleep 0.5
done
printf "\n"

if [ -z "$URL" ]; then
  echo "⚠️ トンネルURLを取得できませんでした。LANで開きます（tunnel.log を確認）。"
  URL="https://localhost:8000"
fi

# 4) セットで開く：QR / 受信監視 / ARマーカー画像
open "$URL/admin.html"       # 子ども用QR（この画面を子どもに見せる）
open "$URL/data.html"        # 受信監視（届いた作品が NEW で出る）
open "vendor/arjs/hiro.jpg"  # ARマーカー（これをカメラに見せると作品が出る）

cat <<EOF

================ 起動しました ================
 子ども用QR : $URL/admin.html   ← この画面を子どもに見せる
 受信監視   : $URL/data.html
 ARマーカー : vendor/arjs/hiro.jpg（Previewで開いた画像をカメラに見せる）
 直接AR     : $URL/ar.html
 子供アプリ : $URL/mock.html
----------------------------------------------
 ※ トンネルURLは起動ごとに変わります
 停止 : このウィンドウで Ctrl+C（host と tunnel を止めます）
==============================================
EOF

# ウィンドウを開いたまま待機（Ctrl+C / 閉じる で全停止）
wait
