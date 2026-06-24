# Q-BU（スマホ版）

子ども向けワークショップ用ツール。子どもが各自のスマホで**立方体ブロックを並べて3Dモデルを作り**、送信するとホストPCに集約され、**3Dプリント**して実物を渡します。

- 対象規模：1会場 最大60人 / ローカルWi-Fi / 各自スマホ（iPhone想定）
- 出口：作品JSON → STL → 3Dプリント
- GitHub：`git@github.com:sakiikapk/q-b_test.git`

詳細ドキュメント → **[技術仕様書（仕様書.md）](仕様書.md)** ／ [要件定義.md](要件定義.md) ／ [拡張性設計.md](拡張性設計.md) ／ 作業ログ [開発メモ.md](開発メモ.md)

---

## クイックスタート

必要なもの：**Python 3**（標準ライブラリのみ）。フロントの依存（Three.js / AR.js / QR生成）は `vendor/` に同梱済み＝**インターネット不要**。

### 1. ホストPC（Mac想定）で起動
```bash
python3 host.py
```
または `start.command` をダブルクリック（サーバ起動＋先生用QR画面が自動で開く）。

起動するとターミナルに各URLが表示されます（自己署名HTTPSで配信）：

| 画面 | URL | 用途 |
|---|---|---|
| 先生用QR | `https://<LAN IP>:8000/admin.html` | 子どもに見せる入口QR |
| 子ども用アプリ | `https://<LAN IP>:8000/mock.html` | ブロックを並べて送信 |
| 受信データ確認 | `https://<LAN IP>:8000/data.html` | 届いた作品を一覧・3Dで確認 |

### 2. スマホで開く
`admin.html` のQRをスマホのカメラで読む → `mock.html` が開く → ブロックを並べる →「送信」。

> ⚠️ **カメラAR（ar.html）には「信頼されたHTTPS」が必要**（iOSの制約）。テスト時は下記トンネルが楽です。

---

## 2つのテスト方法（重要）

スマホのカメラ（getUserMedia）は **信頼されたHTTPS** でないと映像が出ません。用途で使い分けます。

| 方法 | 起動 | 証明書 | ネット | 用途 |
|---|---|---|---|---|
| **LAN（自己署名）** | `start.command` / `python3 host.py` | iPhoneに手動インストール要 | 不要 | **本番会場**（オフライン） |
| **トンネル（cloudflared）** | `テスト起動.command` | **不要**（本物の証明書） | 必要 | **開発／テスト**（証明書の手間なし） |

- トンネル版は `brew install cloudflared` が必要。`テスト起動.command` が host＋トンネル＋（QR・受信監視・ARマーカー画像）をまとめて開きます。
- トンネルURLは起動ごとに変わります（アカウント無しのクイックトンネル）。
- ハマりどころ → [仕様書.md](仕様書.md) の「AR/カメラ/HTTPS」。

---

## リポジトリ構成

| ファイル / フォルダ | 役割 |
|---|---|
| [mock.html](mock.html) | **子ども用アプリ**（ブロックを並べる→送信）。Three.js |
| [ar.html](ar.html) | **マーカーAR**（作品をHiroマーカー上に表示・面接着で編集）。AR.js |
| [admin.html](admin.html) | **先生用QR表示**（子どもが読む入口） |
| [data.html](data.html) | **ホスト用 受信データ確認**（一覧・3Dプレビュー・生JSON） |
| [camtest.html](camtest.html) | カメラ事前チェック（AR前の動作確認） |
| [marker.html](marker.html) | **印刷用Hiroマーカー**（約10cm四方） |
| [host.py](host.py) | **ホスト**（静的配信＋受信 `/submit`＋HTTPS自己署名＋LAN情報） |
| [start.command](start.command) | ワンクリック起動（LAN／自己署名版） |
| [テスト起動.command](テスト起動.command) | ワンクリック起動（cloudflaredトンネル版） |
| manifest.json / icon.svg | PWA（「ホーム画面に追加」で全画面アプリ風） |
| vendor/ | 同梱ライブラリ（Three.js / AR.js / QR） |
| submissions/ | 受信データ（1人1JSON・`.gitignore`） |
| [要件定義.md](要件定義.md) ／ [拡張性設計.md](拡張性設計.md) ／ [仕様書.md](仕様書.md) ／ [開発メモ.md](開発メモ.md) | ドキュメント |

---

## データの流れ

```
スマホ(mock.html)            host.py                      ホストPC
  ブロック編集   ──送信──▶  POST /submit  ──保存──▶  submissions/<id>_<時刻>.json
  「ARで見る」                                              │
   → ar.html(マーカー表示)                                  ▼
                              data.htmlで確認 →（将来）STL変換 → 3Dプリント → 子どもに渡す
```

データは前方互換JSON（`schema: "qbu.creation/1"`）。スキーマ詳細は [仕様書.md](仕様書.md)。

---

## 現在の状態・TODO

最新は [開発メモ.md](開発メモ.md) を参照。要点：

- ✅ 子ども用アプリ／送信／ホスト／受信確認(data.html)／マーカーAR（実機でカメラ表示OK）
- 🔧 AR表示の微調整（立方体の歪み・微妙な傾き）が残課題
- ⬜ STL生成（JSON→STL、3Dプリントの出口）
- ⬜ 複数色 → GLB → AR の拡張（[拡張性設計.md](拡張性設計.md)）

---

## 開発の約束ごと

- フロントは **ローカル同梱（ネット不要）** を維持する。
- データは **前方互換** を壊さない（受信側は未知フィールドも保持）。
- 秘密鍵 `key.pem` は **絶対にコミットしない**（`.gitignore` 済み・配信も403）。
