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

import mysql.connector
from mysql.connector import Error
from getpass import getpass  # For secure password input

# The prefix for all debug prints
PREFIX = 'moths: '

# The default directory to search-from/export-to
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
TABLE_NAME_TRAPPING = 'trapping'

# The name of the instance table in the database
TABLE_NAME_INSTANCE = 'instance'

# The name of the moth table in the database
TABLE_NAME_MOTH = 'moth'

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
            MYSQL_USER_NAME = input(f"{PREFIX}enter your MySQL username: ")
        if MYSQL_USER_NAME is not None:
            self.db_config['user'] = MYSQL_USER_NAME
        if 'password' not in self.db_config and MYSQL_PASSWORD is None:
            MYSQL_PASSWORD = getpass(f"{PREFIX}enter your MySQL password: ")
        if MYSQL_PASSWORD is not None:
            self.db_config['password'] = MYSQL_PASSWORD
        self.connection = None

    def __enter__(self):
        try:
            # Establish the connection
            self.connection = mysql.connector.connect(**self.db_config)
            return self.connection
        except Error as e:
            print(f"{PREFIX}ERROR: could not connect to database ({e}).")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Ensure the connection is closed
        if self.connection and self.connection.is_connected():
            self.connection.close()