#!/bin/bash
# Q-BU 起動ランチャー（Mac用・ダブルクリックで起動）
# このファイルをダブルクリックすると host.py が立ち上がり、ブラウザで先生用QR画面が開く。
cd "$(dirname "$0")" || exit 1

# 先生用QR画面を少し遅らせて自動で開く（サーバ起動を待つ）
( sleep 1; open "http://localhost:8000/admin.html" ) &

# サーバ起動（Ctrl+C か、このウィンドウを閉じると停止）。-u で起動メッセージを即表示
exec python3 -u host.py
