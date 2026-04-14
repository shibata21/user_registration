import logic
import config
import gui
import tkinter.messagebox as messagebox
import os


def main():
    """
    起動フロー：
    1. 設定読み込み（DB パス自動検出も含む）
    2. DBパスを logic に設定
    3. DBが存在しなければ新規作成
    4. GUI起動
    """
    
    # 1. 設定読み込み（自動検出あり）
    cfg = config.load()
    db_path = cfg.get('db_path')
    
    # 2. DB_PATHをlogicに設定
    logic.set_db_path(db_path)
    
    # 3. DB初期化（存在しなければ作成）
    try:
        logic.init_db()
    except Exception as e:
        messagebox.showerror("DBエラー", f"データベースの初期化に失敗しました:\n{str(e)}")
        return
    
    # 4. GUIの起動
    try:
        gui.create_and_show()
    except Exception as e:
        messagebox.showerror("GUIエラー", f"GUIの起動に失敗しました:\n{str(e)}")
        return


if __name__ == "__main__":
    main()
