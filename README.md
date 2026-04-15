# ユーザー登録・管理システム

## 概要

デイサービス施設向けの業務支援システムの一つとして、利用者・スケジュール情報を登録・管理する専用UIアプリです。

同施設向け「入浴表作成ツール（make_bath_table）」との共通DBを使用し、統一的にデータを管理できます。

## 機能

### ユーザー管理
- **ユーザー登録・編集・削除** : 利用者の基本情報（氏/名、氏名カナ、性別、長期休中フラグ）を管理
- **一覧表示** : 全ユーザーを性別・名前カナ順で表示。ステータス列に「長期休中」「臨時適用中」を表示
- **リアルタイム検索** : 氏名・カナで一覧をリアルタイム絞り込み
- **重複チェック** : 同姓同名のユーザーが既に登録されている場合に確認ダイアログを表示
- **削除時の自動処理** : ユーザー削除時に ON DELETE CASCADE で関連スケジュールも自動削除

### 通常スケジュール管理
- **曜日ごとの入浴スケジュール設定** : 月〜日の各曜日について以下を設定
  - **入浴区分** : 風呂なし / チェア浴 / 一般浴(手引き) / 一般浴(シャワーキャリー)
  - **メモ** : 特記事項（軟膏の使用など）※任意入力
- **UNIQUE制約** : 1ユーザーにつき曜日ごとに1レコード

### 臨時スケジュール管理
- **1ユーザーにつき1件** の臨時スケジュールを設定可能（上書き登録）
- **適用期間** : 開始日〜終了日（終了日省略で1日のみ）
- **曜日ごとに設定** : 入浴区分・メモ・休みフラグを通常スケジュールとは独立して設定
  - 臨時に含まれている曜日 → 臨時の設定を使用（入浴区分・メモ・休みフラグ）
  - 臨時に含まれていない曜日 → 通常スケジュールをそのまま使用
- **休みフラグ** : 曜日ごとにチェック可能。Excelに「休」を赤字で出力（長期休中と同じ表示）
- **自動削除** : アプリ起動時に期限切れの臨時スケジュールを自動削除
- **臨時一覧ダイアログ** : メイン画面の「臨時一覧」ボタンから有効な全臨時スケジュールを確認可能

### DB設定
- **DB自動検出** : 起動時に既存DBを自動検出（ローカル→ホームディレクトリ順で検索）
- **DBファイル選択** : ダイアログで任意のDBファイルを選択可能
- **新規作成** : DBが未作成の場合は自動作成
- **config.json** : 設定は自動保存・読み込み

## 入力値の検証ルール

| 項目 | 必須 | 制約 |
|---|---|---|
| 氏 | ✅ | 空白不可 |
| 名 | - | 任意 |
| 氏（カナ） | ✅ | カタカナのみ（長音符・中点含む） |
| 名（カナ） | - | 入力する場合はカタカナのみ |
| 性別 | ✅ | 男 or 女 |
| 長期休中フラグ | - | チェックあり=ON |
| 来所曜日 | ✅ | 1日以上選択 |
| 入浴区分 | ✅ | 曜日ごとに選択 |
| メモ | - | 任意 |

## 技術構成

| 要素 | 内容 |
|---|---|
| 言語 | Python 3.x |
| GUI | customtkinter（モダンなデスクトップGUI、ダークモード対応） |
| DB | SQLite3（dayservice_data.db） |
| テスト | unittest（test_logic.py） |

## ファイル構成

```
user_registration/
  ├── main.py              # エントリーポイント（設定読込 → DB初期化 → GUI起動）
  ├── gui.py               # GUI実装（customtkinter）
  ├── logic.py             # ビジネスロジック（DB操作・バリデーション）
  ├── config.py            # 設定管理（JSON形式）＋ DB自動検出
  ├── test_logic.py        # ユニットテスト（unittest）
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

### テスト実行
```bash
python -m unittest test_logic -v
```

### EXEビルド（PyInstaller）
```bash
pyinstaller --onefile --noconsole --name "ユーザー登録ツール" main.py
```

## データベーススキーマ

### m_users（ユーザー情報）

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| user_id | INTEGER | PK AUTOINCREMENT | ユーザーID |
| name | TEXT | NOT NULL | 氏名（互換用: 「氏 名」結合値） |
| name_kana | TEXT | - | 氏名カナ（互換用: 結合値） |
| last_name | TEXT | NOT NULL DEFAULT '' | 氏 |
| first_name | TEXT | NOT NULL DEFAULT '' | 名 |
| last_name_kana | TEXT | - | 氏（カナ） |
| first_name_kana | TEXT | - | 名（カナ） |
| gender | INTEGER | CHECK(1,2) | 性別（1:男, 2:女） |
| is_long_term_absence | INTEGER | DEFAULT 0 | 長期休中フラグ（1:休中, 0:在籍） |

### m_user_schedules（通常スケジュール）

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| schedule_id | INTEGER | PK AUTOINCREMENT | スケジュールID |
| user_id | INTEGER | FK NOT NULL | ユーザーID |
| day_of_week | INTEGER | CHECK(0-6) NOT NULL | 曜日（0:月〜6:日） |
| bath_type | INTEGER | DEFAULT 0 | 入浴区分 |
| bath_memo | TEXT | - | メモ |
| | | UNIQUE(user_id, day_of_week) | 同一ユーザー+曜日は1レコード |

外部キー: `user_id → m_users(user_id) ON DELETE CASCADE`

### m_user_temp_schedules（臨時スケジュールヘッダー）

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| temp_id | INTEGER | PK AUTOINCREMENT | 臨時スケジュールID |
| user_id | INTEGER | FK NOT NULL UNIQUE | ユーザーID（1ユーザー1件） |
| start_date | TEXT | NOT NULL | 開始日（YYYY-MM-DD） |
| end_date | TEXT | - | 終了日（NULL=1日のみ） |

外部キー: `user_id → m_users(user_id) ON DELETE CASCADE`

### m_user_temp_schedule_days（臨時スケジュール曜日明細）

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| day_id | INTEGER | PK AUTOINCREMENT | 明細ID |
| temp_id | INTEGER | FK NOT NULL | 臨時スケジュールID |
| day_of_week | INTEGER | CHECK(0-6) NOT NULL | 曜日（0:月〜6:日） |
| bath_type | INTEGER | DEFAULT 0 | 入浴区分 |
| bath_memo | TEXT | DEFAULT '' | メモ |
| is_absence | INTEGER | DEFAULT 0 | 休みフラグ（1:休み） |
| | | UNIQUE(temp_id, day_of_week) | 同一臨時スケジュール+曜日は1レコード |

外部キー: `temp_id → m_user_temp_schedules(temp_id) ON DELETE CASCADE`

## マスタデータ定義

### 性別
| 値 | 意味 |
|---|---|
| 1 | 男 |
| 2 | 女 |

### 入浴区分（bath_type）
| 値 | 意味 |
|---|---|
| 0 | 風呂なし |
| 1 | チェア浴 |
| 2 | 一般浴（手引き） |
| 3 | 一般浴（シャワーキャリー） |

### 曜日（day_of_week）
| 値 | 意味 |
|---|---|
| 0 | 月 |
| 1 | 火 |
| 2 | 水 |
| 3 | 木 |
| 4 | 金 |
| 5 | 土 |
| 6 | 日 |

## 設定ファイル（config.json）

起動時に `user_registration/config.json` を読み込みDBパスを取得します。

```json
{
  "db_path": "C:\\Users\\user\\dev\\dayservice\\dayservice_data.db"
}
```

config.json が存在しない場合はデフォルトパス（実行ディレクトリ直下）を使用します。

## データ共有

make_bath_table と以下のテーブルを共有します（同一DBファイルを参照）。

- `m_users` : 利用者基本情報
- `m_user_schedules` : 曜日別スケジュール
- `m_user_temp_schedules` : 臨時スケジュールヘッダー
- `m_user_temp_schedule_days` : 臨時スケジュール曜日明細

## 開発用テストデータ投入

```bash
python seed_data.py
```

約100件のユーザーデータとスケジュール情報がDBに投入されます。

## トラブルシューティング

### DBファイルが見つかりません
- 「DB変更」ボタンで保存先を指定してください。
- 新規作成する場合は「新規作成」ボタンを使用するか、make_bath_table 側でDBを先に作成してください。

### 入浴表ツールとデータが同期されない
- 両アプリが同一のDBファイルパスを参照していることを確認してください。

## ライセンス・著作権

内部用業務ツール（make_bath_table シリーズの一部）
