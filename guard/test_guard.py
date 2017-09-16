# -*- coding: utf-8 -*-

""" Test file for the guard module.
"""

import unittest
import os.path
from unittest import mock
from .guard import Guard


class TestGuardInit(unittest.TestCase):

    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists", return_value=False)
    def test_init(self, mock_exists, mock_makedirs):
        guard = Guard("dir", "exp", "last", best_key="loss")
        self.assertEqual(guard._name, "exp")
        self.assertEqual(guard._root_path, "dir/exp")
        self.assertEqual(guard._meta_path, "dir/exp/meta")
        self.assertEqual(guard._dump_path, "dir/exp/dump")
        self.assertEqual(guard._summary_file, "dir/exp/summary.json")
        self.assertEqual(guard._mode, "last")
        self.assertEqual(guard._best_key, "loss")
        self.assertTrue(guard._best_compare(1, 2))
        self.assertIsNone(guard._summary)
        mock_exists.assert_called_with("dir/exp/dump")
        mock_makedirs.assert_called_with("dir/exp/dump")


class TestGuard(unittest.TestCase):

    @mock.patch("os.makedirs")
    @mock.patch("os.path.exists")
    def setUp(self, mock_exists, mock_makedirs):
        self.guard = Guard("dir", "exp", "last,best", best_key="loss")

    @mock.patch("builtins.open",
                new_callable=mock.mock_open,
                read_data='{"a": 1}')
    @mock.patch("os.path.exists")
    def test_get_summary(self, mock_exists, mock_open):
        summary = self.guard.get_summary()
        mock_exists.assert_called_once_with(self.guard._summary_file)
        self.assertDictEqual(summary, {"a": 1})

    @mock.patch("json.dump")
    @mock.patch("builtins.open")
    def test_write_summary(self, mock_open, mock_dump):
        data = {"b": 2}
        self.guard.write_summary(data)
        self.assertDictEqual(self.guard._summary, data)
        mock_dump.assert_called_once()

    @mock.patch("guard.guard.Guard.write_summary")
    @mock.patch("guard.guard.Guard.get_summary",
                return_value={"best": {"loss": 2}})
    def test_update_summary(self, mock_get, mock_write):
        s = self.guard.update_summary({"loss": 3})
        mock_get.assert_called_once()
        mock_write.assert_called_once()
        self.assertEqual(s["best"]["loss"], 2)
        self.assertEqual(s["last"]["loss"], 3)

    @mock.patch("guard.guard.Guard.remove")
    @mock.patch("glob.glob", return_value=["1.json", "2.json"])
    @mock.patch("os.remove")
    def test_cleanup(self, mock_osremove, mock_glob, mock_remove):
        self.guard.cleanup({"last": {"id": "1"}})
        mock_osremove.assert_called_once_with("2.json")

    @mock.patch("json.dump")
    @mock.patch("builtins.open")
    def test_save_meta(self, mock_open, mock_dump):
        self.guard.save_meta({})
        mock_open.assert_called_once()
        mock_dump.assert_called_once()

    @mock.patch("guard.guard.Guard.cleanup")
    @mock.patch("guard.guard.Guard.update_summary")
    @mock.patch("guard.guard.Guard.serialize")
    @mock.patch("guard.guard.Guard.save_meta", return_value="1")
    def test_checkpoint(self, mock_save, mock_ser, mock_update, mock_clean):
        data = {"a": 3}
        self.guard.checkpoint(data=data)
        mock_save.assert_called_once_with(data)
        mock_ser.assert_called_once_with(
            os.path.join(self.guard._dump_path, "1"))
        mock_update.assert_called_once_with(data)
        mock_clean.assert_called_once()

    def test_serialize(self):
        self.assertEqual(self.guard.serialize("path"), NotImplemented)

    def test_deserialize(self):
        self.assertEqual(self.guard.deserialize("path"), NotImplemented)

    @mock.patch("glob.glob",
                return_value=["dir/exp/dump/1.txt", "dir/exp/dump/1.csv"])
    @mock.patch("os.remove")
    def test_remove(self, mock_remove, mock_glob):
        self.guard.remove(os.path.join(self.guard._dump_path, "1"))
        mock_glob.assert_called_once_with(
            os.path.join(self.guard._dump_path, "1*"))
        mock_remove.assert_any_call(
            os.path.join(self.guard._dump_path, "1.txt"))
        mock_remove.assert_any_call(
            os.path.join(self.guard._dump_path, "1.csv"))

    @mock.patch("guard.guard.Guard.get_summary",
                return_value={"best": {}})
    def test_get_best(self, mock_summary):
        data = self.guard.get_best()
        mock_summary.assert_called_once()
        self.assertDictEqual(data, {})

    @mock.patch("guard.guard.Guard.deserialize")
    @mock.patch("guard.guard.Guard.get_summary",
                return_value={"best": {"id": "1"}})
    def test_deserialize_best(self, mock_summary, mock_deser):
        self.guard.deserialize_best(0, a=2)
        mock_summary.assert_called_once()
        mock_deser.assert_called_once_with(os.path.join(
            self.guard._dump_path, "1"), 0, a=2)

    @mock.patch("guard.guard.Guard.get_summary",
                return_value={"last": {}})
    def test_get_last(self, mock_summary):
        data = self.guard.get_last()
        mock_summary.assert_called_once()
        self.assertDictEqual(data, {})

    @mock.patch("guard.guard.Guard.deserialize")
    @mock.patch("guard.guard.Guard.get_summary",
                return_value={"last": {"id": "1"}})
    def test_deserialize_last(self, mock_summary, mock_deser):
        self.guard.deserialize_last(0, a=2)
        mock_summary.assert_called_once()
        mock_deser.assert_called_once_with(os.path.join(
            self.guard._dump_path, "1"), 0, a=2)
