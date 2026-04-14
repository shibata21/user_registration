"""
user_registration/logic.py のユニットテスト
正常系・異常系
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import logic


class TestInitDb(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    def test_creates_m_users_table(self):
        import sqlite3
        conn = sqlite3.connect(self._path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='m_users'")
        self.assertIsNotNone(cur.fetchone())
        conn.close()

    def test_creates_m_user_schedules_table(self):
        import sqlite3
        conn = sqlite3.connect(self._path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='m_user_schedules'")
        self.assertIsNotNone(cur.fetchone())
        conn.close()

    def test_idempotent_preserves_data(self):
        logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 1)
        logic.init_db()
        self.assertEqual(len(logic.get_users()), 1)

    def test_raises_when_db_path_none(self):
        logic.set_db_path(None)
        with self.assertRaises(RuntimeError):
            logic.init_db()

    def test_get_connection_raises_when_db_path_none(self):
        logic.set_db_path(None)
        with self.assertRaises(RuntimeError):
            logic.get_connection()


class TestAddUser(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    # ── 正常系 ──────────────────────────────────────────────

    def test_returns_positive_id(self):
        uid = logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 1)
        self.assertIsNotNone(uid)
        self.assertGreater(uid, 0)

    def test_stores_split_name(self):
        uid = logic.add_user("鈴木", "花子", "スズキ", "ハナコ", 2)
        u = logic.get_user_by_id(uid)
        self.assertEqual(u[1], "鈴木")
        self.assertEqual(u[2], "花子")
        self.assertEqual(u[3], "スズキ")
        self.assertEqual(u[4], "ハナコ")

    def test_stores_gender(self):
        uid = logic.add_user("田中", "一郎", "タナカ", "イチロウ", 1)
        u = logic.get_user_by_id(uid)
        self.assertEqual(u[5], 1)

    def test_combined_name_saved_for_compatibility(self):
        """make_bath_table 互換: name / name_kana 列が結合形式で保存される"""
        import sqlite3
        logic.add_user("田中", "一郎", "タナカ", "イチロウ", 1)
        conn = sqlite3.connect(self._path)
        row = conn.execute("SELECT name, name_kana FROM m_users").fetchone()
        conn.close()
        self.assertEqual(row[0], "田中 一郎")
        self.assertEqual(row[1], "タナカイチロウ")

    def test_first_name_optional(self):
        uid = logic.add_user("一字", "", "イチジ", "", 1)
        u = logic.get_user_by_id(uid)
        self.assertEqual(u[1], "一字")
        self.assertEqual(u[2], "")

    def test_first_name_kana_optional(self):
        """名カナは省略可能"""
        uid = logic.add_user("田中", "太郎", "タナカ", "", 1)
        self.assertGreater(uid, 0)

    def test_default_absence_is_zero(self):
        uid = logic.add_user("デフォルト", "", "デフォルト", "", 1)
        u = logic.get_user_by_id(uid)
        self.assertEqual(u[6], 0)

    def test_absence_flag_stored(self):
        uid = logic.add_user("長期休中", "", "チョウキキュウチュウ", "", 1, is_long_term_absence=1)
        u = logic.get_user_by_id(uid)
        self.assertEqual(u[6], 1)

    def test_multiple_users_get_unique_ids(self):
        kanas = ["ア", "イ", "ウ", "エ", "オ"]
        ids = [logic.add_user(f"ユーザー{i}", "", kanas[i], "", 1) for i in range(5)]
        self.assertEqual(len(set(ids)), 5)

    def test_duplicate_name_allowed(self):
        uid1 = logic.add_user("同名", "太郎", "ドウメイ", "タロウ", 1)
        uid2 = logic.add_user("同名", "太郎", "ドウメイ", "タロウ", 1)
        self.assertNotEqual(uid1, uid2)

    # ── 異常系 ──────────────────────────────────────────────

    def test_empty_last_name_raises(self):
        """氏が空の場合エラー"""
        with self.assertRaises(ValueError):
            logic.add_user("", "", "テスト", "", 1)

    def test_empty_last_name_kana_raises(self):
        """氏カナが空の場合エラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "", "", "", 1)

    def test_non_katakana_last_name_kana_raises(self):
        """氏カナにひらがなが含まれる場合エラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "", "たなか", "", 1)

    def test_non_katakana_last_name_kana_kanji_raises(self):
        """氏カナに漢字が含まれる場合エラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "", "田中", "", 1)

    def test_non_katakana_first_name_kana_raises(self):
        """名カナにひらがなが含まれる場合エラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "太郎", "タナカ", "たろう", 1)

    def test_katakana_with_long_vowel_allowed(self):
        """長音符（ー）を含むカナは有効"""
        uid = logic.add_user("大野", "", "オーノ", "", 1)
        self.assertGreater(uid, 0)

    def test_katakana_with_middle_dot_allowed(self):
        """中点（・）を含むカナは有効"""
        uid = logic.add_user("アンドレ", "", "アンドレ・スミス", "", 1)
        self.assertGreater(uid, 0)


class TestUpdateUser(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()
        self._uid = logic.add_user("旧姓", "旧名", "キュウセイ", "キュウメイ", 1)

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    # ── 正常系 ──────────────────────────────────────────────

    def test_updates_name(self):
        logic.update_user(self._uid, "新姓", "新名", "シンセイ", "シンメイ", 1, 0)
        u = logic.get_user_by_id(self._uid)
        self.assertEqual(u[1], "新姓")
        self.assertEqual(u[2], "新名")
        self.assertEqual(u[3], "シンセイ")
        self.assertEqual(u[4], "シンメイ")

    def test_updates_gender(self):
        logic.update_user(self._uid, "姓", "", "セイ", "", 2, 0)
        u = logic.get_user_by_id(self._uid)
        self.assertEqual(u[5], 2)

    def test_updates_absence_flag(self):
        logic.update_user(self._uid, "姓", "", "セイ", "", 1, 1)
        u = logic.get_user_by_id(self._uid)
        self.assertEqual(u[6], 1)

    def test_combined_name_updated(self):
        import sqlite3
        logic.update_user(self._uid, "新", "氏名", "シン", "シメイ", 1, 0)
        conn = sqlite3.connect(self._path)
        row = conn.execute("SELECT name FROM m_users WHERE user_id=?", (self._uid,)).fetchone()
        conn.close()
        self.assertEqual(row[0], "新 氏名")

    def test_other_users_not_affected(self):
        uid2 = logic.add_user("別ユーザー", "", "ベツユーザー", "", 2)
        logic.update_user(self._uid, "変更後", "", "ヘンコウゴ", "", 1, 0)
        u2 = logic.get_user_by_id(uid2)
        self.assertEqual(u2[1], "別ユーザー")

    # ── 異常系 ──────────────────────────────────────────────

    def test_update_empty_last_name_raises(self):
        with self.assertRaises(ValueError):
            logic.update_user(self._uid, "", "", "テスト", "", 1, 0)

    def test_update_empty_last_name_kana_raises(self):
        with self.assertRaises(ValueError):
            logic.update_user(self._uid, "姓", "", "", "", 1, 0)

    def test_update_non_katakana_raises(self):
        with self.assertRaises(ValueError):
            logic.update_user(self._uid, "姓", "", "せい", "", 1, 0)


class TestDeleteUser(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    # ── 正常系 ──────────────────────────────────────────────

    def test_removes_user(self):
        uid = logic.add_user("削除対象", "", "サクジョタイショウ", "", 1)
        logic.add_user("残存", "", "ザンゾン", "", 1)
        logic.delete_user(uid)
        self.assertIsNone(logic.get_user_by_id(uid))
        self.assertEqual(len(logic.get_users()), 1)

    def test_removes_associated_schedules(self):
        uid = logic.add_user("スケジュール付き", "", "スケジュールツキ", "", 1)
        logic.set_user_schedule(uid, 0, 1)
        logic.set_user_schedule(uid, 2, 2)
        logic.delete_user(uid)
        self.assertEqual(logic.get_schedules_by_user(uid), [])

    def test_other_users_schedules_not_affected(self):
        uid1 = logic.add_user("削除対象", "", "サクジョタイショウ", "", 1)
        uid2 = logic.add_user("残存", "", "ザンゾン", "", 1)
        logic.set_user_schedule(uid1, 0, 1)
        logic.set_user_schedule(uid2, 0, 2)
        logic.delete_user(uid1)
        self.assertEqual(len(logic.get_schedules_by_user(uid2)), 1)

    # ── 異常系 ──────────────────────────────────────────────

    def test_nonexistent_user_no_error(self):
        logic.delete_user(9999)  # 例外が出ないことを確認


class TestGetUsers(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    def test_empty_db_returns_empty_list(self):
        self.assertEqual(logic.get_users(), [])

    def test_returns_all_users(self):
        logic.add_user("ア", "", "ア", "", 1)
        logic.add_user("イ", "", "イ", "", 2)
        self.assertEqual(len(logic.get_users()), 2)

    def test_includes_long_term_absence(self):
        logic.add_user("在籍", "", "ザイセキ", "", 1, is_long_term_absence=0)
        logic.add_user("離脱", "", "リダツ", "", 1, is_long_term_absence=1)
        self.assertEqual(len(logic.get_users()), 2)

    def test_sorted_by_gender_then_kana(self):
        logic.add_user("女B", "", "ジョセイビー", "", 2)
        logic.add_user("男A", "", "ダンセイエー", "", 1)
        logic.add_user("女A", "", "ジョセイエー", "", 2)
        users = logic.get_users()
        self.assertEqual(users[0][5], 1)                    # 男性が先
        self.assertEqual(users[1][3], "ジョセイエー")       # 女A
        self.assertEqual(users[2][3], "ジョセイビー")       # 女B

    def test_returns_7_tuple_per_row(self):
        logic.add_user("確認", "", "カクニン", "", 1)
        u = logic.get_users()[0]
        # (user_id, last_name, first_name, last_name_kana, first_name_kana, gender, is_long_term_absence)
        self.assertEqual(len(u), 7)


class TestGetUserById(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    def test_found(self):
        uid = logic.add_user("検索", "対象", "ケンサク", "タイショウ", 1)
        u = logic.get_user_by_id(uid)
        self.assertIsNotNone(u)
        self.assertEqual(u[0], uid)
        self.assertEqual(u[1], "検索")
        self.assertEqual(u[2], "対象")

    def test_not_found_returns_none(self):
        self.assertIsNone(logic.get_user_by_id(9999))

    def test_returns_none_after_delete(self):
        uid = logic.add_user("削除済み", "", "サクジョズミ", "", 1)
        logic.delete_user(uid)
        self.assertIsNone(logic.get_user_by_id(uid))


class TestSetUserSchedule(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()
        self._uid = logic.add_user("テスト", "", "テスト", "", 1)

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    # ── 正常系 ──────────────────────────────────────────────

    def test_insert_new_schedule(self):
        logic.set_user_schedule(self._uid, 0, 2, "メモ")
        rows = logic.get_schedules_by_user(self._uid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], 0)      # day_of_week
        self.assertEqual(rows[0][3], 2)      # bath_type
        self.assertEqual(rows[0][4], "メモ") # bath_memo

    def test_update_existing_schedule(self):
        logic.set_user_schedule(self._uid, 0, 1)
        logic.set_user_schedule(self._uid, 0, 3, "更新後")
        rows = logic.get_schedules_by_user(self._uid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], 3)
        self.assertEqual(rows[0][4], "更新後")

    def test_no_duplicate_on_update(self):
        logic.set_user_schedule(self._uid, 0, 1)
        logic.set_user_schedule(self._uid, 0, 2)
        self.assertEqual(len(logic.get_schedules_by_user(self._uid)), 1)

    def test_all_seven_days(self):
        for dow in range(7):
            logic.set_user_schedule(self._uid, dow, 1)
        self.assertEqual(len(logic.get_schedules_by_user(self._uid)), 7)

    def test_all_bath_types(self):
        kanas = ["ゼロ", "イチ", "ニ", "サン"]
        for bt in range(4):
            uid = logic.add_user(f"入浴{bt}", "", kanas[bt], "", 1)
            logic.set_user_schedule(uid, 0, bt)
            s = logic.get_schedule_by_user_and_day(uid, 0)
            self.assertEqual(s[3], bt)

    def test_memo_default_empty(self):
        logic.set_user_schedule(self._uid, 0, 1)
        s = logic.get_schedule_by_user_and_day(self._uid, 0)
        self.assertEqual(s[4], "")


class TestDeleteSchedule(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()
        self._uid = logic.add_user("テスト", "", "テスト", "", 1)

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    # ── 正常系 ──────────────────────────────────────────────

    def test_deletes_target_day(self):
        logic.set_user_schedule(self._uid, 0, 1)
        logic.set_user_schedule(self._uid, 2, 2)
        logic.delete_schedule_by_user_and_day(self._uid, 0)
        rows = logic.get_schedules_by_user(self._uid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], 2)  # 水曜日のみ残る

    # ── 異常系 ──────────────────────────────────────────────

    def test_nonexistent_schedule_no_error(self):
        logic.delete_schedule_by_user_and_day(self._uid, 6)


class TestGetScheduleForDay(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    # ── 正常系 ──────────────────────────────────────────────

    def test_returns_users_on_target_day(self):
        uid1 = logic.add_user("月曜ア", "", "ゲツヨウア", "", 1)
        uid2 = logic.add_user("月曜イ", "", "ゲツヨウイ", "", 2)
        logic.set_user_schedule(uid1, 0, 1)
        logic.set_user_schedule(uid2, 0, 2)
        self.assertEqual(len(logic.get_schedule_for_day(0)), 2)

    def test_excludes_other_days(self):
        uid = logic.add_user("火曜のみ", "", "カヨウノミ", "", 1)
        logic.set_user_schedule(uid, 1, 2)
        self.assertEqual(logic.get_schedule_for_day(0), [])

    def test_empty_when_no_schedules(self):
        for dow in range(7):
            self.assertEqual(logic.get_schedule_for_day(dow), [])

    def test_user_without_schedule_not_returned(self):
        logic.add_user("スケジュールナシ", "", "スケジュールナシ", "", 1)
        for dow in range(7):
            self.assertEqual(logic.get_schedule_for_day(dow), [])

    def test_sort_by_gender_then_kana(self):
        uid1 = logic.add_user("女B", "", "ジョセイビー", "", 2)
        uid2 = logic.add_user("男A", "", "ダンセイエー", "", 1)
        uid3 = logic.add_user("女A", "", "ジョセイエー", "", 2)
        for uid in [uid1, uid2, uid3]:
            logic.set_user_schedule(uid, 3, 1)
        rows = logic.get_schedule_for_day(3)
        names = [r[1] for r in rows]
        self.assertEqual(names, ["男A", "女A", "女B"])

    def test_long_term_absence_included(self):
        uid = logic.add_user("離脱者", "", "リダツシャ", "", 1, is_long_term_absence=1)
        logic.set_user_schedule(uid, 0, 2)
        rows = logic.get_schedule_for_day(0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], 1)   # is_long_term_absence

    def test_bath_type_zero_included(self):
        uid = logic.add_user("風呂ナシ", "", "フロナシ", "", 2)
        logic.set_user_schedule(uid, 2, 0)
        rows = logic.get_schedule_for_day(2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][7], 0)   # bath_type

    def test_saturday(self):
        uid = logic.add_user("土曜利用者", "", "ドヨウリヨウシャ", "", 1)
        logic.set_user_schedule(uid, 5, 2)
        self.assertEqual(len(logic.get_schedule_for_day(5)), 1)

    def test_sunday(self):
        uid = logic.add_user("日曜利用者", "", "ニチヨウリヨウシャ", "", 2)
        logic.set_user_schedule(uid, 6, 1)
        self.assertEqual(len(logic.get_schedule_for_day(6)), 1)

    def test_multiple_users_same_day(self):
        kanas = ["ア", "イ", "ウ", "エ", "オ"]
        for i in range(5):
            uid = logic.add_user(f"利用者{i}", "", kanas[i], "", 1)
            logic.set_user_schedule(uid, 0, 2)
        self.assertEqual(len(logic.get_schedule_for_day(0)), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
