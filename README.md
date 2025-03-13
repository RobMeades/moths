# Introduction
This repo contains the scripts I use to help populate a MySQL database with the results of my moth trapping.

# Database Schema
The database schema [schema](schema.sql) is quite simple:

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

If all of the `.jpg` files in a directory conform to the pattern, a new trapping table row is created for the given date (if it does not already exist) and instance table rows are added for each picture, linked to that trapping row.  It is then up to the user to populate the remaining fields in these table rows, by whatever means, and link each instance row to a moth row, through the ID field, when the moth in that picture has been identified.

## `moths_export_html.py`
TODO