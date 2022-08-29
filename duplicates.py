#!/usr/bin/python3

__doc__ = """Script for finding duplicated files in a given directory and subdirectories"""


import hashlib
import re
import os
import time
import argparse
import sys
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from datetime import datetime


@dataclass
class FileMetadata:
    """
        File basic params.
    """

    def __init__(self, filepath: str) -> None:
        self._size = os.path.getsize(filepath)
        self._mtime = os.path.getmtime(filepath)
        self._ctime = os.path.getctime(filepath)

    @property
    def size(self):
        """file size"""
        return self._size

    @property
    def mtime(self):
        """file modified time"""
        return self._mtime

    @property
    def ctime(self):
        """file created time"""
        return self._ctime

    def __repr__(self) -> str:
        format = '%Y-%m-%d %H:%M:%S'
        return f"FileMetadata: size={self.size/1024:.2f}kb " \
               f"created={datetime.utcfromtimestamp(self.ctime).strftime(format)} " \
               f"modified={datetime.utcfromtimestamp(self.mtime).strftime(format)}"


@dataclass
class Item:
    """
        Used just to keep together path and file md5 hash.
    """

    def __init__(self, path: str, md5: str, metadata: FileMetadata):
        self._path = path
        self._md5 = md5
        self._metadata = metadata

    @property
    def path(self):
        """path getter"""
        return self._path

    @property
    def md5(self):
        """md5 getter"""
        return self._md5

    @property
    def metadata(self):
        """metadata getter"""
        return self._metadata

    def __repr__(self):
        return f"{self.md5} - {self.path}"


class FileBrowser:
    """
        Class used to find all files in the given directory and subdirectories.
        For each found file ItemHandler.handle() will be called.
    """

    def __init__(self, directory_path):
        self.directory_path = directory_path

    @staticmethod
    def _handle_item(handler, file_plus_path, filename):
        handler.handle(file_plus_path, filename)

    def _process_files(self, directory_path, name_regex, handler):
        try:
            for file_name in os.listdir(directory_path):
                file_plus_path = os.path.join(directory_path, file_name)
                if os.path.isfile(file_plus_path):
                    if not name_regex:
                        FileBrowser._handle_item(handler, file_plus_path, file_name)
                    else:
                        if name_regex.match(file_name):
                            FileBrowser._handle_item(handler, file_plus_path, file_name)
                elif os.path.isdir(file_plus_path):
                    self._process_files(file_plus_path, name_regex, handler)
        except PermissionError:
            print(f"[Error] Permission denied to: {directory_path}")

    def process_files(self, name_regex, handler):
        """Method to find files and validate input.
        :param name_regex: regex object to filter file names
        :param handler: this object will be called if some file will be found
        """
        if not isinstance(handler, Handler):
            raise ValueError(f"handler must be a Handler instance {handler} - {Handler}")
        if name_regex and not isinstance(name_regex, re.Pattern):
            raise ValueError(
                f"nameRegex must be a instance of re.Pattern {name_regex} - {re.Pattern}")
        self._process_files(self.directory_path, name_regex, handler)


class Handler:
    """Base class used by FileBrowser.process_files()
       to process results"""
    def handle(self, path, file_name):
        """Callback method"""
        raise NotImplementedError


class FileFoundHandler(Handler):
    """Class used for saving data and calculating md5 hashes"""

    def __init__(self):
        self._out_list = []
        self._found_files = []
        self._cache = None

    @staticmethod
    def _calculate_md5(path):
        hash_md5 = hashlib.md5()
        with open(path, "rb") as file_object:
            for block in iter(lambda: file_object.read(4096), b''):
                hash_md5.update(block)
        return hash_md5.hexdigest()

    @staticmethod
    def _do_work(path):
        md5 = FileFoundHandler._calculate_md5(path)
        metadata = FileMetadata(path)
        i = Item(path, md5, metadata)
        return i

    def handle(self, path, file_name):
        """
        Callback for each found file
        :param path: file path
        :param file_name: file name
        """
        self._found_files.append(path)
        sys.stdout.write(f"Files count: {len(self._found_files)}   \r")
        sys.stdout.flush()

    def get_files_list(self):
        """Return gathered data"""
        if self._cache:
            return self._cache

        def update_std_out(index, size):
            sys.stdout.write(f"Progress: {index}/{size}   \r")
            sys.stdout.flush()

        ready_results = []
        with Pool(cpu_count()) as pool:
            workers = []
            for file_path in self._found_files:
                workers.append(pool.apply_async(FileFoundHandler._do_work, args=(file_path,)))
            for i, result in enumerate(workers):
                ready_results.append(result.get())
                update_std_out(i, len(workers))
        self._cache = ready_results
        return ready_results


class Data:
    """Class for managing data gathered data"""

    def __init__(self):
        self._items = []

    def check_dir(self, path, name_reg=None):
        """
        Get files list
        :param path: root path
        :param name_reg: file name filter
        :return: files list
        """
        file_browser_object = FileBrowser(path)
        item_handler_object = FileFoundHandler()

        print("Indexing...")
        file_browser_object.process_files(name_reg, item_handler_object)
        print("Calculating md5...")
        self._items = item_handler_object.get_files_list()
        return self._items

    def check_for_duplicates(self, delete=None, files_list=None):
        """
        Search for duplicated files
        :param delete: if not none duplicated files will be deleted
        :param files_list: custom files list, if none cached list will be used
        """
        print("Duplicate searching...")
        count = 0
        wasted_space = 0
        files_list = files_list or self._items
        data_sorted = sorted(files_list, key=lambda item: item.md5)
        for i, item_at_i in enumerate(data_sorted):
            if i > 0 and item_at_i.md5 == data_sorted[i - 1].md5:
                count += 1
                wasted_space += item_at_i.metadata.size
                print(f"{count}. Duplicate found! "
                      f"[{item_at_i.metadata}] "
                      f"\n\t[{str(data_sorted[i - 1].path)} - {str(item_at_i.path)}]")
                if delete:
                    print(f"Deleting {item_at_i.path}")
                    os.remove(item_at_i.path)
        print(f"\nSummary:\n\tduplicates={count}\n\twasted space={wasted_space/1024:.2f}kb\n")


def main():
    """Entry function"""
    parser = argparse.ArgumentParser(description='Check duplicates in given folder and subfolders.')
    parser.add_argument('-r', '--root',
                        help='starting directory for the script',
                        default=os.getcwd(),
                        required=False)
    parser.add_argument('-data_object', '--delete',
                        action='store_true',
                        help="delete duplicates",
                        required=False)
    args = parser.parse_args()

    print(f"[root={args.root}, delete={str(args.delete)}]")

    time_start = time.time()
    try:
        data_object = Data()
        data_object.check_dir(args.root, None)
        data_object.check_for_duplicates(args.delete)
    except KeyboardInterrupt:
        print("Interrupted!")
    finally:
        time_elapsed = time.time() - time_start
    print(f"Done, took={time_elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
