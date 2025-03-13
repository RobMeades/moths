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
from getpass import getpass  # For secure password input

# The prefix for all debug prints
PROGRAM_PREFIX = 'moths: '

# The default directory to start searching from
BASE_DIR_DEFAULT = '.'

# The default name of the host where the MySQL database can be found
MYSQL_HOST_NAME_DEFAULT = '10.10.1.7'

# The MySQL user name; use None and the user will be prompted
MYSQL_USER_NAME = None

# The MySQL password; use None and the user will be prompted
MYSQL_PASSWORD = None

# The default name of the database
DATABASE_NAME_DEFAULT = 'moths'

# The name of the trapping table in the database
TABLE_TRAPPING_NAME = 'trapping'

# The name of the instance table in the database
TABLE_INSTANCE_NAME = 'instance'

class DatabaseConnection:
    """
    Custom context manager for database connection.
    """
    def __init__(self, **db_config):
        # Populate the user-name and password the first time through,
        # if not already done
        self.db_config = db_config
        global MYSQL_USER_NAME, MYSQL_PASSWORD
        if 'user' not in self.db_config and MYSQL_USER_NAME is None:
            MYSQL_USER_NAME = input(f"{PROGRAM_PREFIX}enter your MySQL username: ")
        if MYSQL_USER_NAME is not None:
            self.db_config['user'] = MYSQL_USER_NAME
        if 'password' not in self.db_config and MYSQL_PASSWORD is None:
            MYSQL_PASSWORD = getpass(f"{PROGRAM_PREFIX}enter your MySQL password: ")
        if MYSQL_PASSWORD is not None:
            self.db_config['password'] = MYSQL_PASSWORD
        self.connection = None

    def __enter__(self):
        try:
            # Establish the connection
            self.connection = mysql.connector.connect(**self.db_config)
            return self.connection
        except Error as e:
            print(f"{PROGRAM_PREFIX}database connection error: {e}.")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure the connection is closed
        if self.connection and self.connection.is_connected():
            self.connection.close()


def ensure_trapping(db_config, date, verbose=False):
    """
    Add a row to the trapping table in the database, if a row with
    that date does not already exist, returning the ID of the row
    or negative error code.
    """
    return_value = -1
    try:
        if verbose:
            print(f"{PROGRAM_PREFIX}updating table {TABLE_TRAPPING_NAME}...")
        with DatabaseConnection(**db_config) as connection:
            cursor = connection.cursor()
            date_str = date.strftime('%Y-%m-%d')

            # SQL query to insert data if not already present
            query = f"""
            INSERT INTO {TABLE_TRAPPING_NAME} (date)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE date = date  -- Dummy update
            """
            cursor.execute(query, (date_str,))

            # Commit the transaction
            connection.commit()

           # Retrieve the ID of the existing or newly inserted row
            cursor.execute(f"SELECT id FROM {TABLE_TRAPPING_NAME} WHERE date = %s", (date_str,))
            result = cursor.fetchone()
            if result:
                return_value = result[0]
                if cursor.lastrowid == 0:
                    print((f"{PROGRAM_PREFIX}{TABLE_TRAPPING_NAME} table already"
                           f" had an entry for date {date_str}, ID {return_value}."))
                else:
                    print((f"{PROGRAM_PREFIX}entry ID {return_value} added to"
                           f" {TABLE_TRAPPING_NAME} table with date {date_str}."))
            else:
                print((f"{PROGRAM_PREFIX}error: no row found in {TABLE_TRAPPING_NAME}"
                        " table after insert."))
    except Error as e:
        print(f"{PROGRAM_PREFIX}error inserting data: {e}.")
    return return_value

def add_instance_list(db_config, trapping_id, file_list, verbose=False):
    """
    Add rows to the instance table in the database,
    returning the number of rows added or negative error code.
    """

    # file_list is expected to be a list of objects containing the
    # component parts of each image file name (the file_path, n, m and blah),
    # sorted into blah order

    return_value = -1
    try:
        if verbose:
            print(f"{PROGRAM_PREFIX}updating table {TABLE_INSTANCE_NAME}...")
        with DatabaseConnection(**db_config) as connection:
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
                INSERT INTO {TABLE_INSTANCE_NAME} (count, image, trapping_id)
                VALUES (%s, %s, %s)
                """
                cursor.execute(query, (str(count), image_data, trapping_id))

                # Commit the transaction
                connection.commit()
                print((f"{PROGRAM_PREFIX}  added {file['file_path']} as entry ID"
                       f" {cursor.lastrowid} into {TABLE_INSTANCE_NAME} table."))
                moth_count += count
                return_value += 1
            print((f"{PROGRAM_PREFIX}{return_value} picture(s) added, representing"
                   f" {moth_count} moth(s)."))
    except Error as e:
        print((f"{PROGRAM_PREFIX}error inserting data: '{e}', only {return_value}"
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

def process_directory(base_dir, db_config, update_db=True, verbose=False):
    """
    Iterate over sub-directories (each named with a date)
    """
    return_value = 0
    print(f"{PROGRAM_PREFIX}searching directory '{base_dir}'.")
    for date_dir in os.listdir(base_dir):
        date_path = os.path.join(base_dir, date_dir)

        # Ensure it is a directory named in the form YYYY-MM-DD
        date = date_get(date_dir)
        if date is not None and os.path.isdir(date_path):
            print(f"{PROGRAM_PREFIX}processing sub-directory '{date_dir}'...")
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
                        print((f"{PROGRAM_PREFIX}error: '{file_name}' does not include a count, maybe"
                                " it is not of the form blah_n.jpg or blah_n_m.jpg?"))
                        files_in_error += 1
            if files_in_error == 0:
                if len(file_list) > 0:
                    # Now have a list of the component parts of each image file name:
                    # the file_path, n, m and blah; sort the list in order of blah
                    file_list.sort(key=lambda x: x['blah'])
                    # A final check: run through this list and check that, where we have
                    # a name of the form blah_n_m.jpg, for any given blah the n's match,
                    # since we will treat only the first n of each to avoid double-counting
                    n = -1
                    blah = ''
                    for file in file_list:
                        if 'm' in file:
                            if blah == file['blah']:
                                if file['n'] is not n:
                                    print((f"{PROGRAM_PREFIX}error: inconsistent value for 'n' ("
                                           f"'{blah}_{file['n']}_{file['m']}.jpg' after '{blah}_{n}_{file['m']}.jpg'),"
                                            " ignoring this directory."))
                                    files_in_error += 1
                                    break;
                            else:
                                # A new instance of blah, capture n
                                n = file['n']
                            blah = file['blah']
                    if files_in_error == 0:
                        # Make sure there is a row in the trapping table of the database for this date
                        if update_db:
                            return_value = ensure_trapping(db_config, date, verbose)
                        else:
                            print((f"{PROGRAM_PREFIX}would have made sure that date '{date.strftime('%Y-%m-%d')}'"
                                   f" exists in the {TABLE_TRAPPING_NAME} table."))
                        if return_value >= 0:
                            if update_db:
                                # Add the images to the instance table in the database
                                return_value = add_instance_list(db_config, return_value, file_list, verbose)
                            else:
                                print(f"{PROGRAM_PREFIX}would have added {len(file_list)} picture(s) to the instance table:")
                                for file in file_list:
                                    print(f"{PROGRAM_PREFIX}  {file['file_path']}: n={file['n']}", end='')
                                    if 'm' in file:
                                        print(f", m={file['m']}", end='')
                                    print('')
                else:
                    if verbose:
                        print(f"{PROGRAM_PREFIX}warning: sub-directory '{date_dir}' contains no image files, ignoring.")
            else:
                print(f"{PROGRAM_PREFIX}error: ignoring sub-directory '{date_dir}' as it contains non-conformant .jpg files.")
        else:
            if verbose:
                print(f"{PROGRAM_PREFIX}ignoring sub-directory '{date_dir}', likely because it is not of the form YYYY-MM-DD.")


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
    parser.add_argument('base_dir', nargs='?', default=BASE_DIR_DEFAULT, help=("directory to search from,"
                                                                               " default '" +
                                                                               BASE_DIR_DEFAULT + "'."))
    parser.add_argument('-a', default=MYSQL_HOST_NAME_DEFAULT, help=(f"the address where the MySQL server containing"
                                                                      " the database can be found, default '" +
                                                                      MYSQL_HOST_NAME_DEFAULT + "'."))
    parser.add_argument('-d', default=DATABASE_NAME_DEFAULT, help=(f"the database name to import into,"
                                                                    " default '" + DATABASE_NAME_DEFAULT + "'."))
    parser.add_argument('-x', default=False, action='store_true', help=("if this is specified a dry run will"
                                                                        " be performed, the database will not"
                                                                        " be updated."))
    parser.add_argument('-v', default=False, action='store_true', help=("verbose debug."))
    args = parser.parse_args()

    # Database configuration
    db_config = {
        'host': args.a,
        'database': args.d
    }

    sys.exit(process_directory(args.base_dir, db_config, not args.x, args.v))