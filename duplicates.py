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

    def __processFilesR__(self, directoryPath, nameRegex, handler, outList):
        for f in os.listdir(directoryPath):
            filePlusPath = os.path.join(directoryPath, f)
            if os.path.isfile(filePlusPath):
                if not nameRegex:
                    handler.Handle(filePlusPath, f, outList)
                else:
                    if nameRegex.match(f):
                        handler.Handle(filePlusPath, f, outList)
            elif os.path.isdir(filePlusPath):
                self.__processFilesR__(filePlusPath, nameRegex, handler, outList)

    def ProcessFiles(self, nameRegex, handler, outList):
        if not isinstance(handler, Handler):
            raise ValueError("handler must be a Handler instance %s - %s" % (handler, Handler))
        if nameRegex and not isinstance(nameRegex, re.Pattern):
            raise ValueError("nameRegex must be a instance of re.Pattern %s - %s" % (nameRegex, re.Pattern))

        self.__processFilesR__(self.m_directoryPath, nameRegex, handler, outList)


class Handler:
    def Handle(self, path, fileName, outList): raise NotImplementedError


class ItemHandler(Handler):
    def __init__(self):
        pass

    def __calculateMd5__(self, path):
        hashMd5 = hashlib.md5()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(4096), b''):
                hashMd5.update(block)
        return hashMd5.hexdigest()

    def Handle(self, path, fileName, outList):
        md5 = self.__calculateMd5__(path)
        i = Item(path, md5)
        outList.append(i)


class Data:
    def __init__(self):
        self.items = []

    def AnalyzeDir(self, path, nameReg = None):
        o = FileBrowser(path)
        h = ItemHandler()
        o.ProcessFiles(nameReg, h, self.items)

    def RemoveDuplicates(self, delete):
        dataSorted = sorted(self.items, key=lambda item: item.md5)
        for i in range(0, len(dataSorted)):
            if i > 0 and dataSorted[i].md5 == dataSorted[i - 1].md5:
                print("Duplicate found! [%s - %s]" % (str(dataSorted[i - 1].path), str(dataSorted[i].path)))
                if delete:
                    print("Deleting " + dataSorted[i].path)
                    os.remove(dataSorted[i].path)


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
    d.AnalyzeDir(args.root, None)
    d.RemoveDuplicates(args.delete)

    print("Done!")

if __name__ == "__main__":
    main()