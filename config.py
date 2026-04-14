import json
import os
import sys
import sqlite3

def _get_app_dir():
    """exe実行時はexeのある場所、開発時はスクリプトと同じ場所"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_get_app_dir(), 'config.json')
DEFAULT_DB_PATH = os.path.join(_get_app_dir(), 'dayservice_data.db')


def _find_existing_db():
    """
    既存のbath-table用DBを探す
    検索順序: ./dayservice_data.db -> %APPDATA%/dayservice_data.db -> None
    """
    # アプリディレクトリ
    local_db = os.path.join(_get_app_dir(), 'dayservice_data.db')
    if os.path.exists(local_db):
        if _is_valid_db(local_db):
            return local_db
    
    # ユーザーホームディレクトリ
    home_db = os.path.join(os.path.expanduser('~'), 'dayservice_data.db')
    if os.path.exists(home_db):
        if _is_valid_db(home_db):
            return home_db
    
    return None


def _is_valid_db(db_path):
    """
    DBファイルが有効なsqliteファイルか確認
    m_users, m_user_schedulesテーブルの存在確認
    """
    try:
        if not os.path.exists(db_path):
            return False
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='m_users'")
        has_users = cursor.fetchone() is not None
        conn.close()
        return has_users
    except Exception:
        return False


def load():
    """設定を読み込む。既存DBも自動検出する"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding='utf-8') as f:
                cfg = json.load(f)
                # 保存されたパスが有効か確認
                if os.path.exists(cfg.get('db_path', '')):
                    return cfg
        except Exception:
            pass
    
    # DB自動検出
    existing_db = _find_existing_db()
    if existing_db:
        return {'db_path': existing_db}
    
    # デフォルト値
    return {'db_path': DEFAULT_DB_PATH}


def save(data):
    """設定を保存"""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
