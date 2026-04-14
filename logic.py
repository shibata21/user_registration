import sqlite3
import os
import re

_KATAKANA_RE = re.compile(r'^[ァ-ヶーヴ・\s]+$')

def _validate_name(last_name, last_name_kana, first_name_kana):
    if not (last_name or "").strip():
        raise ValueError("氏は必須です")
    if not (last_name_kana or "").strip():
        raise ValueError("氏（カナ）は必須です")
    if not _KATAKANA_RE.match(last_name_kana.strip()):
        raise ValueError("氏（カナ）はカタカナで入力してください")
    if first_name_kana and (first_name_kana or "").strip():
        if not _KATAKANA_RE.match(first_name_kana.strip()):
            raise ValueError("名（カナ）はカタカナで入力してください")

# 性別マスタ
GENDERS = {
    1: "男",
    2: "女",
}

# 入浴区分マスタ
BATH_TYPES = {
    0: "風呂なし",
    1: "機械浴",
    2: "一般浴（手引き）",
    3: "一般浴（シャワーキャリー）",
}

# 曜日マスタ
WEEKDAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]

# グローバルなDB_PATH（起動時にmain.pyから設定される）
DB_PATH = None


def set_db_path(path):
    """DB_PATHを設定"""
    global DB_PATH
    DB_PATH = path


def get_connection():
    """DBに接続（DB_PATHが未設定の場合はエラー）"""
    if DB_PATH is None:
        raise RuntimeError("DB_PATHが設定されていません")
    
    # DBファイルが存在しない場合は作成
    if not os.path.exists(DB_PATH):
        init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """データベースとテーブルの初期化を行う（既存テーブルは保持）"""
    if DB_PATH is None:
        raise RuntimeError("DB_PATHが設定されていません")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ユーザーテーブルの作成 (性別は 1:男, 2:女)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS m_users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_kana TEXT,
        gender INTEGER CHECK(gender IN (1, 2)) NOT NULL,
        is_long_term_absence INTEGER DEFAULT 0
    )
    ''')

    # スケジュールテーブルの作成 (0=月曜日,6=日曜日)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS m_user_schedules (
        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
        bath_type INTEGER NOT NULL DEFAULT 0,
        bath_memo TEXT,
        FOREIGN KEY (user_id) REFERENCES m_users(user_id) ON DELETE CASCADE,
        UNIQUE(user_id, day_of_week)
    )
    ''')

    # マイグレーション: bathing_memo → bath_memo (make_bath_table との共有DB対応)
    cursor.execute("PRAGMA table_info(m_user_schedules)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'bathing_memo' in cols and 'bath_memo' not in cols:
        cursor.execute('ALTER TABLE m_user_schedules RENAME COLUMN bathing_memo TO bath_memo')

    # マイグレーション: name/name_kana → last_name/first_name/last_name_kana/first_name_kana 分割
    cursor.execute("PRAGMA table_info(m_users)")
    user_cols = [row[1] for row in cursor.fetchall()]
    if 'last_name' not in user_cols:
        cursor.execute("ALTER TABLE m_users ADD COLUMN last_name TEXT NOT NULL DEFAULT ''")
        cursor.execute("ALTER TABLE m_users ADD COLUMN first_name TEXT NOT NULL DEFAULT ''")
        cursor.execute("ALTER TABLE m_users ADD COLUMN last_name_kana TEXT")
        cursor.execute("ALTER TABLE m_users ADD COLUMN first_name_kana TEXT")
        cursor.execute("SELECT user_id, name, name_kana FROM m_users")
        for user_id, name, name_kana in cursor.fetchall():
            parts = (name or '').split(' ', 1)
            ln = parts[0].strip()
            fn = parts[1].strip() if len(parts) > 1 else ''
            cursor.execute(
                "UPDATE m_users SET last_name=?, first_name=?, last_name_kana=?, first_name_kana='' WHERE user_id=?",
                (ln, fn, name_kana or '', user_id)
            )

    conn.commit()
    conn.close()



def add_user(last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence=0):
    """ユーザーを追加する"""
    _validate_name(last_name, last_name_kana, first_name_kana)
    name = f"{last_name} {first_name}".strip()
    name_kana = f"{last_name_kana or ''}{first_name_kana or ''}".strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO m_users (name, name_kana, last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, name_kana, last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def update_user(user_id, last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence):
    """ユーザー情報を更新する"""
    _validate_name(last_name, last_name_kana, first_name_kana)
    name = f"{last_name} {first_name}".strip()
    name_kana = f"{last_name_kana or ''}{first_name_kana or ''}".strip()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE m_users
    SET name = ?, name_kana = ?, last_name = ?, first_name = ?, last_name_kana = ?, first_name_kana = ?,
        gender = ?, is_long_term_absence = ?
    WHERE user_id = ?
    ''', (name, name_kana, last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id):
    """ユーザーを削除する（関連するスケジュールも削除）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM m_user_schedules WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM m_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def get_users():
    """全ユーザーを取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT user_id, last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence
    FROM m_users ORDER BY gender, last_name_kana, first_name_kana
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_user_by_id(user_id):
    """IDでユーザーを取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT user_id, last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence
    FROM m_users WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def set_user_schedule(user_id, day_of_week, bath_type, bath_memo=''):
    """ユーザーのスケジュールを設定する（または更新）"""
    conn = get_connection()
    cursor = conn.cursor()
    # UNIQUE制約がないDBとの互換性のため UPDATE → INSERT の順で処理
    cursor.execute('''
    UPDATE m_user_schedules SET bath_type = ?, bath_memo = ?
    WHERE user_id = ? AND day_of_week = ?
    ''', (bath_type, bath_memo, user_id, day_of_week))
    if cursor.rowcount == 0:
        cursor.execute('''
        INSERT INTO m_user_schedules (user_id, day_of_week, bath_type, bath_memo)
        VALUES (?, ?, ?, ?)
        ''', (user_id, day_of_week, bath_type, bath_memo))
    conn.commit()
    conn.close()


def delete_schedule(schedule_id):
    """スケジュールを削除する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM m_user_schedules WHERE schedule_id = ?', (schedule_id,))
    conn.commit()
    conn.close()


def delete_schedule_by_user_and_day(user_id, day_of_week):
    """ユーザーの特定曜日のスケジュールを削除する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    DELETE FROM m_user_schedules
    WHERE user_id = ? AND day_of_week = ?
    ''', (user_id, day_of_week))
    conn.commit()
    conn.close()


def get_schedules_by_user(user_id):
    """ユーザーのスケジュール一覧を取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT schedule_id, user_id, day_of_week, bath_type, bath_memo
    FROM m_user_schedules
    WHERE user_id = ?
    ORDER BY day_of_week
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_schedule_by_user_and_day(user_id, day_of_week):
    """ユーザーの特定の曜日のスケジュールを取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT schedule_id, user_id, day_of_week, bath_type, bath_memo
    FROM m_user_schedules
    WHERE user_id = ? AND day_of_week = ?
    ''', (user_id, day_of_week))
    row = cursor.fetchone()
    conn.close()
    return row


def get_schedule_for_day(day_of_week):
    """指定曜日の全ユーザーのスケジュールを取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.user_id, u.name, u.name_kana, u.gender, u.is_long_term_absence,
           s.schedule_id, s.day_of_week, s.bath_type, s.bath_memo
    FROM m_user_schedules s
    JOIN m_users u ON u.user_id = s.user_id
    WHERE s.day_of_week = ?
    ORDER BY u.gender, u.name_kana
    ''', (day_of_week,))
    rows = cursor.fetchall()
    conn.close()
    return rows
