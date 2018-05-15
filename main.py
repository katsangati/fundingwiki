"""
This is a top-level script for managing the tables and pages on Innovations in Fundraising Wiki.
It provides command-line access to the possible operations on the wiki content using the Airtable
database.

The settings for accessing the Wiki need to be specified in the config.json file. Currently config.json contains two
Wikis that can be used: local test wiki and the official Wiki located at innovationsinfundraising.org.

In order to use the script with either of these wikis 3 things needs to be specified:
- username for the user with admin-rights that will be posting content
- password key for retrieving the wiki password from os profile (see note below)
- wiki url for the location of the wiki

Note: the script assumes that passwords to the wiki and Airtable api key are stored in the user bash profile as
environmental variables. In order to save them as such open the bash profile file and add lines like this:

export SOME_KEY="your_key"

Save the file. You can now insert SOME_KEY that specifies the wiki password in config.json. Alternatively, export
your passwords with keys specified in the config file and only edit the username and url settings.

TODO: how to install requirements
TODO: Examples and command
TODO: minimal working example for writing a new class
TODO: things need to change when i add a new table
TODO: picture a flow
TODO: instruction case: I want to run this
TODO: instruction case: I want to change format of a table/page
TODO: instruction case: I want to create a table/page
TODO: update everything
"""
import wikimanager
import argparse


def main(wiki_version, table_name, mode, resource_type):
    """Create or update wiki content.

    Args:
        wiki_version: which wiki we are trying to modify - local test or public official one
        table_name: which table on Airtable we are trying to use
        mode: do we want to create specified content or update existing content based on changed records
        resource_type: type of content we want to create or update - wiki table, wiki pages or both
    """
    manager = wikimanager.WikiManager(wiki_version)
    manager.setup_table(table_name)

    if mode == 'create':
        if resource_type == 'table':
            manager.create_table()
        elif resource_type == 'pages':
            manager.create_pages()
        elif resource_type == 'both':
            manager.create_table_pages()
        else:
            print("Resource type unrecognized. Please choose from 'table', 'pages' or 'both'.")
    elif mode == 'update':
        if resource_type == 'table':
            manager.update_table()
        elif resource_type == 'pages':
            manager.update_pages()
        elif resource_type == 'both':
            manager.update_table_pages()
        else:
            print("Resource type unrecognized. Please choose from 'table', 'pages' or 'both'.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("wiki_version", type=str, help="Specify the DW version",
                        choices=["official", "test"])
    parser.add_argument("table_name", type=str, help="Specify which table you want to use")
    parser.add_argument("mode", type=str,
                        help="Specify whether you want to create a new resource or update an existing one",
                        choices=["create", "update"])
    parser.add_argument("resource_type", type=str, help="Specify if your resource is a table or a set of pages",
                        choices=["table", "pages", "both"])
    args = parser.parse_args()
    main(args.wiki_version, args.table_name, args.mode, args.resource_type)
