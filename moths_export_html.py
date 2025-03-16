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
from urllib.parse import urljoin, urlsplit, urlunsplit
from pathlib import Path
import mysql.connector
from mysql.connector import Error
from jinja2 import Environment, FileSystemLoader, select_autoescape

import moths_common

# The default base URL that exported pages should follow-on from,
# MUST END WITH A /
BASE_URL_DEFAULT = 'https://www.meades.org/moths/'

# The default name to display on the exported pages for the web-site 
SITE_NAME_DEFAULT = 'Meades Family'

# Moth trapping name prefix
TRAPPING_NAME_PREFIX = 'moths_'

# The index file name for all of the moth pages on the web-site, assumed
# to be at BASE_URL_DEFAULT; do NOT include the '.html' extension
MOTH_INDEX_FILE_NAME = 'moths'

# The offset that is added to the ID of an instance when creating the
# image file name for that instance to ensure that there is no clash
# in names with the image files previously created by hand on the
# web site
IMAGE_FILE_NAME_INDEX_OFFSET = 100

# Array to convert a small integer to a word
INT_TO_WORD = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
               'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
               'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
               'nineteen','twenty', 'twenty-one', 'twenty-two', 'twenty-three',
               'twenty-four', 'twenty-five', 'twenty-six', 'twenty-seven'
               'twnenty-eight', 'twenty-nine', 'thirty']

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
    last_published_file_path = None
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
        pattern = re.compile(f'<a\\s+(?:[^>]*?\\s+)?href=\\s*"({TRAPPING_NAME_PREFIX}\\d\\d-\\d\\d-\\d\\d/)"')
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
            last_published_file_path = files[len(files) - 1]
            print((f"{moths_common.PREFIX}latest trapping page at '{base_url}' is"
                   f" '{last_published_file_path[len(base_url):]}'."))
        else:
            if verbose:
                print((f"{moths_common.PREFIX} found no directories macthing the pattern"
                       f" '{TRAPPING_NAME_PREFIX}DD-MM-YY'."))
    else:
        print((f"{moths_common.PREFIX}ERROR: failed to retrieve page ({response.status_code})."))

    return last_published_file_path

def url_copy_local(base_dir, base_url, url, verbose=False):
    """
    Fetch a url to a local file, returning the file path.
    """
    file_path = None
    local_file_path = os.path.join(base_dir, url[len(base_url):])
    if verbose:
        print((f"{moths_common.PREFIX}fetching '{url}' to '{local_file_path}'."))
        
    response = requests.get(url)
    if response.status_code == 200:
        file_path = Path(local_file_path)
        # Make sure the directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open(mode='wb') as file:
            file.write(response.content)
    else:
        print((f"{moths_common.PREFIX}ERROR: failed to retrieve '{url}' ({response.status_code})."))
    return file_path

def trappings_db_get_data(base_url, date_from, db_config, verbose=False):
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
                # Next, a query to obtain the moths for the instances in each
                # trapping that have an image attached or a count > 0
                query = f"""
                SELECT DISTINCT
                  {moths_common.TABLE_NAME_MOTH}.id AS moth_id,
                  {moths_common.TABLE_NAME_MOTH}.common_name,
                  {moths_common.TABLE_NAME_MOTH}.scientific_name,
                  {moths_common.TABLE_NAME_MOTH}.html_name,
                  {moths_common.TABLE_NAME_MOTH}.html_best_instance_id,
                  {moths_common.TABLE_NAME_MOTH}.html_best_url,
                  {moths_common.TABLE_NAME_TRAPPING}.date -- required in order to use a DISTINCT SELECT
                FROM {moths_common.TABLE_NAME_INSTANCE}
                JOIN {moths_common.TABLE_NAME_TRAPPING} ON {moths_common.TABLE_NAME_INSTANCE}.trapping_id = {moths_common.TABLE_NAME_TRAPPING}.id
                JOIN {moths_common.TABLE_NAME_MOTH} ON {moths_common.TABLE_NAME_INSTANCE}.moth_id = {moths_common.TABLE_NAME_MOTH}.id
                WHERE {moths_common.TABLE_NAME_TRAPPING}.date = %s AND
                      (({moths_common.TABLE_NAME_INSTANCE}.html_use_image AND {moths_common.TABLE_NAME_INSTANCE}.image IS NOT NULL) OR {moths_common.TABLE_NAME_INSTANCE}.count > 0)
                """
                cursor.execute(query, (trapping['date'],))
                # Fetch the result
                trapping['moth_list'] = cursor.fetchall()

                # Now, for each moth, fetch the instances
                # that have an image attached or a count > 0
                instance_count = 0
                for moth in trapping['moth_list']:
                    query = f"""
                    SELECT
                      {moths_common.TABLE_NAME_INSTANCE}.id AS instance_id,
                      {moths_common.TABLE_NAME_INSTANCE}.count,
                      {moths_common.TABLE_NAME_INSTANCE}.variant,
                      {moths_common.TABLE_NAME_INSTANCE}.image,
                      {moths_common.TABLE_NAME_INSTANCE}.html_use_image,
                      {moths_common.TABLE_NAME_INSTANCE}.html_description
                    FROM {moths_common.TABLE_NAME_INSTANCE}
                    JOIN {moths_common.TABLE_NAME_TRAPPING} ON {moths_common.TABLE_NAME_INSTANCE}.trapping_id = {moths_common.TABLE_NAME_TRAPPING}.id
                    JOIN {moths_common.TABLE_NAME_MOTH} ON {moths_common.TABLE_NAME_INSTANCE}.moth_id = {moths_common.TABLE_NAME_MOTH}.id
                    WHERE {moths_common.TABLE_NAME_TRAPPING}.date = %s AND {moths_common.TABLE_NAME_INSTANCE}.moth_id = %s AND
                          (({moths_common.TABLE_NAME_INSTANCE}.html_use_image AND {moths_common.TABLE_NAME_INSTANCE}.image IS NOT NULL) OR {moths_common.TABLE_NAME_INSTANCE}.count > 0)
                    """
                    cursor.execute(query, (trapping['date'], moth['moth_id']))
                    # Fetch the result
                    instance_list = cursor.fetchall()
                    # Go through the list, totalling up the counts to add
                    # that at the top level, and adding the instances that
                    # have an image attached to that moth's image list
                    moth['image_list'] = []
                    count = 0
                    for instance in instance_list:
                        count += instance['count']
                        if instance['image'] and instance['html_use_image']:
                            moth['image_list'].append(instance)
                        instance_count += 1
                    moth['count'] = count

                if verbose:
                    print(f"{moths_common.PREFIX}trapping on {trapping['date'].strftime('%Y-%m-%d')}"
                          f" had {instance_count} instance(s), {len(trapping['moth_list'])} type(s) of moth.")
                for instance in trapping['moth_list']:
                    # If 'html_name' is empty, generate a name from 'common_name'
                    if not instance['html_name']:
                        instance['html_name'] = instance['common_name'].replace(' ', '_')
                    # Finally, for moths we have photographed before, populate a 'html_previous_image'
                    # field for each instance in the returned dictionary.
                    # In cases where there is a 'html_best_url' it will be that, otherwise
                    # if 'html_best_instance_id' has been populated we can work out what the
                    # 'html_best_url' would be from that, in the form
                    # 'base_url + moths_DD-MM-YY/moths_DD-MM-YY.html#html_name'.
                    # Alternatively, if the 'trapping_id' for the 'html_best_instance_id'
                    # is this 'trapping_id' then there _is_ no previous photo, this is our first.
                    if instance['html_best_url']:
                        instance['html_previous_image'] = '../' + instance['html_best_url']
                    else:
                        if instance['html_best_instance_id']:
                            if verbose:
                                print((f"{moths_common.PREFIX}moth ID {instance['moth_id']}"
                                       f" ('{instance['common_name']}') does not have a 'html_best_url',"
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
                                        instance['html_previous_image'] = urljoin('../', prefix_str + '/' + \
                                                                                  prefix_str + '.html#' + \
                                                                                  best_url_computed[0]['html_name']) 
                                        if verbose:
                                            print(f"{moths_common.PREFIX}\"best url\" for moth ID {instance['moth_id']}"
                                                  f" ('{instance['common_name']}') is '{instance['html_best_url_computed']}').")
                                    else:
                                        if verbose:
                                            print((f"{moths_common.PREFIX}moth ID {instance['moth_id']}"
                                                   f" ('{instance['common_name']}') does not need a 'html_previous_image';"
                                                    " it is the first of its kind."))
                                else:
                                    success = False
                                    print((f"{moths_common.PREFIX}ERROR, could not compute 'html_best_url' for"
                                           f" moth ID {instance['moth_id']} ('{instance['common_name']}') since the"
                                           f" best instance ID pointed-to ({instance['html_best_instance_id']}) either"
                                            " has no image or has 'html_use_image' set to False or has no 'html_name'."))
                            else:
                                success = False
                                print((f"{moths_common.PREFIX}ERROR, could find not find 'html_best_instance_id'"
                                       f" ({instance['html_best_instance_id']}) for moth ID {instance['moth_id']}"
                                       f" ('{instance['common_name']}'), or found more than one."))
                        else:
                            success = False
                            print((f"{moths_common.PREFIX}ERROR, moth ID {instance['moth_id']}"
                                   f" ('{instance['common_name']}') does not have a 'html_best_url'"
                                    " or a 'html_best_instance_id'."))
            if success:
                # Sort the list with entries that have no 'html_previous_image'
                # (i.e. new ones) at the top, and then in descending order of 'count'
                trapping['moth_list'].sort(key=lambda x: ('html_previous_image' in x, -x['count']))
            else:
                trapping_list = []
    except Error as e:
        print(f"{moths_common.PREFIX}ERROR retrieving data: {e}.")
    return trapping_list

def trappings_publish(base_dir, base_url, site_name, last_published_file_path,
                      trapping_list, jinja2_env, verbose=False):
    """
    Publish trapping_list as HTML pages and modify last_published_file_path to include
    the new trappings in the navigation list, returning the number of pages created.
    """

    # Load the template HTML file
    template = jinja2_env.get_template('moths.html')

    # A context to carry all the variables that are required by the template HTML file
    context = {}

    # Populate the static members of the context
    context['url_base_moths'] = base_url
    context['name_prefix'] = TRAPPING_NAME_PREFIX
    context['moth_index_file_name'] = MOTH_INDEX_FILE_NAME
    # The path to the site index URL, used in the link back to "home" at the bottom of the
    # HTML page, is assumed to be at the root of the base URL, file 'index.html', and
    # is a relative path
    split_url = urlsplit(base_url)
    dot_dot_count = split_url.path.count('/')
    context['url_site_index'] = ''
    for x in range(dot_dot_count):
        context['url_site_index'] += '../'
    context['url_site_index'] += 'index.html'
    context['site_name'] = site_name
    file_path_previous = last_published_file_path
    # The date of the previous trapping from the web-site
    date_previous = date_from_path(str(file_path_previous))
    # Run through the list populating the other context variables and writing the files
    for trapping in trapping_list:
        date_this_dmy = trapping['date'].strftime('%d-%m-%y') # 01-06-25
        date_this_long = trapping['date'].strftime('%e %B %Y').strip() # 1 June 2025

        # Update the "Forward to" section of the last published file path to point
        # to this one
        if file_path_previous:
            with open(str(file_path_previous), 'r') as file:
                file_contents = file.read()
            name = TRAPPING_NAME_PREFIX + date_this_dmy
            forward_to = f"Forward to <a href=\"{'../' + name + '/' + name + '.html'}\">{date_this_long}</a> moth page, b"
            # This regex looks for "<i> Back to <a href="*">*</a> moth page" and changes
            # it to "<i> Forward to <a href="blah">blah</a> moth page, back to...".
            # In implementation terms, it replaces the 'B' with the value of 'forward_to'.
            file_contents = re.sub('(<i>\\s*)B(ack to <a\\s+href=\\s*"[^"]+"\\s*>[^<]+</a> moth page)',
                                   f'\\1{forward_to}\\2',
                                   file_contents, count=1, flags=re.MULTILINE)
            with open(file_path_previous, 'w') as file:
                file.write(file_contents)

        # The name of both the directory and the file for this trapping: moths_DD-MM-YY
        file_and_dir_name = f"{TRAPPING_NAME_PREFIX}{trapping['date'].strftime('%d-%m-%y')}"
        dir = os.path.join(base_dir, file_and_dir_name)
        file_path = Path(os.path.join(dir, file_and_dir_name) + '.html')
        # Make sure the directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Populate the trapping-specific context variables
        context['date_this_long'] = date_this_long
        context['date_previous_dmy'] = date_previous.strftime('%d-%m-%y') # 01-06-25
        context['date_previous_long'] = date_previous.strftime('%e %B %Y').strip() # 1 June 2025
        context['description_trapping'] = trapping['description']
        context['bullet_list'] = []
        context['reference_list'] = []
        context['image_list'] = []
        bullet_list = []
        for instance in trapping['moth_list']:
            object = {}
            object['common_name'] = instance['common_name']
            object['html_name'] = instance['html_name']
            object['count'] = instance['count']
            if object['count'] < len(INT_TO_WORD):
                object['count_word'] = INT_TO_WORD[instance['count']]
            else:
                object['count_word'] = 'lots of'
            if 'html_previous_image' in instance:
                object['previous_image'] = instance['html_previous_image']
            if len(instance['image_list']) > 0:
                for image in instance['image_list']:
                    # Have an image: make a unique name for it, write the
                    # file and add it to the 'image_list' of the context
                    image_file_name = instance['html_name'].lower() + '_' + str(image['instance_id'] + IMAGE_FILE_NAME_INDEX_OFFSET) + '.jpg'
                    with open(os.path.join(base_dir, file_and_dir_name, image_file_name), 'wb') as file:
                        file.write(image['image'])
                    object['file_name'] = image_file_name
                    object['description'] = image['html_description']
                    object['image'] = image_file_name
                    object['label'] = False
                    if object['html_name'] not in bullet_list:
                        object['label'] = True
                        context['bullet_list'].append(object.copy())
                        # Update the bullet list
                        bullet_list.append(object['html_name'])
                    context['image_list'].append(object.copy())
            else:
                # Either don't have an image or don't want to use it,
                # add it to the 'reference_list' of the context
                context['reference_list'].append(object.copy())

        # Write the rendered HTML file
        with open(file_path, 'w') as file:
            file.write(template.render(context))
        print(f"{moths_common.PREFIX}CREATED new directory '{dir}' and populated it with all"
              f" of the files for the trapping on {trapping['date'].strftime('%Y-%m-%d')}.")

        # Update the previous date and the previous file path
        # to be this one
        date_previous = trapping['date']
        file_path_previous = file_path

    return len(trapping_list)

def export_html(base_dir, base_url, site_name, db_config, jinja2_env, verbose=False):
    """
    Export HTML pages from the moth database in a form that can be
    copied to base_url and should "just work" (TM) with any pages
    already there.
    """
    trappings_published = 0

    # Check out the directories off base_url to determine the last trapping date
    # already published there
    last_published = url_trapping_latest(base_url, verbose)
    if last_published:
        # Fetch the last published trapping page to a local directory of the same
        # name so that we can modify it
        last_published_file_path = url_copy_local(base_dir, base_url, last_published, verbose)
        if last_published_file_path:
            # Get the date from the file path
            last_published_date = date_from_path(str(last_published_file_path))
            # Get a list of trappings from the database that are later than this date,
            # each of which contains a dictionary of the fields that we need to
            # make the HTML page
            trapping_list = trappings_db_get_data(base_url, last_published_date, db_config, verbose)
            if len(trapping_list) > 0:
                # Create the HTML files for each trapping and modify the
                # last published file to include them in the navigation sequence
                trappings_published = trappings_publish(base_dir, base_url, site_name,
                                                        last_published_file_path, trapping_list,
                                                        jinja2_env, verbose)
                if trappings_published > 0:
                    print(f"{moths_common.PREFIX}finished.")
                    print(f"{moths_common.PREFIX}please FTP the newly create HTML folder(s),"
                          f" plus the updated file {str(last_published_file_path)}"
                          f" (i.e. everything from {base_dir} if it was empty beforehand),"
                          f" to {base_url[:-1]} and your published moth data will be up to date.")
                    print(f"{moths_common.PREFIX}you may modify the copies of these HTML files,"
                           " they will not be modified by this program in future runs once uploaded.")

    return trappings_published

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
    parser.add_argument('-n', default=SITE_NAME_DEFAULT, help=("the name to display for the web-site,"
                                                               " default '" + SITE_NAME_DEFAULT + "'."))
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

    # The Jinja2 environment
    jinja2_env = Environment (
        loader = FileSystemLoader("templates"),
        autoescape = select_autoescape()
    )

    # Return 0 on success (i.e. something was exported), else 1
    sys.exit(not (export_html(args.base_dir, args.u, args.n, db_config, jinja2_env, args.v) >= 0))