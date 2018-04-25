"""
This is a top-level script for managing the tables and pages on Innovations in Fundraising Wiki.
It provides command-line access to the possible operations on the wiki content using the Airtable
database.
The settings for accessing the Wiki and the tables need to be specified
"""
import wikimanager
import argparse


def main(wiki_version, table_name, mode, resource_type):
    """
    This is the main function for creating and updating wiki content.
    :param wiki_version: which wiki we are trying to modify - local test or public official one
    :param table_name: which table on Airtable we are trying to use
    :param mode: do we want to create specified content or update existing content based on changed records
    :param resource_type: type of content we want to create or update - wiki table, wiki pages or both
    :return:
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
