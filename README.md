# Introduction
This repo contains the scripts I use to help populate a MySQL database with the results of our moth trapping.

# Database Schema
The database [schema](schema.sql) is quite simple, essentially as below:

```
- moths
  - tables:
    - location, fields:
      - id (UNSIGNED INT, PRIMARY KEY)
      - name (TINYTEXT)
      - latitude_longitude (POINT)
    - trapping, fields:
      - id (UNSIGNED INT, PRIMARY KEY)
      - date (DATE, UNIQUE KEY)
      - temperature_celsius (INT, average overnight temperature in Celsius)
      - description (TEXT)
      - location_id (UNSIGNED INT, link to the location table row ID for this trapping)
    - moth, fields:
      - id (UNSIGNED INT, PRIMARY KEY)
      - common_name (TINYTEXT)
      - scientific_name (TINYTEXT)
      - agg_id (UNSIGNED INT, link to an aggregate moth ID if this moth has one, e.g. Oak Beauty Agg. for Pale/Great Oak Beauty)
      - confusion_1_id (UNSIGNED INT, link to a confusion species for this moth)
      - confusion_2_id (UNSIGNED INT, link to a confusion species for this moth)
      - confusion_3_id (UNSIGNED INT, link to a confusion species for this moth)
      - confusion_4_id (UNSIGNED INT, link to a confusion species for this moth)
    - instance, fields:
      - id (UNSIGNED INT, PRIMARY KEY)
      - count (INT, the number of moths of this type caught in any one trapping)
      - variant (TINYTEXT, e.g. male/female, worn, etc.)
      - image (MEDIUMBLOB, a .jpg image)
      - trapping_id (UNSIGNED INT, link to the trapping table row ID for this instance)
      - moth_id (UNSIGNED INT, link to the moth table row ID for this instance)
```

You will notice that, in [schema.sql](schema.sql), there are additional fields, all prefixed with `html_`:  these are required to support exporting the moth data to HTML pages that integrate with pre-existing HTML pages, see the description of `moths_export_html.py` below for more information.

# Scripts
There are two main Python scripts, both of which include command-line help, plus a `moths_common.py` for some stuff that is shared between them.

## Installation
The few dependencises required to run the scripts can be installed with:

```
pip install -r requirements.txt
```

You will also need to have installed a [MySQL](https://www.mysql.com/) server somewhere and created on it a database with the [schema](schema.sql).  The machine on which you run the scripts will need to be able to log-in to that MySQL server.

You will need to install a client application on the scripting machine that allows you to edit the database; for the purposes her [HeidiSQL](https://www.heidisql.com/) is sufficient.

## Usage
The process for using the scripts is as follows:

- trap some moths and photograph those moths as you wish,
- edit the photographs as you please, so that you end up with a set that effectively catalogues the moths (see the description of `moths_import.py` below for the naming patten),
- run `moths_import.py` on those photographs: this will import the photographs into the database; note that you can do a dry-run first if you wish to check that your naming was good,
- populate the empty fields in the new `trapping` entry of the database (e.g. description, temperature, etc.) using something like [HeidiSQL](https://www.heidisql.com/),
- identify each of the moths in the database by editing the imported data to link each new `instance` to a `moth ID`; this may involve creating new `moth` entries, updating the `html_` entries for existing `moth` entries (see the description of `moths_export_html.py` for how these fields are used), deciding whether the photograph of an `instance` is one you want to display or not, etc.
- if necessary, manually add any instances where you took no photographs, linking each one up to a `moth` in the same way,
- run `moths_export_html.py` to export the new data to an `.html` page,
- open the exported `.html` page in a browser to see what it looks like, edit any data in the database as necessary to make the text/pictures as you please, re-run `moths_export_html.py`, repeating until happy,
- optionally, once you are going to export the `.html` page no more, open it in an HTML editor and make any manual changes (e.g. re-sizing or re-arranging the pictures),
- copy the new `.html` page, plus the locally modified version of the last `.html` page that was already on the web-site (which will have had its `Forward to` navigation line modified to reflect the added page) to the web-site.

Note that, once a trapping is exported and published back to the web-site, future runs of `moths_export_html.html` will not modify that page's content (except to add a `Forward to` navigation entry to the very latest one), no edits in the database to that `trapping` entry or any of the associated `instance` entries will be applied; such changes may still be made manually of course.

## `moths_import.py`
This script searches a directory for sub-directories named in the pattern `YYYY-MM-DD`, which are assumed to be the results of a trapping on the previous night.

It then looks for `.jpg` files in those directories of the form `blah_n.jpg` or `blah_n_m.jpg`, where `blah` is any prefix, `n` is a count of the number of that moth that were caught in that trapping and `m` is `a`, `b`, `c` etc. for the case where there is more than one picture of a single type of moth.  For instance, a directory might contain:

```
IMG_7843_1_a.jpg
IMG_7843_1_b.jpg
IMG_7843_1_c.jpg
IMG_7845_3_a.jpg
IMG_7845_3_b.jpg
IMG_7852_2.jpg
IMG_7854_1.jpg
```

If all of the `.jpg` files in a directory conform to the pattern, a new trapping table row is created for the given date (if it does not already exist) and instance table rows are added for each picture, linked to that trapping table row.  It is then up to the user to populate the remaining fields in these table rows, by whatever means (e.g. [HeidiSQL](https://www.heidisql.com/)), and link each instance row to a moth row, through the ID field, when the moth in that picture has been identified.

## `moths_export_html.py`
This script exports the data from the database into per-trapping HTML pages that are compatible with the ones previously published at https://www.meades.org/moths/moths.  These HTML pages were all originally hand-crafted but in a very specific format which allows them to be parsed by the PHP scripts that create the dynamic moth browser page here: https://www.meades.org/moths/moth_browse.php.

A page is generally structured as follows:

- a heading of the form "Moths Found on 1 April 2025",
- a sub-heading, with links, of the form "Forward to 7 April 2025 moth page, back to 22 March 2025 moth page, to general moths page", the "Forward blah" bit being absent if this is the most recent HTML page,
- a short paragraph commenting on the trapping, followed by bullets with links to the photographs on the page, with a "previously photographed" link for each one (where available), e.g.:

  >A good variety in the trap, it is July after all.  Those worth photographing included:
  > - a rather fine example of Swallow-tailed Moth (previously photographed here),
  > - the amazingly beautiful argyresthia agg., either brokeella or goedartella.
- a final paragraph listing the other moths in the trap, those either not pictured or not worth displaying a picture of 'cos it is not that interesting, but, for each one, linking to a previous picture of that moth, and including the number of that moth present in the trap,
- a table containing the photographs, noting that each photograph name must be unique within the set of photographs on the website since they are turned into thumbnails with the same name that are all placed in the same directory for the moth browser page,
- a standard footer.

Programmatically, such a page is created using [jinja2](https://pypi.org/project/Jinja2/); the template from which the page is generated can be found in the [templates](templates) directory.

To support this export script, there are additional fields in [schema.sql](schema.sql), all prefixed with `html_`, as follows:

```
- moths
  - tables:
    - moth, fields:
      - html_name (TINYTEXT, the name used for this moth on https://www.meades.org)
      - html_instance_best_id (UNSIGNED INT, a link to the instance ID that best represents this moth, may be empty)
      - html_instance_best_url (TINYTEXT, a URL, from the existing https://www.meades.org, that best represents this moth, must be populated if html_instance_best_id is empty)
    - instance, fields:
      - html_use_image (TINYINT, true if the image in this instance is worth displaying on an exported HTML page)
      - html_description (TINYTEXT, a short description that will be used as the bullet-point text when this is exported to HTML)
```