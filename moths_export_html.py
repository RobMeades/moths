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
import requests
import re
from urllib.parse import urljoin
from pathlib import Path
import mysql.connector
from mysql.connector import Error

import moths_common

# The default base URL that exported pages should follow-on from,
# MUST END WITH A /
BASE_URL_DEFAULT = 'https://www.meades.org/moths/'

# Moth trapping name prefix
TRAPPING_NAME_PREFIX = 'moths_'

def date_from_path(path):
    """
    Function to get a date/time from a string that ends with "dd-mm-yy.html"
    """
    # The negative numbers here are meant to get "30-05-24" from "blah_30-05-24.html"
    return datetime.strptime(path[-8-5:-5], '%d-%m-%y')

def url_trapping_latest(base_url, verbose=False):
    """
    Check base_url to find all of the moth trappings at it
    and return the URL of the latest one.  Directories
    containing trappings are assumed to be named as moths_DD-MM-YY
    and contain a HTML page of the same name.
    """
    return_value = None
    if verbose:
        print((f"{moths_common.PREFIX}searching '{base_url}' for directories"
               f" of the pattern '{TRAPPING_NAME_PREFIX}DD-MM-YY/'..."))

    # Send a GET request to the URL
    response = requests.get(base_url)

    # Check if the request was successful
    if response.status_code == 200:
        # Find all the directory links of the form moths_DD-MM-YY
        # This pattern looks for <a> tags with href attributes that begin
        # with TRAPPING_NAME_PREFIX_DD-MM-YY and end with a '/', indicating
        # a directory
        pattern = re.compile(f'<a\\s+(?:[^>]*?\\s+)?href="({TRAPPING_NAME_PREFIX}\\d\\d-\\d\\d-\\d\\d/)"')
        matches = pattern.findall(response.text)        
        if verbose:
            print(f"{moths_common.PREFIX}found {len(matches)} directories:")
            for match in matches:
                print((f"{moths_common.PREFIX}  '{match}'"))
        # Construct full URLs for the directories and the HTML pages they should contain
        # ":-1" below to remove the "/" on the end of match
        files = [urljoin(base_url, match + match[:-1] + '.html') for match in matches]
        # Sort the list in order of DD-MM-YY
        files.sort(key=date_from_path)
        if len(files) > 0:
            return_value = files[len(files) - 1]
            print((f"{moths_common.PREFIX}latest trapping page at '{base_url}' is"
                   f" '{return_value[len(base_url):]}'."))
        else:
            if verbose:
                print((f"{moths_common.PREFIX} found no directories macthing the pattern"
                       f" '{TRAPPING_NAME_PREFIX}DD-MM-YY'."))
    else:
        print((f"{moths_common.PREFIX}ERROR: failed to retrieve page ({response.status_code})."))

    return return_value

def url_copy_local(url, base_url, base_dir, verbose=False):
    """
    Fetch a url to a local file, returning the file path.
    """
    return_value = None
    local_file_path = os.path.join(base_dir, url[len(base_url):])
    if verbose:
        print((f"{moths_common.PREFIX}fetching '{url}' to '{local_file_path}'."))
        
    response = requests.get(url)
    if response.status_code == 200:
        file_path = Path(local_file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open(mode='wb') as file:
            file.write(response.content)
        return_value = file_path
    else:
        print((f"{moths_common.PREFIX}ERROR: failed to retrieve '{url}' ({response.status_code})."))
    return return_value

def trappings_db_get_data(date_from, db_config, base_url, verbose=False):
    """
    Get the data required for the HTML page for trappings that are present in the
    database after the given date, returning a dictionary of trappings, each
    of which includes a list of instances.
    """
    trapping_list = []
    try:
        with moths_common.DatabaseConnection(**db_config) as connection:
            cursor = connection.cursor()
            # This will get us back a dictionary rather than a list
            cursor = connection.cursor(dictionary=True)

            # First, a query to obtain a dictionary of trappings after the given date
            query = f"""
            SELECT
              {moths_common.TABLE_NAME_TRAPPING}.id AS trapping_id,
              {moths_common.TABLE_NAME_TRAPPING}.date,
              {moths_common.TABLE_NAME_TRAPPING}.description
            FROM {moths_common.TABLE_NAME_TRAPPING}
            WHERE {moths_common.TABLE_NAME_TRAPPING}.date > %s
            ORDER BY {moths_common.TABLE_NAME_TRAPPING}.date DESC;
            """
            cursor.execute(query, (date_from,))

            # Fetch the result
            trapping_list = cursor.fetchall()
            print(f"{moths_common.PREFIX}{len(trapping_list)} trapping(s) in database"
                  f" after {date_from.strftime('%Y-%m-%d')}.")
            success = True
            for trapping in trapping_list:
                # Next, a query to obtain the instances for each trapping
                query = f"""
                SELECT
                  {moths_common.TABLE_NAME_INSTANCE}.id AS instance_id,
                  {moths_common.TABLE_NAME_INSTANCE}.count,
                  {moths_common.TABLE_NAME_INSTANCE}.variant,
                  {moths_common.TABLE_NAME_INSTANCE}.image,
                  {moths_common.TABLE_NAME_INSTANCE}.html_use_image,
                  {moths_common.TABLE_NAME_INSTANCE}.html_description,
                  {moths_common.TABLE_NAME_MOTH}.id AS moth_id,
                  {moths_common.TABLE_NAME_MOTH}.common_name,
                  {moths_common.TABLE_NAME_MOTH}.scientific_name,
                  {moths_common.TABLE_NAME_MOTH}.html_name,
                  {moths_common.TABLE_NAME_MOTH}.html_best_instance_id,
                  {moths_common.TABLE_NAME_MOTH}.html_best_url
                FROM {moths_common.TABLE_NAME_INSTANCE}
                JOIN {moths_common.TABLE_NAME_TRAPPING} ON {moths_common.TABLE_NAME_INSTANCE}.trapping_id = {moths_common.TABLE_NAME_TRAPPING}.id
                JOIN {moths_common.TABLE_NAME_MOTH} ON {moths_common.TABLE_NAME_INSTANCE}.moth_id = {moths_common.TABLE_NAME_MOTH}.id
                WHERE {moths_common.TABLE_NAME_TRAPPING}.date = %s
                ORDER BY {moths_common.TABLE_NAME_TRAPPING}.date DESC;
                """
                cursor.execute(query, (trapping['date'],))
                # Fetch the result and add it to the dictionary
                trapping['instance_list'] = cursor.fetchall()
                if verbose:
                    print(f"{moths_common.PREFIX}trapping on {trapping['date'].strftime('%Y-%m-%d')}"
                          f" had {len(trapping['instance_list'])} instance(s).")
                for instance in trapping['instance_list']:
                    # Finally, for moths we have photographed before, populate a 'html_previous_photo'
                    # field for each instance in the returned dictionary.
                    # In cases where there is a 'html_best_url' it will be that, otherwise
                    # if 'html_best_instance_id' has been populated we can work out what the
                    # 'html_best_url' would be from that, in the form
                    # 'base_url + moths_DD-MM-YY/moths_DD-MM-YY.html#html_name'.
                    # Alternatively, if the 'trapping_id' for the 'html_best_instance_id'
                    # is this `trapping_id` then there _is_ no previous photo, this is our first.
                    if instance['html_best_url']:
                        instance['html_previous_photo'] = instance['html_best_url']
                    else:
                        if instance['html_best_instance_id']:
                            if verbose:
                                print((f"{moths_common.PREFIX}moth ID {instance['moth_id']}"
                                       f" ('{instance['common_name']}'), referred to by instance ID"
                                       f" {instance['instance_id']}, does not have a 'html_best_url',"
                                        " computing one..."))
                            # This query should return a single row combining the required instance
                            # and moth data for the instance ID that is 'html_best_instance_id'
                            query = f"""
                            SELECT
                              {moths_common.TABLE_NAME_INSTANCE}.id AS instance_id,
                              {moths_common.TABLE_NAME_INSTANCE}.trapping_id,
                              {moths_common.TABLE_NAME_INSTANCE}.image,
                              {moths_common.TABLE_NAME_INSTANCE}.html_use_image,
                              {moths_common.TABLE_NAME_MOTH}.id as moth_id,
                              {moths_common.TABLE_NAME_MOTH}.html_name
                            FROM {moths_common.TABLE_NAME_INSTANCE}
                            JOIN {moths_common.TABLE_NAME_MOTH} ON {moths_common.TABLE_NAME_INSTANCE}.moth_id = {moths_common.TABLE_NAME_MOTH}.id
                            WHERE {moths_common.TABLE_NAME_INSTANCE}.id = %s
                            """
                            cursor.execute(query, (instance['html_best_instance_id'],))
                            best_url_computed = cursor.fetchall()
                            if best_url_computed and len(best_url_computed) == 1:
                                if best_url_computed[0]['image'] and \
                                   best_url_computed[0]['html_use_image'] and \
                                   best_url_computed[0]['html_name']:
                                    if trapping['trapping_id'] != best_url_computed[0]['trapping_id']:
                                        prefix_str = TRAPPING_NAME_PREFIX + trapping['date'].strftime('%d-%m-%y')
                                        instance['html_previous_photo'] = urljoin(base_url, prefix_str + '/' + \
                                                                                  prefix_str + '.html#' + \
                                                                                  best_url_computed[0]['html_name']) 
                                        if verbose:
                                            print(f"{moths_common.PREFIX}\"best url\" for moth ID {instance['moth_id']}"
                                                  f" ('{instance['common_name']}') is '{instance['html_best_url_computed']}').")
                                    else:
                                        if verbose:
                                            print((f"{moths_common.PREFIX}moth ID {instance['moth_id']}"
                                                   f" ('{instance['common_name']}'), referred to by instance ID"
                                                   f" {instance['instance_id']}, does not need a 'html_previous_photo';"
                                                    " it is the first of its kind."))
                                else:
                                    success = False
                                    print((f"{moths_common.PREFIX}ERROR, could not compute 'html_best_url' for"
                                           f" moth ID {instance['moth_id']} ('{instance['common_name']}'), referred"
                                           f" to by instance ID {instance['instance_id']}, since the best instance"
                                           f" ID pointed-to ({instance['html_best_instance_id']}) either has no image"
                                            " or has 'html_use_image' set to False or has no 'html_name'."))
                            else:
                                success = False
                                print((f"{moths_common.PREFIX}ERROR, could find not find 'html_best_instance_id'"
                                       f" ({instance['html_best_instance_id']}) for moth ID {instance['moth_id']}"
                                       f" ('{instance['common_name']}'), referred to by instance ID {instance['instance_id']},"
                                        " or found more than one."))
                        else:
                            success = False
                            print((f"{moths_common.PREFIX}ERROR, moth ID {instance['moth_id']}"
                                   f" ('{instance['common_name']}'), referred to by instance ID"
                                   f" {instance['instance_id']}, does not have a 'html_best_url'"
                                    " or a 'html_best_instance_id'."))
            if not success:
                trapping_list = []
    except Error as e:
        print(f"{moths_common.PREFIX}ERROR retrieving data: {e}.")
    return trapping_list

def export_html(base_dir, db_config, base_url, verbose=False):
    """
    Export HTML pages from the moth database in a form that can be
    copied to base_url and should "just work" (TM) with any pages
    already there.
    """
    return_value = 0

    # Check out the directories off base_url to determine the last trapping date
    # already published there
    last_published = url_trapping_latest(base_url, verbose)
    if last_published:
        # Fetch the last published trapping page to a local directory of the same
        # name so that we can modify it
        last_published_file_path = url_copy_local(last_published, base_url, base_dir, verbose)
        if last_published_file_path:
            # Get the date from the file path
            last_published_date = date_from_path(str(last_published_file_path))
            # Get a list of trappings from the database that are later than this date,
            # each of which contains a dictionary of the fields that we need to
            # make the HTML page
            data = trappings_db_get_data(last_published_date, db_config, base_url, verbose)
            if len(data) > 0:
                # TODO
                pass

    return return_value;

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=("A script to export data from the moth database"
                                                  " into per-trapping HTML pages compatible with"
                                                  " those that can be found at https://www.meades.org/moths/."
                                                  " The pages there are assumed to be named in the"
                                                  " form moths_DD-MM-YY/moths_DD-MM-YY.html, with"
                                                  " the image files for each trapping in the directory"
                                                  " of the .html file."),
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('base_dir', nargs='?', default=moths_common.BASE_DIR_DEFAULT, help=("directory to export to,"
                                                                                            " default '" +
                                                                                            moths_common.BASE_DIR_DEFAULT +
                                                                                            "'."))
    parser.add_argument('-u', default=BASE_URL_DEFAULT, help=("the base URL of the set of web pages that the exported"
                                                              " page(s) should follow-on from, MUST END WITH A /,"
                                                              " default '" + BASE_URL_DEFAULT + "'."))
    parser.add_argument('-a', default=moths_common.MYSQL_HOST_NAME_DEFAULT, help=(f"the address where the MySQL server"
                                                                                   " containing the database can be"
                                                                                   " found, default '" +
                                                                                   moths_common.MYSQL_HOST_NAME_DEFAULT +
                                                                                   "'."))
    parser.add_argument('-d', default=moths_common.DATABASE_NAME_DEFAULT, help=(f"the database name to export from,"
                                                                                 " default '" +
                                                                                 moths_common.DATABASE_NAME_DEFAULT +
                                                                                 "'."))
    parser.add_argument('-v', default=False, action='store_true', help=("verbose debug."))
    args = parser.parse_args()

    # Database configuration
    db_config = {
        'host': args.a,
        'database': args.d
    }

    # Return 0 on success (i.e. something was exported), else 1
    sys.exit(not (export_html(args.base_dir, db_config, args.u, args.v) >= 0))