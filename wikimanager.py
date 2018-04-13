"""
This is a script that defines the main classes for managing the DokuWiki content in connection
with Airtable, i.e. creating new pages or updating the existing ones.
"""

import os
import dokuwiki as dw
import wikicontents


# in addition to tables that are associated with wiki pages,
# there can be tables not associated with pages and pages not associated with tables
# i.e. update_table has to check this but both update_table and update_pages should be callable separately
class WikiManager:

    def __init__(self, version):
        # for DokuWiki we need url, user name and password
        usr = "katja"  # this has to be added to the remoteuser in config:authentication
        if version == 'official':
            # the official DW
            url = "http://innovationsinfundraising.org/"
            pss = os.environ['DOKUWIKI_PASS']
        elif version == 'test':
            # local testing ground
            url = "http://localhost/~katja/dokuwiki"
            pss = os.environ['DOKUWIKI_PASS_TEST']
        else:
            print('Unknown version specified, choose from: "official" or "test"')
            return
        self.wiki = dw.DokuWiki(url, usr, pss)
        self.user_key = os.environ['AIRTABLE_API_KEY']
        self.table = None

    def setup_table(self, table_name):
        if table_name == 'tools_public_sample':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.ToolTable(self.wiki, table_base, table_name, self.user_key)

        elif table_name == 'ftse100+givingpolicies':
            table_base = 'apprleNrkR7dTtW60'
            self.table = wikicontents.FtseTable(self.wiki, table_base, table_name, self.user_key)

        elif table_name == 'Charity experiments':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.ExperimentTable(self.wiki, table_base, table_name, self.user_key)

        elif table_name == 'Third sector':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.ThirdSectorTable(self.wiki, table_base, table_name, self.user_key)

        elif table_name == 'papers_mass':
            table_base = 'appBzOSifwBqSuVfH'
            self.table = wikicontents.PapersTable(self.wiki, table_base, table_name, self.user_key)

        else:
            print('An interface to this table has not been implemented yet')

    def create_table(self):
        self.table.set_table_page()

    def create_pages(self):
        self.table.set_pages()

    def update_table(self):
        """Re-generate the full table on DW if any record has been modified.
        When done, reset the 'Modified' fields in the Airtable."""
        modified_records = 0
        for record in self.table.records:
            if 'Modified' in record['fields']:
                modified_records += 1
                self.table.airtable.update(record['id'], {'Modified': False})
        if modified_records > 0:
            self.table.set_table_page()
            if self.table.linked_pages:
                print("The table has linked DW pages. Remember to call manager.update_pages() to update them.")

    def update_pages(self):
        """Re-generate the pages on DW associated with any records that have been modified.
        When done, reset the 'Modified' fields in the Airtable."""
        modified_records = []
        for record in self.table.records:
            if 'Modified' in record['fields']:
                modified_records.append(record)
                self.table.airtable.update(record['id'], {'Modified': False})
        if len(modified_records) > 0:
            self.table.records = modified_records
            self.table.set_pages()
