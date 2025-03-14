# Introduction
This repo contains the scripts I use to help populate a MySQL database with the results of my moth trapping.

# Database Schema
The database schema [schema](schema.sql) is quite simple, essentially as below:

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

You will notice that, in [schema](schema.sql), there are additional fields, all prefixed with `html_`:  these are required to support exporting the moth data to HTML pages that integrate with pre-existing HTML pages, see the description of `moths_export_html.py` below for more information.

# Scripts
There are two Python scripts, both of which include command-line help:

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

If all of the `.jpg` files in a directory conform to the pattern, a new trapping table row is created for the given date (if it does not already exist) and instance table rows are added for each picture, linked to that trapping table row.  It is then up to the user to populate the remaining fields in these table rows, by whatever means, and link each instance row to a moth row, through the ID field, when the moth in that picture has been identified.

## `moths_export_html.py`
This script exports the data from the database into per-trapping HTML pages that are compatible with the ones previously published at https://www.meades.org/moths/moths.  These HTML pages were all originally hand-crafted but in a very specific format which allows them to be parsed by the PHP scripts that create the dynamic moth browser page here: https://www.meades.org/moths/moth_browse.php.

A page is generally structured as follows:

- a heading of the form "Moths Found on 1 April 2025",
- a sub-heading, with links, of the form "Forward to 7 April 2025 moth page, back to 22 March 2025 moth page, to general moths page", the "Forward blah" bit being absent if this is the most recent HTML page,
- a short paragraph commenting on the trapping, followed by bullets with links to the photographs on the page, with a "previously photographed" link for each one (where available), e.g.:
  >A good variety in the trap, it is July after all.  Those worth photographing included:
  > - a rather fine example of Swallow-tailed Moth (previously photographed here),
  > - the amazingly beautiful argyresthia agg., either brokeella or goedartella.
- a final paragraph listing the other moths in the trap, those either not pictured or not worth displaying a picture of 'cos it is not that interesting, but, for each one, linking to a previous picture of that moth, and including the number of that moth there were in the trapping,
- a table containing the photographs, noting that each photograph name must be unique within the set of photographs on the website since they are turned into thumbnails with the same name that are all placed in the same directory for the moth browser page,
- a standard footer.

To support this export script, there are additional fields in the [schema](schema.sql), all prefixed with `html_`, as follows:

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