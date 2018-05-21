"""
This is a top-level script for maintaining all the tables and pages on Innovations in Fundraising Wiki.
"""
import wikimanager


def main():
    manager = wikimanager.WikiManager("official")
    defined_tables = manager.defined_tables

    for table in defined_tables:
        manager.setup_table(table)
        manager.update_table_pages()


if __name__ == '__main__':
    main()
