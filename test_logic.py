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

    def test_katakana_with_space_allowed(self):
        """スペースを含むカナは有効（regex に \s を含む）"""
        uid = logic.add_user("山田", "", "ヤマ ダ", "", 1)
        self.assertGreater(uid, 0)

    # ── 異常系（追加エッジケース） ────────────────────────────

    def test_whitespace_only_last_name_raises(self):
        """空白のみの氏はエラー"""
        with self.assertRaises(ValueError):
            logic.add_user("   ", "", "テスト", "", 1)

    def test_whitespace_only_last_name_kana_raises(self):
        """空白のみの氏カナはエラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "", "   ", "", 1)

    def test_none_last_name_raises(self):
        """None の氏はエラー"""
        with self.assertRaises(ValueError):
            logic.add_user(None, "", "テスト", "", 1)

    def test_none_last_name_kana_raises(self):
        """None の氏カナはエラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "", None, "", 1)

    def test_roman_alphabet_in_last_name_kana_raises(self):
        """氏カナにローマ字が入るとエラー"""
        with self.assertRaises(ValueError):
            logic.add_user("Smith", "", "Smith", "", 1)

    def test_numbers_in_last_name_kana_raises(self):
        """氏カナに数字が入るとエラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "", "タナカ123", "", 1)

    def test_mixed_katakana_hiragana_in_kana_raises(self):
        """氏カナにひらがなが混じるとエラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "", "タなカ", "", 1)

    def test_roman_alphabet_in_first_name_kana_raises(self):
        """名カナにローマ字が入るとエラー"""
        with self.assertRaises(ValueError):
            logic.add_user("田中", "太郎", "タナカ", "Taro", 1)

    def test_whitespace_only_first_name_kana_is_ok(self):
        """名カナが空白のみは空扱いでOK"""
        uid = logic.add_user("田中", "", "タナカ", "   ", 1)
        self.assertGreater(uid, 0)


class TestFindUsersByName(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    # ── 正常系 ──────────────────────────────────────────────

    def test_no_duplicate_returns_empty(self):
        logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 1)
        result = logic.find_users_by_name("鈴木", "花子")
        self.assertEqual(result, [])

    def test_finds_same_full_name(self):
        uid = logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 1)
        result = logic.find_users_by_name("山田", "太郎")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], uid)

    def test_finds_multiple_duplicates(self):
        logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 1)
        logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 2)
        result = logic.find_users_by_name("山田", "太郎")
        self.assertEqual(len(result), 2)

    def test_excludes_self_on_update(self):
        """編集時は自分自身を重複対象から除外する"""
        uid = logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 1)
        result = logic.find_users_by_name("山田", "太郎", exclude_user_id=uid)
        self.assertEqual(result, [])

    def test_does_not_exclude_other_duplicates(self):
        uid1 = logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 1)
        uid2 = logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 2)
        result = logic.find_users_by_name("山田", "太郎", exclude_user_id=uid1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], uid2)

    def test_partial_name_not_matched(self):
        """氏だけが一致しても重複とみなさない"""
        logic.add_user("山田", "太郎", "ヤマダ", "タロウ", 1)
        result = logic.find_users_by_name("山田", "花子")
        self.assertEqual(result, [])

    def test_empty_first_name_matched(self):
        """名が空の場合も正しく照合する"""
        logic.add_user("山田", "", "ヤマダ", "", 1)
        result = logic.find_users_by_name("山田", "")
        self.assertEqual(len(result), 1)

    # ── 異常系 ──────────────────────────────────────────────

    def test_no_users_returns_empty(self):
        result = logic.find_users_by_name("山田", "太郎")
        self.assertEqual(result, [])


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

    def test_update_whitespace_only_last_name_raises(self):
        with self.assertRaises(ValueError):
            logic.update_user(self._uid, "   ", "", "テスト", "", 1, 0)

    def test_update_whitespace_only_kana_raises(self):
        with self.assertRaises(ValueError):
            logic.update_user(self._uid, "姓", "", "   ", "", 1, 0)

    def test_update_none_last_name_raises(self):
        with self.assertRaises(ValueError):
            logic.update_user(self._uid, None, "", "テスト", "", 1, 0)

    def test_update_roman_in_kana_raises(self):
        with self.assertRaises(ValueError):
            logic.update_user(self._uid, "姓", "", "Smith", "", 1, 0)


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


class TestTempSchedule(unittest.TestCase):

    def setUp(self):
        self._fd, self._path = tempfile.mkstemp(suffix=".db")
        os.close(self._fd)
        logic.set_db_path(self._path)
        logic.init_db()
        self._uid = logic.add_user("臨時テスト", "", "リンジテスト", "", 1)

    def tearDown(self):
        logic.set_db_path(None)
        os.unlink(self._path)

    # ── 正常系 ──────────────────────────────────────────────

    def test_set_and_get(self):
        logic.set_temp_schedule(self._uid, "2099-04-01", "2099-04-07",
                                [(0, 2, ""), (2, 1, "メモ")])
        ts = logic.get_temp_schedule(self._uid)
        self.assertIsNotNone(ts)
        self.assertEqual(ts['start_date'], "2099-04-01")
        self.assertEqual(ts['end_date'],   "2099-04-07")
        self.assertEqual(len(ts['days']), 2)

    def test_single_day_end_date_none(self):
        """終了日なし → 1日のみ適用"""
        logic.set_temp_schedule(self._uid, "2099-06-01", None, [(0, 2, "")])
        ts = logic.get_temp_schedule(self._uid)
        self.assertIsNone(ts['end_date'])

    def test_replace_existing(self):
        """上書き登録で古い設定が消えること"""
        logic.set_temp_schedule(self._uid, "2099-04-01", "2099-04-07", [(0, 2, "")])
        logic.set_temp_schedule(self._uid, "2099-05-01", "2099-05-03", [(1, 1, "")])
        ts = logic.get_temp_schedule(self._uid)
        self.assertEqual(ts['start_date'], "2099-05-01")
        self.assertEqual(len(ts['days']), 1)
        self.assertEqual(ts['days'][0]['day_of_week'], 1)

    def test_delete(self):
        logic.set_temp_schedule(self._uid, "2099-04-01", None, [(0, 2, "")])
        logic.delete_temp_schedule(self._uid)
        self.assertIsNone(logic.get_temp_schedule(self._uid))

    def test_delete_nonexistent_no_error(self):
        logic.delete_temp_schedule(9999)

    def test_get_all_active(self):
        uid2 = logic.add_user("別ユーザー", "", "ベツユーザー", "", 2)
        logic.set_temp_schedule(self._uid, "2099-04-01", "2099-04-07", [(0, 2, "")])
        logic.set_temp_schedule(uid2,      "2099-05-01", None,         [(3, 1, "")])
        result = logic.get_all_active_temp_schedules()
        self.assertEqual(len(result), 2)

    def test_get_active_user_ids_empty(self):
        """今日有効な臨時スケジュールがない場合"""
        ids = logic.get_active_temp_schedule_user_ids()
        self.assertEqual(ids, set())

    def test_user_deleted_cascades_temp(self):
        """ユーザー削除で臨時スケジュールも消えること"""
        logic.set_temp_schedule(self._uid, "2099-04-01", None, [(0, 2, "")])
        logic.delete_user(self._uid)
        logic.set_db_path(self._path)
        # DBに残っていないことをSQLで直接確認
        import sqlite3
        conn = sqlite3.connect(self._path)
        row = conn.execute(
            "SELECT COUNT(*) FROM m_user_temp_schedules WHERE user_id=?", (self._uid,)
        ).fetchone()
        conn.close()
        self.assertEqual(row[0], 0)

    # ── 異常系 ──────────────────────────────────────────────

    def test_invalid_date_format_raises(self):
        with self.assertRaises(ValueError):
            logic.set_temp_schedule(self._uid, "2099/04/01", None, [(0, 2, "")])

    def test_end_before_start_raises(self):
        with self.assertRaises(ValueError):
            logic.set_temp_schedule(self._uid, "2099-04-10", "2099-04-01", [(0, 2, "")])

    def test_no_days_raises(self):
        with self.assertRaises(ValueError):
            logic.set_temp_schedule(self._uid, "2099-04-01", None, [])

    def test_is_absence_stored_and_retrieved(self):
        """is_absence フラグが保存・取得できること"""
        logic.set_temp_schedule(self._uid, "2099-04-01", "2099-04-07",
                                [(0, 2, "", 1), (1, 1, "", 0)])
        ts = logic.get_temp_schedule(self._uid)
        days = {d['day_of_week']: d for d in ts['days']}
        self.assertEqual(days[0]['is_absence'], 1)
        self.assertEqual(days[1]['is_absence'], 0)

    def test_is_absence_defaults_to_zero(self):
        """3要素タプルで登録した場合 is_absence は 0"""
        logic.set_temp_schedule(self._uid, "2099-04-01", None, [(0, 2, "")])
        ts = logic.get_temp_schedule(self._uid)
        self.assertEqual(ts['days'][0]['is_absence'], 0)

    def test_end_date_same_as_start_date_is_valid(self):
        """end_date == start_date (明示的同日指定) は有効"""
        logic.set_temp_schedule(self._uid, "2099-06-01", "2099-06-01", [(0, 1, "")])
        ts = logic.get_temp_schedule(self._uid)
        self.assertIsNotNone(ts)
        self.assertEqual(ts['end_date'], "2099-06-01")

    def test_active_ids_includes_future_schedule(self):
        """未来日付の臨時でも期限切れでなければ ID が返る"""
        logic.set_temp_schedule(self._uid, "2099-01-01", "2099-12-31", [(0, 1, "")])
        ids = logic.get_active_temp_schedule_user_ids()
        self.assertIn(self._uid, ids)

    def test_active_ids_excludes_expired_single_day(self):
        """過去の1日のみ臨時は startup cleanup 後に返らない（init_db 呼び出し）"""
        import sqlite3
        conn = sqlite3.connect(self._path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            "INSERT INTO m_user_temp_schedules (user_id, start_date, end_date) VALUES (?,?,?)",
            (self._uid, "2000-01-01", None)
        )
        temp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO m_user_temp_schedule_days (temp_id, day_of_week, bath_type, bath_memo) VALUES (?,?,?,?)",
            (temp_id, 0, 1, "")
        )
        conn.commit()
        conn.close()
        logic.init_db()  # cleanup 実行
        ids = logic.get_active_temp_schedule_user_ids()
        self.assertNotIn(self._uid, ids)

    def test_multiple_users_active_ids(self):
        """複数ユーザーの臨時設定で全員返ること"""
        uid2 = logic.add_user("二番目", "", "ニバンメ", "", 2)
        logic.set_temp_schedule(self._uid, "2099-01-01", "2099-12-31", [(0, 1, "")])
        logic.set_temp_schedule(uid2,      "2099-06-01", None,         [(3, 2, "")])
        ids = logic.get_active_temp_schedule_user_ids()
        self.assertIn(self._uid, ids)
        self.assertIn(uid2, ids)

    def test_whitespace_date_raises(self):
        """空白の日付文字列はエラー"""
        with self.assertRaises(ValueError):
            logic.set_temp_schedule(self._uid, "   ", None, [(0, 1, "")])

    def test_invalid_end_date_format_raises(self):
        """終了日の不正フォーマットはエラー"""
        with self.assertRaises(ValueError):
            logic.set_temp_schedule(self._uid, "2099-04-01", "2099/04/07", [(0, 1, "")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
