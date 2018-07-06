Usage
======

1. Clone the package_ from GitHub to your chosen directory.

2. Make sure you have Python 3 installed and configured to be accessible by default or with a python3 command.

3. Install required dependence packages by running::

    pip3 install -r requirements.txt

4. Configure your user profile file:

    * the script assumes that passwords to the Wiki and the personal Airtable api key are stored in the user bash profile as environmental variables
    * in order to save them as such, open your bash profile file and add the following lines at the bottom::

        export DOKUWIKI_PASS=your_key
        export DOKUWIKI_PASS_TEST=your_key
        export AIRTABLE_API_KEY=your_key

    * your_key for the DOKUWIKI entries are the keys that you use to access the official and test wikis
    * to get your Airtable API key, follow `these instructions <https://support.airtable.com/hc/en-us/articles/219046777-How-do-I-get-my-API-key->`_

5. Configure the settings in ``config.json`` file (located in the package top folder), namely:

    * the package can push content to the official Wiki at ``innovationsinfundraising.org`` or a local version of it (if you have one set up -- instructions on how to do this go beyond the scope of this manual)
    * pushing content requires providing login information to be used to access the Wiki -- ``config.json`` is a dictionary that stores that information
    * **username** is the user login name to access the Wiki
    * **password key** is the key that refers to the key in the user profile file that stores password to access the Wiki; if you followed point 4 above, you do not need to change anything here
    * **wiki url** is the address of the Wiki; you have to change this only if the official Wiki moves or you want to set up your own local version

6. Configure the remote API setting in the Wiki configuration manager:

    * go to Admin --> Configuration Manager --> Authentication --> remoteuser
    * add your user name in the field provided

7. Run main.py with appropriate parameters (see examples below):

    * **wiki version** can be set to 'official' (the one publicly accessible) or 'test' (the local version if set up)
    * **table name** is the name of the table in the Airtable database you want to use (this needs to be exactly the same name as in Airtable, case-sensitive)
    * **mode** can be set to 'create' or 'update' depending on whether you want to create a new resource from scratch or update an existing one
    * **resource type** can be set to 'table', 'pages' or 'both' depending on whether you want to use the Airtable table to build a table, a set of Wiki pages or both

.. _package: https://github.com/kabramova/fundingwiki

The instructions above will set up the environment and allow you to create or update tables and pages based on the content stored in Airtable tables. It will only work, however, for those tables that have been already defined in the package, i.e., for which it has been defined where the content will be published and in what format. It is recommended to first become comfortable with this process before proceeding to the more complex functionalities of the package.

In order to define the format for new tables and publish them on the Wiki, please follow the Development guide.


Examples
---------

Create a Tools table from scratch and push it to the official Wiki::

    python3 main.py official Tools create table

Update a set of pages that have been previously published on the official Wiki based on the Tools table::

    python3 main.py official Tools update pages

Create a Papers table and a set of pages and push them to the local test Wiki::

    python3 main.py test papers_mass create both



Automatic updating
===================


In order to perform regular maintenance, a different script has to be run as follows::

    python3 update_all.py


This will check all the defined tables for updated records and update the table published on the Wiki, as well as
associated pages. It will also perform a within-database maintenance. Currently this is implemented only for filling in
bibliographic details in the Papers table.

The updating script is run automatically on the server every Sunday. Therefore manual maintenance is no longer required
but can be performed when needed.