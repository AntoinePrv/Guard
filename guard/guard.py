# -*- coding: utf-8 -*-

"""
"""

import json
import os
import time
import uuid
import glob


class Guard(object):

    def __init__(self, dir_path, exp_name, mode="all", best_key=None,
                 best_compare=lambda x, y: x < y, cache=True):
        self._name = exp_name
        self._root_path = os.path.join(dir_path, exp_name)
        self._meta_path = os.path.join(self._root_path, "meta")
        self._dump_path = os.path.join(self._root_path, "dump")
        self._summary_file = os.path.join(self._root_path, "summary.json")
        self._mode = mode
        self._best_key = best_key
        self._best_compare = best_compare
        self._summary = None
        self._cache = cache

        if not os.path.exists(self._meta_path):
            os.makedirs(self._meta_path)
        if not os.path.exists(self._dump_path):
            os.makedirs(self._dump_path)

    def get_summary(self):
        if self._summary is not None and self._cache:
            return self._summary
        if os.path.exists(self._summary_file):
            with open(self._summary_file, "r") as f:
                return json.load(f)
        return {}

    def write_summary(self, summary):
        if self._cache:
            self._summary = summary
        with open(self._summary_file, "w+") as f:
            json.dump(summary, f, indent=2)

    def update_summary(self, data):
        summary = self.get_summary()

        summary["last"] = data

        if self._best_key is not None:
            if "best" not in summary or self._best_key not in summary["best"]:
                summary["best"] = data
            else:
                old_metric = summary["best"][self._best_key]
                new_metric = data[self._best_key]
                if self._best_compare(new_metric, old_metric):
                        summary["best"] = data

        self.write_summary(summary)
        return summary

    def cleanup(self, summary):
        # TODO change summary as optional for external use
        if "all" in self._mode:
            return
        keep = []
        if "best" in self._mode:
            keep.append(summary.get("best", {}).get("id", None))
        if "last" in self._mode:
            keep.append(summary.get("last", {}).get("id", None))

        meta_filenames = os.path.join(self._meta_path, "*.json")
        for m_file in glob.glob(meta_filenames):
            id = os.path.splitext(os.path.basename(m_file))[0]
            if id not in keep:
                os.remove(m_file)
                self.remove(os.path.join(self._dump_path, id))

    def save_meta(self, data):
        timestamp = time.time()
        date_time = time.strftime('%Y-%m-%d %H:%M:%S %Z',
                                  time.localtime(timestamp))
        id = str(uuid.uuid4())
        data.update({
            "id": id,
            "timestamp": timestamp,
            "date_time": date_time,
        })

        with open(os.path.join(self._meta_path, id + ".json"), "w+") as f:
            json.dump(data, f, indent=2)

        return id

    def checkpoint(self, data={}, *args, **kwargs):
        id = self.save_meta(data)
        path = os.path.join(self._dump_path, id)
        self.serialize(path, *args, **kwargs)
        summary = self.update_summary(data)
        self.cleanup(summary)

    def serialize(self, path, *args, **kwargs):
        return NotImplemented

    def deserialize(self, path, *args, **kwargs):
        return NotImplemented

    def remove(self, path):
        id = os.path.splitext(os.path.basename(path))[0]
        filenames = os.path.join(self._dump_path, id + "*")
        for file in glob.glob(filenames):
            os.remove(file)

    def get_best(self):
        summary = self.get_summary()
        return summary.get("best", None)

    def deserialize_best(self, *args, **kwargs):
        best_id = self.get_summary()["best"]["id"]
        path = os.path.join(self._dump_path, best_id)
        return self.deserialize(path, *args, **kwargs)

    def get_last(self):
        summary = self.get_summary()
        return summary.get("last", None)

    def deserialize_last(self, *args, **kwargs):
        last_id = self.get_summary()["last"]["id"]
        path = os.path.join(self._dump_path, last_id)
        return self.deserialize(path, *args, **kwargs)

    def has_history(self):
        raise NotImplementedError
