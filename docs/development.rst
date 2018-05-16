Development
============

This package provides a way to connect Airtable (AT) as a GUI database and DokuWiki (DW) as a content presentation system.
This is done through developing interfaces between particular AT tables and particular DW pages. A number of such interfaces
have been implemented and can be kept up to date via the top-level script of this package, i.e., ``main.py``.

Developing a new interface requires several steps described in detail in this section:

1. Understand package structure.
2. Try out default settings for a new table.
3. Define a new table class in ``wikicontents.py``.
4. Define a connection to the new class in ``wikimanager.py``.


Package structure
------------------

This image gives a schematic representation of the 3 scripts included in the package:

.. image:: dw_scheme.png


Defaults
-----------------

The first step in constructing a class for a new table is to display its content using the default formatting included
in the base Table class. For every AT table there is in principle a possibility to push it to DW (1) as a table, such as
`the tools table <http://innovationsinfundraising.org/doku.php?id=tables:tools>`_ or (2) as a set of pages, where each page
is based on information contained in a single row of the AT table. For instance, see
`this page <http://innovationsinfundraising.org/doku.php?id=tools:contingent_match>`_
based on one of the rows in the tools table.

When pushing a new table to DW the default settings will simply put all the information contained in the table in either
the table or a pages format. The former will be published on `IIF tables:test page <http://innovationsinfundraising.org/doku.php?id=tables:test>`_
while the latter on `IIF test:test_page page <http://innovationsinfundraising.org/doku.php?id=test:test_page>`_. Once these test pages are published,
one can see the default formatting and try to understand how it can be improved to achieve a desired look.

As an example, let's imagine we wanted to publish a Theories table as a table and a set of pages, where each page describes
a single theory. We need to run the following::

    python3 main.py official Theories create both

Now, if we go to the 'tables:test' link mentioned above we will see something like the following:

.. image:: test_table1.png

The information that is placed in the table is not ordered, formatted or interpreted by default. This is because the
table content returned by Airtable API is a list of dictionaries, one dictionary per table row, where dictionary keys
are column names and dictionary values are whatever is stored in that row in those columns. If for a given row some
column in the table is empty, it is not fetched by the API. Furthermore, if a row contains linked records (records that
link to other tables), what is returned is their ids and we need a separate operation to fetch whatever information we
require from those records.

The same principle holds for a default page. It will print a given row as a set of lines in which column names written
in uppercase alternate with the content of those columns. Such as this:

.. image:: test_page1.png


Defining a new class
---------------------

In order to create a meaningful presentation of information contained in the AT table, one needs to define a new class
specific for that table in the ``wikicontents.py`` file. Specifically:

1. ``def __init__()`` function for initializing the table with its basic properties

    * ``self.airtable`` creates a connection to the require table in the AT database
    * ``self.records`` fetches all the records
    * ``self.dw_table_page`` defines the location of the table (formatted as a table) on DW
    * ``self.included_in`` defines where the table is actually shown on DW (this is mostly for record-keeping)
    * ``self.main_column`` defines the first column to be displayed - the record is not displayed if information in that column is missing
    * ``self.header`` defines the table header
    * ``self.linked_pages`` specifies whether the AT table is to be presented also as a set of pages
    * ``self.dw_page_template`` if the former condition is true here we define the template for those pages (more below)
    * ``self.dw_page_name_column`` defines which column is used to create a page name on DW (and its location)
    * ``self.root_namespace`` defines in which namespace the page is included

2. ``def construct_row(self, record)`` function for specifying what a single row of the table should look like

3. ``def create_page(self, record)`` function for specifying what a single page based on the table should look like (this works in conjunction with the page template specified in the ``__init__`` function)


For defining the format of the table and a set of pages it is best to copy-paste one of the classes already defined
and adjust from there, adopting an iterative approach. Some general tips, however, are included below.

First of all, it is important to understand how content is stored in the AT table and how it gets fetched by
the AT API. Namely, all records are stored in a list of records. Every record in that list is a dictionary with 3 keys:
'id', 'fields' and 'createdTime'. The row information is stored in the 'fields' dictionary which is also a dictionary
with keys that correspond to column names.

Therefore, assuming we have initialized the Theories table and stored it in a variable 'table', in order to get the
content of, for instance, the 'Theory' column of the first row that got fetched, we would need to execute the
following command::

    theory_name = table.records[0]['fields']['Theory']
    print(theory_name)

The type of the entity that comes out of such a call depends on the column type in the AT table. For instance, short and
long text will be a string, multiple select -- a list of strings while linked records -- a list of ids for records in a
linked table. Depending on this and the desired look, a different processing will have to be adopted to convert AT content
into a printed out DW content.


Defining table format
^^^^^^^^^^^^^^^^^^^^^^^

A function for this is composed of three basic steps:

1. Get all the required row values

    * if content comes as a string, take it as is
    * if content comes as a list, join it into a string
    * if content comes as a list of linked record ids, fetch required information from a linked table (using the ids)
    * if a given table cell should contain links to other tables or pages, build those links (note: if information that is used to construct a page address contains punctuation marks, they need to be removed)

2. Concatenate all row values into a single string with column separators " | "

3. Return row


Defining page format
^^^^^^^^^^^^^^^^^^^^^^^

A function to create a page is composed of similar steps as the one for creating a table:

1. Get all the required row values

2. Insert row values into their assigned positions in the page template:

    * the template contains text that will appear on all pages constructed from a given table, e.g., section headings

    * the template also contains uppercase place-holder text that gets replaced with actual content, different for every page

3. Return page.


Adding a connection
--------------------

Once a new table class has been implemented, it needs to be added in two places in the ``wikimanager.py``:

* the name of the table should be added to the ``self.defined_tables`` list in manager initialization function

* a connection between the table name and the table class should be added as a following snipped in the ``setup_table`` function::

       elif table_name == 'NAME':
            table_base = 'BASE API KEY'
            self.table = wikicontents.SOMETABLE(self.wiki, table_base, table_name, self.user_key)
            self.used_table_name = table_name

where NAME is the name of the table in the AT database, BASE API KEY is the API key for the base in which that table is contained
and SOMETABLE is the name of the newly defined class.
