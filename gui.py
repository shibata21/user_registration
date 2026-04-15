import os
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import logic
import config

def create_and_show():
    """メイン画面を作成・表示"""
    
    def refresh_user_list(query=""):
        """ユーザーリストを更新（queryで氏名・カナを絞り込み）"""
        for item in user_tree.get_children():
            user_tree.delete(item)

        users = logic.get_users()
        q = query.strip()
        matched = 0
        for user in users:
            user_id, last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence = user
            full_name = f"{last_name}　{first_name}".strip()
            full_kana = f"{last_name_kana or ''}{first_name_kana or ''}".strip()
            if q and q not in full_name and q not in full_kana:
                continue
            gender_str = logic.GENDERS.get(gender, "不明")
            status = "長期休中" if is_long_term_absence else ""
            user_tree.insert('', 'end', values=(user_id, full_name, full_kana, gender_str, status))
            matched += 1

        total = len(users)
        if q:
            count_label.configure(text=f"{matched} / {total} 件")
        else:
            count_label.configure(text=f"{total} 件")

    def on_add_user_clicked():
        """ユーザー追加ボタン"""
        open_user_edit_dialog(None)

    def on_edit_user_clicked():
        """ユーザー編集ボタン"""
        selected = user_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "ユーザーを選択してください")
            return
        user_id = int(user_tree.item(selected[0])['values'][0])
        user = logic.get_user_by_id(user_id)
        open_user_edit_dialog(user)

    def on_delete_user_clicked():
        """ユーザー削除ボタン"""
        selected = user_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "ユーザーを選択してください")
            return
        user_id = int(user_tree.item(selected[0])['values'][0])
        name = user_tree.item(selected[0])['values'][1]
        
        if messagebox.askyesno("確認", f"{name}を削除しますか？"):
            logic.delete_user(user_id)
            refresh_user_list(search_var.get())
            messagebox.showinfo("成功", f"{name}を削除しました")

    def on_db_setting_clicked():
        """DB設定ボタン"""
        path = filedialog.askopenfilename(
            title="DBファイルを選択",
            defaultextension=".db",
            filetypes=[("SQLiteデータベース", "*.db"), ("すべてのファイル", "*.*")],
        )
        if not path:
            return

        # 選択したファイルが有効なDBか確認
        if not config._is_valid_db(path):
            if not messagebox.askyesno("確認", "このファイルは既存のDBではありません。新規作成しますか？"):
                return

        try:
            cfg = config.load()
            cfg['db_path'] = path
            config.save(cfg)
            logic.set_db_path(path)
            logic.init_db()
            db_path_label.configure(text=path)
            status_label.configure(text="DBファイルを変更しました", text_color="#2FA572")
            search_var.set("")
        except Exception as e:
            messagebox.showerror("エラー", f"DB変更に失敗しました:\n{str(e)}")

    def on_new_db_clicked():
        """DB新規作成ボタン"""
        messagebox.showwarning(
            "注意",
            "新規データベースを作成します。\n\n"
            "・現在のデータベースとは別に空のDBが作成されます\n"
            "・既存のデータは新しいDBに引き継がれません\n"
            "・作成後は新しいDBに切り替わります\n\n"
            "続ける場合は保存先を選択してください。"
        )
        path = filedialog.asksaveasfilename(
            title="新規DBの保存先を選択",
            defaultextension=".db",
            filetypes=[("SQLiteデータベース", "*.db"), ("すべてのファイル", "*.*")],
            initialfile="dayservice_data.db",
        )
        if not path:
            return

        if os.path.exists(path):
            if not messagebox.askyesno("上書き確認", f"既存のファイルが見つかりました。\n上書きして新規作成しますか？\n\n{path}"):
                return

        try:
            # 既存ファイルを削除して新規作成
            if os.path.exists(path):
                os.remove(path)
            cfg = config.load()
            cfg['db_path'] = path
            config.save(cfg)
            logic.set_db_path(path)
            logic.init_db()
            db_path_label.configure(text=path)
            status_label.configure(text="新規DBを作成しました", text_color="#2FA572")
            search_var.set("")
        except Exception as e:
            messagebox.showerror("エラー", f"DB作成に失敗しました:\n{str(e)}")

    def on_quit_clicked():
        """終了ボタン"""
        if messagebox.askyesno("終了確認", "アプリケーションを終了しますか？"):
            app.destroy()

    def open_user_edit_dialog(user):
        """ユーザー編集ダイアログを開く（スケジュール設定を含む）"""
        dialog = ctk.CTkToplevel(app)
        dialog.geometry("500x680")
        dialog.title("ユーザー情報" if user else "新規ユーザー")
        dialog.resizable(False, False)
        dialog.transient(app)
        dialog.grab_set()

        # スクロール可能なメインエリア
        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=15, pady=(15, 5))

        # ── 基本情報 ──
        ctk.CTkLabel(scroll, text="基本情報", font=("", 13, "bold")).pack(anchor="w", pady=(0, 8))

        name_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        name_frame.pack(anchor="w", fill="x", pady=(0, 10))
        ctk.CTkLabel(name_frame, text="氏:", font=("", 12), width=60, anchor="w").grid(row=0, column=0)
        last_name_entry = ctk.CTkEntry(name_frame, width=160, font=("", 12))
        last_name_entry.grid(row=0, column=1, padx=(0, 15))
        ctk.CTkLabel(name_frame, text="名:", font=("", 12), width=40, anchor="w").grid(row=0, column=2)
        first_name_entry = ctk.CTkEntry(name_frame, width=160, font=("", 12))
        first_name_entry.grid(row=0, column=3)
        if user:
            last_name_entry.insert(0, user[1])
            first_name_entry.insert(0, user[2])

        kana_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        kana_frame.pack(anchor="w", fill="x", pady=(0, 10))
        ctk.CTkLabel(kana_frame, text="氏（カナ）:", font=("", 12), width=60, anchor="w").grid(row=0, column=0)
        last_name_kana_entry = ctk.CTkEntry(kana_frame, width=160, font=("", 12))
        last_name_kana_entry.grid(row=0, column=1, padx=(0, 15))
        ctk.CTkLabel(kana_frame, text="名（カナ）:", font=("", 12), width=40, anchor="w").grid(row=0, column=2)
        first_name_kana_entry = ctk.CTkEntry(kana_frame, width=160, font=("", 12))
        first_name_kana_entry.grid(row=0, column=3)
        if user:
            last_name_kana_entry.insert(0, user[3] or "")
            first_name_kana_entry.insert(0, user[4] or "")

        ctk.CTkLabel(scroll, text="性別:", font=("", 12)).pack(anchor="w")
        gender_var = tk.IntVar(value=user[5] if user else 1)
        gender_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        gender_frame.pack(anchor="w", pady=(0, 10))
        ctk.CTkRadioButton(gender_frame, text="男", variable=gender_var, value=1).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(gender_frame, text="女", variable=gender_var, value=2).pack(side="left")

        absence_var = tk.BooleanVar(value=bool(user[6]) if user else False)
        ctk.CTkCheckBox(scroll, text="長期休中", variable=absence_var).pack(anchor="w", pady=(0, 15))

        # 区切り線
        ctk.CTkFrame(scroll, height=2, fg_color="gray50").pack(fill="x", pady=(0, 12))

        # ── 来所スケジュール ──
        ctk.CTkLabel(scroll, text="来所スケジュール", font=("", 13, "bold")).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(scroll, text="来所日を選択し、入浴区分を設定してください",
                     font=("", 11), text_color="gray").pack(anchor="w", pady=(0, 10))

        if user:
            schedules = logic.get_schedules_by_user(user[0])
            schedule_dict = {s[2]: s for s in schedules}
        else:
            schedule_dict = {}

        day_entries = {}
        for day_idx in range(7):
            day_name = logic.WEEKDAY_NAMES[day_idx]
            schedule = schedule_dict.get(day_idx)

            day_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            day_frame.pack(fill="x", pady=4)

            is_attending_var = tk.BooleanVar(value=schedule is not None)
            ctk.CTkCheckBox(day_frame, text=f"{day_name}曜日", variable=is_attending_var,
                            width=90, font=("", 11)).pack(side="left", padx=(0, 8))

            bath_var = tk.StringVar()
            bath_combo = ttk.Combobox(day_frame, textvariable=bath_var, width=24,
                                      state="readonly", font=("", 11))
            bath_combo['values'] = [f"{k}: {v}" for k, v in logic.BATH_TYPES.items()]
            bath_combo.set(f"{schedule[3]}: {logic.BATH_TYPES[schedule[3]]}" if schedule else "0: 風呂なし")
            bath_combo.pack(side="left", padx=(0, 8))

            memo_entry = ctk.CTkEntry(day_frame, placeholder_text="メモ", width=130, font=("", 11))
            if schedule and schedule[4]:
                memo_entry.insert(0, schedule[4])
            memo_entry.pack(side="left")

            day_entries[day_idx] = (is_attending_var, bath_var, memo_entry)

        # ── ボタン ──
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)

        def on_save():
            import re
            last_name = last_name_entry.get().strip()
            first_name = first_name_entry.get().strip()
            last_name_kana = last_name_kana_entry.get().strip()
            first_name_kana = first_name_kana_entry.get().strip()

            if not last_name:
                messagebox.showwarning("入力エラー", "氏を入力してください")
                last_name_entry.focus_set()
                return
            if not last_name_kana:
                messagebox.showwarning("入力エラー", "氏（カナ）を入力してください")
                last_name_kana_entry.focus_set()
                return
            katakana_re = re.compile(r'^[ァ-ヶーヴ・\s]+$')
            if not katakana_re.match(last_name_kana):
                messagebox.showwarning("入力エラー", "氏（カナ）はカタカナで入力してください")
                last_name_kana_entry.focus_set()
                return
            if first_name_kana and not katakana_re.match(first_name_kana):
                messagebox.showwarning("入力エラー", "名（カナ）はカタカナで入力してください")
                first_name_kana_entry.focus_set()
                return
            if not any(is_attending_var.get() for is_attending_var, _, _ in day_entries.values()):
                messagebox.showwarning("入力エラー", "来所日を1日以上選択してください")
                return

            # 重複チェック
            exclude_id = user[0] if user else None
            duplicates = logic.find_users_by_name(last_name, first_name, exclude_user_id=exclude_id)
            if duplicates:
                dup_info = "\n".join(
                    f"  ・{r[1]} {r[2]}（{'男' if r[5] == 1 else '女'}）ID:{r[0]}"
                    for r in duplicates
                )
                if not messagebox.askyesno(
                    "重複確認",
                    f"同じ氏名のユーザーが既に登録されています。\n\n{dup_info}\n\nこのまま登録しますか？"
                ):
                    return

            gender = gender_var.get()
            is_long_term_absence = 1 if absence_var.get() else 0
            try:
                if user:
                    logic.update_user(user[0], last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence)
                    target_user_id = user[0]
                else:
                    target_user_id = logic.add_user(last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence)
                for day_idx, (is_attending_var, bath_var, memo_entry) in day_entries.items():
                    if is_attending_var.get():
                        bath_type = int(bath_var.get().split(':')[0])
                        memo = memo_entry.get().strip()
                        logic.set_user_schedule(target_user_id, day_idx, bath_type, memo)
                    else:
                        if day_idx in schedule_dict:
                            logic.delete_schedule_by_user_and_day(target_user_id, day_idx)
                messagebox.showinfo("成功", "保存しました")
                refresh_user_list(search_var.get())
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("エラー", f"処理に失敗しました: {str(e)}")

        ctk.CTkButton(button_frame, text="保存", width=100, command=on_save).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="キャンセル", width=100, command=dialog.destroy,
                      fg_color="#888888", hover_color="#666666").pack(side="left", padx=5)

    # --- メイン画面構築 ---
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.geometry("900x700")
    app.title("ユーザー登録システム")

    # タイトル
    title_label = ctk.CTkLabel(app, text="ユーザー登録・管理", font=("", 24, "bold"))
    title_label.pack(pady=(20, 10))

    # DB設定エリア
    db_frame = ctk.CTkFrame(app)
    db_frame.pack(fill="x", padx=40, pady=(0, 15))

    ctk.CTkLabel(db_frame, text="DB:", font=("", 12)).grid(row=0, column=0, padx=(10, 4), pady=8)
    db_path_label = ctk.CTkLabel(db_frame, text=logic.DB_PATH if logic.DB_PATH else "未設定", font=("", 10), anchor="w")
    db_path_label.grid(row=0, column=1, padx=4, pady=8, sticky="ew")
    db_frame.grid_columnconfigure(1, weight=1)

    ctk.CTkButton(db_frame, text="変更", width=70, height=28, font=("", 11),
                  command=on_db_setting_clicked).grid(row=0, column=2, padx=(4, 4), pady=8)
    ctk.CTkButton(db_frame, text="新規作成", width=80, height=28, font=("", 11),
                  fg_color="#555555", hover_color="#333333",
                  command=on_new_db_clicked).grid(row=0, column=3, padx=(4, 10), pady=8)

    # 検索バー
    search_frame = ctk.CTkFrame(app, fg_color="transparent")
    search_frame.pack(fill="x", padx=20, pady=(0, 4))

    ctk.CTkLabel(search_frame, text="検索:", font=("", 12)).pack(side="left", padx=(0, 6))
    search_var = tk.StringVar()
    search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, width=260,
                                placeholder_text="氏名・カナで絞り込み", font=("", 12))
    search_entry.pack(side="left")
    ctk.CTkButton(search_frame, text="✕", width=32, height=28, font=("", 12),
                  fg_color="#888888", hover_color="#666666",
                  command=lambda: search_var.set("")).pack(side="left", padx=(6, 0))
    count_label = ctk.CTkLabel(search_frame, text="", font=("", 11), text_color="gray")
    count_label.pack(side="left", padx=(12, 0))

    search_var.trace_add("write", lambda *_: refresh_user_list(search_var.get()))

    # TreeView（ユーザー一覧）
    tree_frame = ctk.CTkFrame(app)
    tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    # ツリービューのスタイル設定
    style = ttk.Style()
    style.theme_use('clam')
    
    columns = ('ID', '氏名', 'カナ', '性別', 'ステータス')
    user_tree = ttk.Treeview(tree_frame, columns=columns, height=15, show='headings')
    
    user_tree.column('ID', width=50, anchor='center')
    user_tree.column('氏名', width=150)
    user_tree.column('カナ', width=150)
    user_tree.column('性別', width=80, anchor='center')
    user_tree.column('ステータス', width=100, anchor='center')
    
    user_tree.heading('ID', text='ID')
    user_tree.heading('氏名', text='氏名')
    user_tree.heading('カナ', text='カナ')
    user_tree.heading('性別', text='性別')
    user_tree.heading('ステータス', text='ステータス')
    
    # スクロールバー（treeviewより先にpackする必要がある）
    scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=user_tree.yview)
    scrollbar.pack(side='right', fill='y')

    user_tree.pack(fill="both", expand=True)
    user_tree.configure(yscrollcommand=scrollbar.set)

    # 操作ボタン
    button_frame = ctk.CTkFrame(app, fg_color="transparent")
    button_frame.pack(pady=15)

    ctk.CTkButton(button_frame, text="新規追加", width=100, font=("", 12),
                  command=on_add_user_clicked).pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="編集", width=100, font=("", 12),
                  command=on_edit_user_clicked).pack(side="left", padx=5)
    ctk.CTkButton(button_frame, text="削除", width=100, font=("", 12),
                  fg_color="#DD0000", hover_color="#AA0000",
                  command=on_delete_user_clicked).pack(side="left", padx=5)

    # ステータスバー
    status_label = ctk.CTkLabel(app, text="", font=("", 12))
    status_label.pack(pady=5)

    # 終了ボタン
    quit_btn = ctk.CTkButton(app, text="終了", font=("", 12), width=100, height=32,
                             fg_color="#888888", hover_color="#666666", command=on_quit_clicked)
    quit_btn.pack(pady=(0, 15))

    # 初期表示
    refresh_user_list(search_var.get())

    app.mainloop()
