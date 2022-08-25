#!/usr/bin/python3

import hashlib
import re
import os
import argparse


class Item:
    def __init__(self, path, md5):
        self.path = path
        self.md5 = md5


class FileBrowser:
    def __init__(self, directoryPath):
        self.m_directoryPath = directoryPath

    def _process_files(self, directoryPath, name_regex, handler, out_list):
        for f in os.listdir(directoryPath):
            filePlusPath = os.path.join(directoryPath, f)
            if os.path.isfile(filePlusPath):
                if not name_regex:
                    handler.handle(filePlusPath, f, out_list)
                else:
                    if name_regex.match(f):
                        handler.handle(filePlusPath, f, out_list)
            elif os.path.isdir(filePlusPath):
                self._process_files(filePlusPath, name_regex, handler, out_list)

    def process_files(self, nameRegex, handler, outList):
        if not isinstance(handler, Handler):
            raise ValueError("handler must be a Handler instance %s - %s" % (handler, Handler))
        if nameRegex and not isinstance(nameRegex, re.Pattern):
            raise ValueError("nameRegex must be a instance of re.Pattern %s - %s" % (nameRegex, re.Pattern))

        self._process_files(self.m_directoryPath, nameRegex, handler, outList)


class Handler:
    def handle(self, path, fileName, outList): raise NotImplementedError


class ItemHandler(Handler):
    def __init__(self):
        pass

    def _calculate_md5(self, path):
        hashMd5 = hashlib.md5()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(4096), b''):
                hashMd5.update(block)
        return hashMd5.hexdigest()

    def handle(self, path, fileName, outList):
        md5 = self._calculate_md5(path)
        i = Item(path, md5)
        outList.append(i)


class Data:
    def __init__(self):
        self.items = []

    def check_dir(self, path, nameReg = None):
        o = FileBrowser(path)
        h = ItemHandler()
        o.process_files(nameReg, h, self.items)

    def check_for_duplicates(self, delete):
        data_sorted = sorted(self.items, key=lambda item: item.md5)
        for i in range(0, len(data_sorted)):
            if i > 0 and data_sorted[i].md5 == data_sorted[i - 1].md5:
                print("Duplicate found! [%s - %s]" % (str(data_sorted[i - 1].path), str(data_sorted[i].path)))
                if delete:
                    print("Deleting " + data_sorted[i].path)
                    os.remove(data_sorted[i].path)


def main():
    parser = argparse.ArgumentParser(description='Check duplicates in given folder and subfolders.')
    parser.add_argument('-r', '--root',
                        help='starting directory for the script',
                        default=os.getcwd(),
                        required=False)
    parser.add_argument('-d', '--delete',
                        action='store_true',
                        help="delete duplicates",
                        required=False)
    args = parser.parse_args()

    print("[root=%s, delete=%s] Calculating md5..." % (args.root, str(args.delete)))

    d = Data()
    d.check_dir(args.root, None)
    d.check_for_duplicates(args.delete)

    print("Done!")

if __name__ == "__main__":
    main()