#!/usr/bin/python3

import os
import re
import sys
import glob
import json
import pprint
import shutil
import argparse
import logging
import subprocess

KNOWN_EXT = [".jpg", ".mov", ".mp4", ".mts", ".heic"]
DB_FILENAME = "photo_index.db"

logger = logging.getLogger(__name__)

def get_size(file_path):
    return str(os.path.getsize(file_path))

def get_md5(file_path):
    output = subprocess.check_output("md5sum '" + file_path + "'", shell=True).decode('utf-8')
    return output.split()[0]

def get_base_path(date_str):
    t = date_str.split('-')
    return t[0] + '/' + t[0] + '_' + t[1]

def get_created_date_time(file_path):

    regex = re.compile(r': (?P<date>\d{4}:\d{2}:\d{2}) (?P<time>\d{2}:\d{2}:\d{2})')
    try:

        output = subprocess.check_output("exiftool '" + file_path + "' | grep '^Create Date'", shell=True).decode('utf-8')
        create_date = output.split('\n')[0]

        # Create Date                     : 2014:12:13 17:00:35
        result = regex.search(create_date)
        if result:
            return result.group('date').replace(":","-"), result.group('time')

    except:
        output = subprocess.check_output("exiftool '" + file_path + "' | grep '^File Inode Change Date/Time'", shell=True).decode('utf-8')
        create_date = output.split('\n')[0]

        # Create Date                     : 2014:12:13 17:00:35
        result = regex.search(create_date)
        if result:
            return result.group('date').replace(":","-"), result.group('time')

    return "0000-00-00", "00:00:00"

def get_created_date_time_as_one(file_path):
    d, t = get_created_date_time(file_path)

    # return as 0000-00-00_00-00-00"
    return d + "_" + t.replace(":", "-")

def check_same_md5(now, file_list):
    now_md5 = get_md5(now)

    for f in file_list:
        if now_md5 == get_md5(f):
            logger.debug(" MD5 match")
            return f

    logger.debug(" MD5 mismatch")
    return False
        
def _copy_file(origin, new, remove):
    try:
        if remove:
            shutil.move(origin, new)
        else:
            shutil.copy(origin, new)
    except IOError as io_err:
        os.makedirs(os.path.dirname(new))
        if remove:
            shutil.move(origin, new)
        else:
            shutil.copy(origin, new)

def get_unduplicated_filename(base, filename):
    name, extension = os.path.splitext(filename)
    i = 0
    while True:
        i += 1
        temp_filepath = "%s/%s_duplicated_%d%s" % (base, name, i, extension)
        if os.path.exists(temp_filepath):
            logger.debug("  Duplicated %s" % temp_filepath)
            continue
        else:
            logger.debug("  New filename : %s" % temp_filepath)
            return temp_filepath


def copy_file(target_path, date_time, file_path, remove=False):
    new_base_path = get_base_path(date_time.split('_')[0])
    filename = os.path.basename(file_path)
    new_path = os.path.join(target_path, new_base_path, filename)

    if os.path.exists(new_path):
        logger.debug(" copy_file(): File already exists(%s). so rename current file(%s)" % (new_path, file_path))
        new_path = get_unduplicated_filename(os.path.join(target_path, new_base_path), filename)

    _copy_file(file_path, new_path, remove)
    logger.debug(" copy_file() : %s -> %s" % (file_path, new_path))
    if remove:
        logger.debug("  %s was removed" % file_path)

    return new_path

def progress(total, count, suffix=''):
    bar_len = 40
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '█' * filled_len + ' ' * (bar_len - filled_len)

    sys.stdout.write('\r[%s] %s%s (%d/%d) %s' % (bar, percents, '%', count, total, suffix))
    sys.stdout.flush()

def create_file_index_db(path):

    file_list = glob.glob(path, recursive=True)

    count = 0
    total = len(file_list)
    results = {}

    for f in file_list:

        count += 1
        progress(total, count, f)
        logger.debug("Create Index DB: %s" % f)

        if os.path.isdir(f):
            continue

        filename, file_extension = os.path.splitext(f)

        if file_extension.lower() not in KNOWN_EXT:
            logger.debug(" Skip by extension : %s" % f)
            continue

        # First key : date/time
        dt = get_created_date_time_as_one(f)
        
        # Second key : size
        size = get_size(f)

        if dt in results:
            if size in results[dt]:
                results[dt][size].append(f)
            else:
                results[dt][size] = [f]
        else:
            results[dt] = {}
            results[dt][size] = [f]
            
    return results


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', required=True,
                        help="Source path - Photo From path")
    parser.add_argument('-t', '--target', required=True,
                        help="Target path - Photo Copy to path")
    parser.add_argument('-r', '--remove_source', default=False, action="store_true",
                        help="Remove source file after file copied")
    parser.add_argument('--index_db',
                        help="Load index db for target path(skip indexing target path)")
    parser.add_argument('--logfile',
                        help="logfile for detail progress")

    args = parser.parse_args()

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', '%Y-%m-%d %H:%M:%S')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if args.remove_source:
        remove = True
    else:
        remove = False

    if args.logfile:
        file_debug_handler = logging.FileHandler(args.logfile)
        file_debug_handler.setLevel(logging.DEBUG)
        file_debug_handler.setFormatter(formatter)
        logger.addHandler(file_debug_handler)

    source_path = os.path.abspath(os.path.expanduser(args.source))
    target_path = os.path.abspath(os.path.expanduser(args.target))

    target = False
    if args.index_db:

        logger.info("Load Index DB instead of lookup target path")
        index_db = os.path.abspath(os.path.expanduser(args.index_db))
        if os.path.exists(index_db):
            with open(index_db, 'r') as fp:
                target = json.load(fp)
                logger.info("Load Index DB success")
        else:
            logger.info(" => Index DB not exists, will be save later")

    if target == False:
        logger.info("Creating DB with size/datetime for Target folder (%s)" % target_path)
        target = create_file_index_db(target_path + "/**/*")
        logger.info("\n\n")

    logger.info("Check and Copy source path to target path(%s -> %s)" % (source_path, target_path))

    file_list = glob.glob(source_path + "/**/*", recursive=True)

    count = 0
    total = len(file_list)
    static = {
        "total": total,
        "skip": 0,
        "dir": 0,
        "new_file": 0,
        "dup_file": 0,
    }

    for f in file_list:

        count += 1
        progress(total, count, f)
        logger.debug("")
        logger.debug("Current File : %s" % f)
        if os.path.isdir(f):
            static["dir"] += 1
            continue

        filename, file_extension = os.path.splitext(f)

        if file_extension.lower() not in KNOWN_EXT:
            logger.debug("Skip by extension : %s" % f)
            static["skip"] += 1
            continue

        # First key : date/time
        dt = get_created_date_time_as_one(f)
        
        # Second key : size
        size = get_size(f)

        if dt in target:
            if size in target[dt]:

                same_file = check_same_md5(f, target[dt][size])

                if same_file:
                    logger.debug(" The same target file already exists")
                    logger.debug("  Source %s - (%s)" % (f, size))
                    logger.debug("  Target %s - (%s)" % (same_file, size))
                    if remove:
                        logger.debug("   Source %s removed" % f)
                        os.remove(f)
                    static["dup_file"] += 1
                else:
                    logger.debug(" New file(case3 - the same datetime/size index exists case)")

                    new_file = copy_file(target_path, dt, f, remove)
                    target[dt][size].append(new_file)
                    static["new_file"] += 1

            else:
                logger.debug(" New file(case2 - the same datetime index exists case)")
                new_file = copy_file(target_path, dt, f, remove)
                target[dt][size] = [new_file]
                static["new_file"] += 1
        else:
            logger.debug(" New file(case1 - No same datetime exists)")
            new_file = copy_file(target_path, dt, f, remove)
            target[dt] = {}
            target[dt][size] = [new_file]
            static["new_file"] += 1

    logger.info("")
    logger.info("Source Statistics")
    logger.info(" - Total : %d" % static["total"])
    logger.info(" - Directory : %d" % static["dir"])
    logger.info(" - Skip by file extension : %d" % static["skip"])
    logger.info(" - Duplicated files : %d" % static["dup_file"])
    logger.info(" - New files(Copied files) : %d" % static["new_file"])

    if args.index_db:
        with open(index_db, 'w') as fp:
            json.dump(target, fp)

if __name__ == "__main__":
    main()
