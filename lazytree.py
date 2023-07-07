#!/usr/bin/env python3
# Test copy_dir and FileSystem.tree()
import fs
from fs.copy import copy_dir
import os
from pyfatfs.PyFat import PyFat
import shutil
import tempfile
import uuid

TempFolder = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
print("\nTempFolder: %s\n" % TempFolder)
os.mkdir(TempFolder)

OutFile = os.path.join(TempFolder, "outfile.bin")
InputDir = os.path.join(TempFolder, "indir")
OutputDir = os.path.join(TempFolder, "outdir")
FatFsUrl = "fat://"+OutFile+"?lazy_load=True"

print("Create test files...")
os.mkdir(InputDir)
os.mkdir(os.path.join(InputDir, "sub1"))
os.mkdir(os.path.join(InputDir, "sub2"))
os.mkdir(os.path.join(InputDir, "sub1", "sub3"))
with open(os.path.join(InputDir, "sub1", "file1.txt"), 'w') as TestFile: TestFile.write("file1")
with open(os.path.join(InputDir, "sub1", "file2.txt"), 'w') as TestFile: TestFile.write("file2")
with open(os.path.join(InputDir, "sub2", "file3.txt"), 'w') as TestFile: TestFile.write("file3")
with open(os.path.join(InputDir, "sub1", "sub3", "file4.txt"), 'w') as TestFile: TestFile.write("file4")

print("Create empty FAT filesystem...")
with open(OutFile, 'wb'):
    Image = PyFat()
    Image.mkfs(OutFile, fat_type = PyFat.FAT_TYPE_FAT12, size = 1024 * 1024)
    Image.close()

print("Copy input directory into FAT FS...")
copy_dir(InputDir, "/", FatFsUrl, "/")

print("Copy FAT FS contents to output directory...")
copy_dir(FatFsUrl, "/", OutputDir, "/")

print("\nTree input dir:")
with fs.open_fs(InputDir) as FileSystem:
    FileSystem.tree(with_color=True)

print("\nTree FAT FS:")
with fs.open_fs(FatFsUrl) as FileSystem:
    FileSystem.tree(with_color=True)

print("\nTree output dir:")
with fs.open_fs(OutputDir) as FileSystem:
    FileSystem.tree(with_color=True)

print("\nRemove test folder...\n")
shutil.rmtree(TempFolder)
