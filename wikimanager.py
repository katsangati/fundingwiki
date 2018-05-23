"""
Define the main classes for managing the DokuWiki content in connection
with Airtable, i.e. creating new pages or updating the existing ones.
"""

import os
import dokuwiki as dw
import wikicontents
import json


class WikiManager:
    """Manager class that provides short-hand access to content editing functionality.

    Attributes:
        wiki (DokuWiki): wiki object that will be used to fetch and post content
        user_key: user API key to the Airtable
        table (Table): table object that will be instantiated and used to format content
        used_table_name (str): table name in the Airtable
        defined_tables (list): a list of tables that have defined formats

    """
    def __init__(self, version):
        """Instantiate a manager for a particular wiki version.
        This sets up a connection to the wiki, fetches Airtable API key and defines which tables
        in the Airtable database have their templates defined.

        Args:
            version (str): wiki version to interface with (official or test)
        """
        with open('config.json', 'r') as f:
            config = json.load(f)
        if version not in ["official", "test"]:
            print('Unknown version specified, choose from: "official" or "test".')
            return
        else:
            self.wiki = dw.DokuWiki(config[version]["wiki_url"],
                                    config[version]["username"],
                                    os.environ[config[version]["password_key"]])
            self.user_key = os.environ['AIRTABLE_API_KEY']
            self.table = None
            self.used_table_name = None
            self.defined_tables = ['Tools', 'Giving_companies_ftse', 'Giving_companies_other', 'Charity_experiments',
                                   'Experiences', 'Third_sector', 'papers_mass', 'Categories']

    def setup_table(self, table_name):
        """Initialize the connection to a given table in Airtable.
         This is accomplished by instantiating a specific object of a Table class.

        Args:
            table_name: the name of the table in the Airtable database

        Returns:
            Table object
        """
        if table_name == 'Tools':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.ToolTable(self.wiki, table_base, table_name, self.user_key)
            self.used_table_name = table_name

        elif table_name == 'Giving_companies_ftse':
            table_base = 'apprleNrkR7dTtW60'
            self.table = wikicontents.FtseTable(self.wiki, table_base, table_name, self.user_key, 'FTSE100')
            self.used_table_name = table_name

        elif table_name == 'Giving_companies_other':
            table_base = 'apprleNrkR7dTtW60'
            self.table = wikicontents.FtseTable(self.wiki, table_base, 'Giving companies', self.user_key, 'Other')
            self.used_table_name = table_name

        elif table_name == 'Charity_experiments':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.ExperimentTable(self.wiki, table_base, table_name, self.user_key)
            self.used_table_name = table_name

        elif table_name == 'Experiences':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.ExperienceTable(self.wiki, table_base, table_name, self.user_key)
            self.used_table_name = table_name

        elif table_name == 'Third_sector':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.ThirdSectorTable(self.wiki, table_base, table_name, self.user_key)
            self.used_table_name = table_name

        elif table_name == 'papers_mass':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.PapersTable(self.wiki, table_base, table_name, self.user_key)
            self.used_table_name = table_name

        elif table_name == 'Categories':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.CategoryTable(self.wiki, table_base, table_name, self.user_key)
            self.used_table_name = table_name

        else:
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.Table(self.wiki, table_base, table_name, self.user_key)
            self.used_table_name = table_name

    def create_table(self):
        """Create a new Wiki table from an Airtable table."""
        self.table.set_table_page()
        print("Go to {} in your DokuWiki to see the table.".format(self.table.dw_table_page))
        if self.used_table_name not in self.defined_tables:
            print("To change the table formatting, implement an appropriate class.")

    def create_pages(self):
        """Create a set of Wiki pages from an Airtable table."""
        self.table.set_pages()
        if self.used_table_name not in self.defined_tables:
            print("Go to 'test:test_page' in your DokuWiki to see the possible page content. "
                  "To change its formatting, please implement an appropriate class.")
        else:
            print("Go to {} namespace in your DokuWiki to see the pages.".format(self.table.root_namespace))

    def create_table_pages(self):
        """Create a table and a set of pages on the Wiki from an Airtable table."""
        self.table.set_table_page()
        print("Go to {} in your DokuWiki to see the table.".format(self.table.dw_table_page))
        if self.table.linked_pages:
            self.table.set_pages()
            if self.used_table_name not in self.defined_tables:
                print("Go to 'test:test_page' in your DokuWiki to see the possible page content.\n "
                      "To change the formatting of this table and pages, implement an appropriate class.")
            else:
                print("Go to {} namespace in your DokuWiki to see the pages.".format(self.table.root_namespace))
        else:
            print("This table does not have associated pages. Only the table has been created.")

    def update_table(self):
        """Re-generate a full table on the Wiki if any record in Airtable table has been modified.
        When done, reset the 'Modified' fields in the Airtable."""
        modified_records = 0
        for record in self.table.records:
            if 'Modified' in record['fields']:
                modified_records += 1
                self.table.airtable.update(record['id'], {'Modified': False})
        if modified_records > 0:
            self.table.set_table_page()

    def update_pages(self):
        """Re-generate the pages on Wiki associated with any records that have been modified in the Airtable.
        When done, reset the 'Modified' fields in the Airtable."""
        modified_records = []
        for record in self.table.records:
            if 'Modified' in record['fields']:
                modified_records.append(record)
                self.table.airtable.update(record['id'], {'Modified': False})
        if len(modified_records) > 0:
            self.table.records = modified_records
            self.table.set_pages()

    def update_table_pages(self):
        """Re-generate the full table on the Wiki if any record has been modified, as well as associated pages.
        When done, reset the 'Modified' fields in the Airtable."""
        modified_records = []
        for record in self.table.records:
            if 'Modified' in record['fields']:
                modified_records.append(record)
                self.table.airtable.update(record['id'], {'Modified': False})
        if len(modified_records) > 0:
            self.table.set_table_page()
            self.table.records = modified_records
            self.table.set_pages()
            print("Updated {} records in table {}.".format(len(modified_records), self.used_table_name))
