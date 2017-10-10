# -*- coding: utf-8 -*-

"""Module file for the Guard base class.

The Guard class allow to safely checkpoint information during an optimization
process.
"""

import json
import os
import time
import uuid
import glob


class Guard(object):
    """Guard main class.

    Guard is the base class making checkpoints. Everytime the method
    `checkpoint` is called. A json file file is created under
    {dir_path}/{exp_name}/meta with metadata given. A summary file is created
    under {dir_path}/{exp_name} with the recards for the last and best
    checkpoint (where applies).

    When making checkpoint needs heavier or specific serialization, the methods
    `serialize` and `deserialize` can be extanded to build a user-defined
    behaviour.
    """

    def __init__(self, dir_path, exp_name, mode="all", best_key=None,
                 best_compare=lambda x, y: x < y, cache=True):
        """Create the object.

        Class constructor to defines future behaviours.

        Parameters
        ----------
        dir_path : str
            Path of the root directories where experiences are stored.
        exp_name : str
            Experience name. Creates a sub-direcctory for the experience.
        mode : str
            Storing mode. Currently supported are:
                'all' : all checkpoints are kept.
                'last': the last checkpoint is kept
                'best': the best checkpoint is kept (Needs best_key).
            It is possible to combine last and best using 'last,best'.
        best_key : any
            Key used to compare best performances in all checkpoints.
        best_compare : function
            function(x, y) returns True if x is better than y. Used to compare
            best performances.
        cache : bool
            Cache summary. Memory cache used for single instance process.
        """
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
        """Get the summary.

        Gets the summary file as a dictionnary. If cache is used the cache is
        returned.

        Returns
        -------
        dict
            The summary file or an empty dictionnary if no file is found.
        """
        if self._summary is not None and self._cache:
            return self._summary
        if os.path.exists(self._summary_file):
            with open(self._summary_file, "r") as f:
                return json.load(f)
        return {}

    def write_summary(self, summary):
        """Write in the summary.

        Write the given dictionnary in the file as a json. Updated the cache if
        the cache is used.

        Parameters
        ----------
        summary : dict
            Information to write in the summary. Usually with an nested
            structure.
        """
        if self._cache:
            self._summary = summary
        with open(self._summary_file, "w+") as f:
            json.dump(summary, f, indent=2)

    def update_summary(self, meta):
        """Udpate the summary.

        Updates the summary with the new metadata checkpoints and write it to
        the file. If 'best' or 'last' can be computed, they will be added to
        the summary.

        Parameters
        ----------
        meta : dict
            The last checkpoint information.

        Returns
        -------
        summary : dict
            The updated summary.
        """
        summary = self.get_summary()

        summary["last"] = meta

        if self._best_key is not None:
            if "best" not in summary or self._best_key not in summary["best"]:
                summary["best"] = meta
            else:
                old_metric = summary["best"][self._best_key]
                new_metric = meta[self._best_key]
                if self._best_compare(new_metric, old_metric):
                        summary["best"] = meta

        self.write_summary(summary)
        return summary

    def cleanup(self):
        """Cleanup.

        Clear files that do not match the storing mode.
        """
        if "all" in self._mode:
            return
        summary = self.get_summary()
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

    def save_meta(self, meta):
        """Save the metadata to the file.

        Save the metadata given in the checkpoints to the metadata file. the
        following information is added: time, timestamp and an id.

        Parameters
        ----------
        meta : dict
            Metadata to save.

        Retruns
        -------
        id : str
            The id given to the metadata (and thus the checkpoint).
        """
        timestamp = time.time()
        date_time = time.strftime('%Y-%m-%d %H:%M:%S %Z',
                                  time.localtime(timestamp))
        id = str(uuid.uuid4())
        meta.update({
            "id": id,
            "timestamp": timestamp,
            "date_time": date_time,
        })

        with open(os.path.join(self._meta_path, id + ".json"), "w+") as f:
            json.dump(meta, f, indent=2)

        return id

    def checkpoint(self, meta={}, *args, **kwargs):
        """Make a checkpoint.

        Save the metadata according to the storing mode, call for serialization
        and update the summary file.

        Parameters
        ----------
        meta : dict
            Metadata to save.
        *args, **kwargs
            Argument passed to the serialization function.

        Returns
        -------
        result : any
            Return of the serialization function.
        """
        id = self.save_meta(meta)
        path = os.path.join(self._dump_path, id)
        result = self.serialize(path, *args, **kwargs)
        self.update_summary(meta)
        self.cleanup()
        return result

    def serialize(self, path, *args, **kwargs):
        """Serialization.

        Method to save special parameters for the checkpoint. Extend this
        function to save the heavyweight specifics of your process.

        Parameters
        ----------
        path : str
            Filename where to save your information.
        *args, **kwargs
            Argument passed to the checkpoint function.

        Returns
        -------
        any
            Will be returned by the checkpoint function.
        """
        return NotImplemented

    def deserialize(self, path, *args, **kwargs):
        """Deserialization.

        Method to load special checkpointed parameters. Extend this
        function to load the heavyweight specifics of your process.

        Parameters
        ----------
        path : str
            Filename where the information was saved.
        *args, **kwargs
            Argument passed to the loading functions.

        Returns
        -------
        any
            Will be returned by the loading function.
        """
        return NotImplemented

    def remove(self, path):
        """Remove the serialized data.

        Method to removed the data created by serialized. This method removes
        all files starting with the given path. It can be overriden for mode
        complex serialized objects.

        Parameters
        ----------
        path : str
            Filename where the data was saved.
        """
        id = os.path.splitext(os.path.basename(path))[0]
        filenames = os.path.join(self._dump_path, id + "*")
        for file in glob.glob(filenames):
            os.remove(file)

    def get_best(self):
        """Best metadata.

        Returns the best metadata in the process.

        Returns
        -------
        dict
            The best metadata.
        """
        summary = self.get_summary()
        return summary.get("best", None)

    def deserialize_best(self, *args, **kwargs):
        """Deserialize best object.

        Call deserialize on the best object in the process.

        Parameters
        ----------
        *args, **kwargs
            Arguments passed to deserialize along with the path.

        Returns
        -------
        any
            The retrun of the deserialize.
        """
        best_id = self.get_summary()["best"]["id"]
        path = os.path.join(self._dump_path, best_id)
        return self.deserialize(path, *args, **kwargs)

    def get_last(self):
        """Best metadata.

        Returns the last metadata in the process.

        Returns
        -------
        dict
            The last metadata.
        """
        summary = self.get_summary()
        return summary.get("last", None)

    def deserialize_last(self, *args, **kwargs):
        """Deserialize last object.

        Call deserialize on the last object in the process.

        Parameters
        ----------
        *args, **kwargs
            Arguments passed to deserialize along with the path.

        Returns
        -------
        any
            The retrun of the deserialize.
        """
        last_id = self.get_summary()["last"]["id"]
        path = os.path.join(self._dump_path, last_id)
        return self.deserialize(path, *args, **kwargs)

    def has_history(self):
        """Experiment history.

        Check wether the experiment has previous history (files written).

        Returns
        -------
        bool
            Wether the experiment has previous history.
        """
        return os.path.exists(self._summary_file)

    def get_history(self):
        """Get all history.

        Gets all history into one single dictionary. All dictionares are
        aggregated into one dictionary. Every value in the dictionary is thus a
        list of every file's values. Missing values are filled with `None`.
        Values are sorted by the 'timestamp' of the witting.

        Returns
        -------
        dict
            The dictionary of all entries.
        """
        meta_filenames = os.path.join(self._meta_path, "*.json")
        all_meta = list(map(json.load, glob.glob(meta_filenames)))
        all_meta.sort(key=lambda d: d.get("timestamp", 0))

        history = {}
        for n, meta in enumerate(all_meta):
            for k in meta:
                if k in history:
                    history[k].append(meta[k])
                else:
                    history[k] = n*[None] + [meta[k]]
            for k in history:
                if k not in meta:
                    history[k].append(None)
        return history
