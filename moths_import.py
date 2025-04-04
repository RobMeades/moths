#!/usr/bin/env python

# Copyright 2025 Rob Meades
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import argparse
from datetime import datetime
import mysql.connector
from mysql.connector import Error

import moths_common

# The default maximum size for an image (use 0 for no limit)
IMAGE_SIZE_MAX_DEFAULT = (1024 * 1024)

def ensure_trapping(db_config, date, verbose=False):
    """
    Add a row to the trapping table in the database, if a row with
    that date does not already exist, returning the ID of the row
    or negative error code.
    """
    return_value = -1
    try:
        if verbose:
            print(f"{moths_common.PREFIX}updating table {moths_common.TABLE_NAME_TRAPPING}...")
        with moths_common.DatabaseConnection(**db_config) as connection:
            cursor = connection.cursor()
            date_str = date.strftime('%Y-%m-%d')

            # SQL query to insert data if not already present
            query = f"""
            INSERT INTO {moths_common.TABLE_NAME_TRAPPING} (date)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE date = date  -- Dummy update
            """
            cursor.execute(query, (date_str,))

            # Commit the transaction
            connection.commit()

           # Retrieve the ID of the existing or newly inserted row
            cursor.execute(f"SELECT id FROM {moths_common.TABLE_NAME_TRAPPING} WHERE date = %s", (date_str,))
            result = cursor.fetchone()
            if result:
                return_value = result[0]
                print((f"{moths_common.PREFIX}trapping ID {return_value} in"
                       f" {moths_common.TABLE_NAME_TRAPPING} table with date {date_str}."))
            else:
                print((f"{moths_common.PREFIX}ERROR: no row found in {moths_common.TABLE_NAME_TRAPPING}"
                        " table after insert."))
    except Error as e:
        print(f"{moths_common.PREFIX}ERROR inserting data: {e}.")
    return return_value

def add_instance_list(db_config, trapping_id, file_list, verbose=False):
    """
    Add rows to the instance table in the database,
    returning the number of rows added or negative error code.
    """

    # file_list is expected to be a list of objects containing the
    # component parts of each image file name (the file_path, n, m and blah),
    # sorted in blah order

    return_value = -1
    try:
        if verbose:
            print(f"{moths_common.PREFIX}updating table {moths_common.TABLE_NAME_INSTANCE}...")
        with moths_common.DatabaseConnection(**db_config) as connection:
            cursor = connection.cursor()
            return_value = 0
            moth_count = 0
            blah_previous = ''
            for file in file_list:
                # Get the count
                count = file['n']
                if file['blah'] == blah_previous:
                    # If the prefix is the same as the previous
                    # file we must be in a case where m is present,
                    # i.e. this is an additional image of the same moth,
                    # so ignore the count this time
                    count = 0
                blah_previous = file['blah']
                # Read the image file as binary data
                with open(file['file_path'], 'rb') as image_file:
                    image_data = image_file.read()

                # SQL query to insert data
                query = f"""
                INSERT INTO {moths_common.TABLE_NAME_INSTANCE} (count, image, trapping_id)
                VALUES (%s, %s, %s)
                """
                cursor.execute(query, (str(count), image_data, trapping_id))

                # Commit the transaction
                connection.commit()
                print((f"{moths_common.PREFIX}  added {file['file_path']} as entry ID"
                       f" {cursor.lastrowid} into {moths_common.TABLE_NAME_INSTANCE} table."))
                moth_count += count
                return_value += 1
            print((f"{moths_common.PREFIX}{return_value} picture(s) added, representing"
                   f" {moth_count} moth(s)."))
    except Error as e:
        print((f"{moths_common.PREFIX}ERROR inserting data: '{e}', only {return_value}"
               f" of {len(file_list)} image(s) written."))
    return return_value

def date_get(date_str):
    """
    Check if a string is a valid date in the format YYYY-MM-DD.
    """
    try:
        # Attempt to parse the string into a datetime object
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None

def process_directory(base_dir, db_config, file_size_max=0, update_db=True, verbose=False):
    """
    Iterate over sub-directories (each named with a date)
    """
    return_value = 0
    print(f"{moths_common.PREFIX}searching directory '{base_dir}'.")
    for date_dir in os.listdir(base_dir):
        date_path = os.path.join(base_dir, date_dir)

        # Ensure it is a directory named in the form YYYY-MM-DD
        date = date_get(date_dir)
        if date is not None and os.path.isdir(date_path):
            print(f"{moths_common.PREFIX}processing sub-directory '{date_dir}'...")
            # Iterate over the JPG files in the directory, making a list
            files_in_error = 0
            file_list = []
            for file_name in os.listdir(date_path):
                if file_name.lower().endswith('.jpg'):
                    file_list_entry = {}
                    file_list_entry['file_path'] = os.path.join(date_path, file_name)
                    # The file name should either be blah_n.jpg, where n
                    # is an integer, or blah_n_m.jpg, where m is 'a', 'b', etc.
                    # Split the filename at underscores and work backwards along it
                    file_name_no_ext = file_name[:-4]
                    file_name_parts = file_name_no_ext.split('_')
                    len_prefix = len(file_name_no_ext);
                    for text in reversed(file_name_parts):
                        # First time around we either have m or n,
                        # second time around we can only have n
                        try:
                            file_list_entry['n'] = int(text)
                            # If we can convert it to an integer, we're done,
                            # we have our n
                            len_prefix -= len(text) + 1 # +1 for the underscore
                            break;
                        except ValueError:
                            # It wasn't an integer (i.e. an n) so see if it is
                            # a single letter, an m
                            if 'm' not in file_list_entry and len(text) == 1 and text.isalpha():
                                file_list_entry['m'] = text.lower()
                                len_prefix -= len(text) + 1 # +1 for the underscore
                            else:
                                # Don't understand the format of this file name
                                break;
                    if 'n' in file_list_entry:
                        file_list_entry['blah'] = file_name_no_ext[:len_prefix]
                        file_list.append(file_list_entry)
                    else:
                        print((f"{moths_common.PREFIX}ERROR: '{file_name}' does not include a count, maybe"
                                " it is not of the form blah_n.jpg or blah_n_m.jpg?"))
                        files_in_error += 1
            if files_in_error == 0:
                if len(file_list) > 0:
                    # Now have a list of the component parts of each image file name:
                    # the file_path, n, m and blah; sort the list in order of blah
                    file_list.sort(key=lambda x: x['blah'])
                    # A final name check: run through this list and check that, where we have
                    # a name of the form blah_n_m.jpg, for any given blah the n's match,
                    # since we will treat only the first n of each to avoid double-counting
                    n = -1
                    blah = ''
                    for file in file_list:
                        if 'm' in file:
                            if blah == file['blah']:
                                if file['n'] is not n:
                                    print((f"{moths_common.PREFIX}ERROR: inconsistent value for 'n' ("
                                           f"'{blah}_{file['n']}_{file['m']}.jpg' after '{blah}_{n}_{file['m']}.jpg'),"
                                            " ignoring this directory."))
                                    files_in_error += 1
                                    break;
                            else:
                                # A new instance of blah, capture n
                                n = file['n']
                            blah = file['blah']
                    if files_in_error == 0 and file_size_max > 0:
                        # Before we commit to the import, check the sizes of each of the files
                        for file in file_list:
                            if os.path.getsize(file['file_path']) > file_size_max:
                                print(f"{moths_common.PREFIX}ERROR: image '{file['file_path']}' is larger"
                                      f" than the limit that has been set ({file_size_max}); use"
                                       " the -s option to set a different limit if necessary.")
                                files_in_error += 1
                    if files_in_error == 0:
                        # Make sure there is a row in the trapping table of the database for this date
                        if update_db:
                            return_value = ensure_trapping(db_config, date, verbose)
                        else:
                            print((f"{moths_common.PREFIX}would have made sure that date '{date.strftime('%Y-%m-%d')}'"
                                   f" exists in the {moths_common.TABLE_NAME_TRAPPING} table."))
                        if return_value >= 0:
                            if update_db:
                                # Add the images to the instance table in the database
                                return_value = add_instance_list(db_config, return_value, file_list, verbose)
                            else:
                                print(f"{moths_common.PREFIX}would have added {len(file_list)} picture(s) to the instance table:")
                                for file in file_list:
                                    print(f"{moths_common.PREFIX}  {file['file_path']}: n={file['n']}", end='')
                                    if 'm' in file:
                                        print(f", m={file['m']}", end='')
                                    print('')
                            return_value = len(file_list)
                else:
                    if verbose:
                        print(f"{moths_common.PREFIX}warning: sub-directory '{date_dir}' contains no image files, ignoring.")
            else:
                print(f"{moths_common.PREFIX}ERROR: sub-directory '{date_dir}' contains non-conformant .jpg files.")
        else:
            if verbose:
                print(f"{moths_common.PREFIX}ignoring sub-directory '{date_dir}', likely because it is not of the form YYYY-MM-DD.")
    return return_value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=("A script to import moth data into a database."
                                                  " It will search from this directory (or the"
                                                  " directory specified on the command-line) for"
                                                  " directories named YYYY-MM-DD (e.g. 2025-03-21"
                                                  " for 21st Match 2025) and will assume that the"
                                                  " contents of such directories are pictures of"
                                                  " moths trapped the previous night.\n\n"
                                                  "The naming convention for the image files is"
                                                  " xxxx_n_m.jpg where xxxx is any prefix string,"
                                                  " n is an integer count of the number of moths"
                                                  " of the type in the image that were caught on"
                                                  " that night and m is an alpha (a, b, c, etc.)"
                                                  " that should be present if there is more"
                                                  " then one picture of that moth type in the set."
                                                  " For instance, you might have:\n\n"
                                                  "2025-06-15 --- IMG_2567_1.jpg\n"
                                                  "            |- IMG_2568_3.jpg\n"
                                                  "            |- IMG_2570_1_a.jpg\n"
                                                  "            |- IMG_2570_1_b.jpg\n"),
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('base_dir', nargs='?', default=moths_common.BASE_DIR_DEFAULT, help=("directory to search from,"
                                                                                            " default '" +
                                                                                            moths_common.BASE_DIR_DEFAULT + "'."))
    parser.add_argument('-a', default=moths_common.MYSQL_HOST_NAME_DEFAULT, help=(f"the address where the MySQL server containing"
                                                                                   " the database can be found, default '" +
                                                                                   moths_common.MYSQL_HOST_NAME_DEFAULT + "'."))
    parser.add_argument('-d', default=moths_common.DATABASE_NAME_DEFAULT, help=(f"the database name to import into,"
                                                                                 " default '" +
                                                                                 moths_common.DATABASE_NAME_DEFAULT + "'."))
    parser.add_argument('-x', default=False, action='store_true', help=("if this is specified a dry run will"
                                                                        " be performed, the database will not"
                                                                        " be updated."))
    parser.add_argument('-s', type=int, default=IMAGE_SIZE_MAX_DEFAULT, help=(f"set a maximum image size, default"
                                                                               " " + str(IMAGE_SIZE_MAX_DEFAULT) + ", specify"
                                                                               " 0 for no limit; if an image larger than"
                                                                               " this is found the entire import will be"
                                                                               " aborted."))
    parser.add_argument('-v', default=False, action='store_true', help=("verbose debug."))
    args = parser.parse_args()

    # Database configuration
    db_config = {
        'host': args.a,
        'database': args.d
    }

    # Return 0 on success (i.e. something was imported), else 1
    sys.exit(not (process_directory(args.base_dir, db_config, int(args.s), not args.x, args.v) >= 0))