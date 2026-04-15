# ユーザー登録・管理システム

## 概要
デイサービス施設向けの業務支援システムの一つとして、利用者・スケジュール情報を登録・管理する専用UIアプリです。

同施設向け「入浴表管理ツール（make_bath_table）」との共通DBを使用し、統一的にデータを管理できます。

## 機能
### ユーザー管理
- **ユーザー登録・編集・削除** : 利用者の基本情報（氏名、氏名カナ、性別、長期休中フラグ）を管理
- **一覧表示** : 全ユーザーを性別・名前カナ順で表示
- **削除時の自動処理** : ユーザー削除時にON DELETE CASCADEで関連するスケジュールも自動削除

### スケジュール管理
- **曜日ごとの入浴スケジュール設定** : 月～日の各曜日について以下を設定
  - **入浴区分** : 風呂なし / チェア浴 / 一般浴(手引き) / 一般浴(シャワーキャリー)
  - **メモ** : 特記事項（軟膏の使用など）※任意入力
- **UNIQUE制約** : 1ユーザーにつき曜日ごとに1レコード

### DB設定
- **DB自動検出** : 起動時に既存DBを自動検出（ローカル→ホームディレクトリ順で検索）
- **DBファイル選択** : Dialogで任意のDBファイルを選択可能
- **新規作成** : DBが未作成の場合は自動作成
- **config.json** : 設定は自動保存・読み込み

## 技術構成
- **言語** : Python 3.x
- **GUI** : customtkinter（モダンなデスクトップGUI、darkモード対応）
- **DB** : SQLite 3（dayservice_data.db）
- **開発方針** : make_bath_tableと同一技術スタック

## データベーススキーマ
### m_users テーブル
```sql
CREATE TABLE m_users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_kana TEXT,
    gender INTEGER CHECK(gender IN (1, 2)) NOT NULL,
    is_long_term_absence INTEGER DEFAULT 0
)
```

### m_user_schedules テーブル
```sql
CREATE TABLE m_user_schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    bath_type INTEGER NOT NULL DEFAULT 0,
    bath_memo TEXT,
    FOREIGN KEY (user_id) REFERENCES m_users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, day_of_week)
)
```

**定数値:**
- `gender`: 1=男, 2=女
- `bath_type`: 0=風呂なし, 1=チェア浴, 2=一般浴(手引き), 3=一般浴(シャワーキャリー)
- `day_of_week`: 0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日

## ファイル構成
```
user_registration/
  ├── main.py              # エントリーポイント（設定読込→DB初期化→GUI起動）
  ├── gui.py               # GUI実装（customtkinter）
  ├── logic.py             # ビジネスロジック（DB操作）
  ├── config.py            # 設定管理（JSON形式）＋DB自動検出
  ├── seed_data.py         # テストデータ作成（開発用）
  ├── dayservice_data.db   # SQLiteDB（アプリが自動作成）
  ├── config.json          # 設定ファイル（アプリが自動作成）
  └── README.md            # 本ドキュメント
```

## インストール・実行

### 必要なライブラリ
```bash
pip install customtkinter
```

### 実行
```bash
python main.py
```

## 入力値の検証ルール
- **氏名** : 必須（空白は不可）
- **氏名（カナ）** : 任意
- **性別** : 必須（男 or 女）
- **長期休中フラグ** : 任意（チェックあり=ON）
- **曜日ごとの入浴区分** : 必須
- **メモ** : 任意

## 開発用テストデータ投入

```bash
python seed_data.py
```

`seed_data.py`を実行すると、テスト用の約100件のユーザーデータとスケジュール情報がDBに投入されます。

## 使用しているlibrary

| Library | 用途 |
| --- | --- |
| customtkinter | GUI フレームワーク |
| tkinter | Python標準GUIライブラリ（customtkinterで使用） |
| sqlite3 | DB操作 |
| json | 設定ファイルの読み書き |

## 今後の拡張可能性
- **汎化カラム設計** : m_user_schedulesの`bath_*`プレフィックスは拡張を想定
  - 将来: `toilet_*`（排泄）、`transfer_*`（送迎）などのカラムを追加可能
- **CSV/Excel エクスポート** : ユーザー・スケジュール情報の外部形式への出力
```bash
python main.py
```

## DB スキーマ

### m_users テーブル（ユーザー情報）
| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| user_id | INTEGER | PK AUTOINCREMENT | ユーザーID |
| name | TEXT | NOT NULL | 氏名 |
| name_kana | TEXT | - | 氏名（カナ） |
| gender | INTEGER | CHECK(1,2) | 性別（1:男, 2:女） |
| is_long_term_absence | INTEGER | DEFAULT 0 | 長期休中フラグ（1:休中, 0:在籍） |

### m_user_schedules テーブル（曜日ごとのスケジュール）
| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| schedule_id | INTEGER | PK AUTOINCREMENT | スケジュールID |
| user_id | INTEGER | FK, NOT NULL | ユーザーID |
| day_of_week | INTEGER | CHECK(0-6) NOT NULL | 曜日（0:月 ～ 6:日） |
| bath_type | INTEGER | DEFAULT 0 | 入浴区分（0/1/2/3） |
| bath_memo | TEXT | - | メモ |
| | | UNIQUE(user_id, day_of_week) | 同一ユーザー+曜日は1レコードのみ |

**外部キー制約**
- user_id → m_users(user_id) ON DELETE CASCADE
- ユーザー削除時、関連するスケジュールは自動削除

## マスタデータ定義

### 性別
- 1 : 男
- 2 : 女

### 入浴区分
- 0 : 風呂なし
- 1 : チェア浴
- 2 : 一般浴（手引き）
- 3 : 一般浴（シャワーキャリー）

### 曜日
- 0 : 月
- 1 : 火
- 2 : 水
- 3 : 木
- 4 : 金
- 5 : 土
- 6 : 日

## データ共有
このアプリは、make_bath_table（入浴表管理ツール）と以下のテーブルを共有しています：

- m_users ... 利用者基本情報
- m_user_schedules ... 曜日別スケジュール（入浴情報）

両アプリケーションが同一DBを参照・更新するため、柔軟な業務運用が可能です。

## 設定ファイル（config.json）

起動時に `.../user_registration/config.json` を読み込み、DBパスを取得します。

例:
```json
{
  "db_path": "C:\\Users\\user\\dev\\dayservice\\dayservice_data.db"
}
```

既存のconfig.jsonが無い場合、デフォルトパスを使用します：
```
<アプリケーション実行ディレクトリ>/dayservice_data.db
```

## PyInstaller によるEXE化

make_bath_tableと同様、PyInstaller で単一EXEファイルに変換可能です：
```bash
pyinstaller --onefile --name "ユーザー登録ツール" main.py
```

## トラブルシューティング

### DBファイルが見つかりません
- DBの保存先を「DB変更」ボタンで設定して下さい
- 新規作成する場合は、先にmake_bath_tableで作成するか、本アプリの値が無い状態で起動するとデフォルトパスに生成されます

### 入浴表ツールとデータが同期されない
- 同じDBパスを指定していることを確認してください
- モジュールを再起動して設定を再読み込みしてください

## ライセンス・著作権
内部用業務ツール（make_bath_tableシリーズの一部）
