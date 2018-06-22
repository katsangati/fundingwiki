"""
Define functions and classes for representing Airtable data, manipulating it and redirecting it to the Wiki
in different formats (as tables or pages).
"""
# noinspection PyPackageRequirements
import airtable as at
from functools import reduce
import string
import time
import doi_resolver as dr
from pybtex.database.input import bibtex
import json
from collections import OrderedDict


# define a punctuation stripper for using later in pagename constructors
punctuation_translator = str.maketrans('', '', string.punctuation)
bibtex_translator = str.maketrans('', '', '\\{}')


def insert_check(value, record):
    if value not in record['fields']:
        return ""
    else:
        return u'\u2713'


def make_external_link(record, link_name, label_type, label_name):
    link = record['fields'].get(link_name, '')

    if label_type == 'field':
        label = record['fields'].get(label_name, '')
        if link != '':
            return '[[{}|{}]]'.format(link, label)
        else:
            return label
    else:
        if link != '':
            return '[[{}|{}]]'.format(link, label_name)
        else:
            return ''


def make_internal_link(record, label_name, namespace, replacement_label_name):
    # fetch the column whose value will be displayed in the link
    label = record['fields'].get(label_name, '')
    # the label will be used to create a DW page name and we have to remove all punctuation for this purpose
    # (because a web link cannot have punctuation marks on DW)
    page_name = label.translate(punctuation_translator)
    # create a DW link to that page
    if replacement_label_name is None:
        link = '[[{}:{}|{}]]'.format(namespace, page_name, label)
    else:
        replacement_label = record['fields'][replacement_label_name]
        link = '[[{}:{}|{}]]'.format(namespace, page_name, replacement_label)
    return link


def get_linked_items(airtable, column_name, record, linked_column_name):
    """Fetch linked item names from a given column in a given record.
    This is used when a table we are using has a column in which records are not natively present
    but linked from a different table. The Airtable API provides such records as their ids.
    This function looks up these records and retrieves information from a specified column in their table.

    Args:
        airtable: airtable object associated with the table
        column_name: the name of the column that contains linked item ids
        record: which record to fetch for
        linked_column_name: the name of the column in a linked table that we use to retrieve meaningful item names

    Returns:
        str: joined item names

    """
    if column_name in record['fields']:
        item_ids = record['fields'][column_name]
        item_names = [airtable.get(item_id)['fields'][linked_column_name] for item_id in item_ids]
        items = ', '.join(item_names)
    else:
        items = ''
    return items


def get_paper_links(airtable, paper_ids, label, fulltext):
    # This function is used when we need to link to paper pages from outside the paper table
    # This can appear as [[paper_title | paper_title]] or [[paper_title | parencite]]
    # and additionally can have an external link to full text
    papers = []
    # create links only if there are papers in the table for a given tool
    if len(paper_ids) > 0:
        for paper_id in paper_ids:
            p_title = airtable.get(paper_id)['fields'].get('Title', '')
            p_parencite = airtable.get(paper_id)['fields'].get('parencite', '')
            # paper pages use paper Titles for their web address and main heading
            # web addresses do not have punctuation
            paper_page_name = p_title.translate(punctuation_translator)
            # create a DW link to paper page
            # the label that links to that page can be Title or parencite
            if label == 'title':
                paper_page = '[[papers:{}|{}]]'.format(paper_page_name, p_title)
            elif label == 'parencite':
                paper_page = '[[papers:{}|{}]]'.format(paper_page_name, p_parencite)
            else:
                paper_page = ''

            if fulltext:
                p_url = airtable.get(paper_id)['fields'].get('URL', '')
                if p_url != '':
                    # we also link to paper full text when available
                    fulltext_link = '[[{}|Full text]]'.format(p_url)
                    paper_page += ', ' + fulltext_link
            papers.append(paper_page)
    return papers


def get_tool_links(airtable, tool_ids):
    # This function is used when we need to link to tool pages from outside the tool table
    related_tools = []
    # create links only if there are papers in the table for a given tool
    if len(tool_ids) > 0:
        for tool_id in tool_ids:
            tool_name = airtable.get(tool_id)['fields'].get('Tool name', '')
            tool_page_name = tool_name.translate(punctuation_translator)
            tool_dw_table_page = '[[tools:{}|{}]]'.format(tool_page_name, tool_name)
            related_tools.append(tool_dw_table_page)
    return related_tools


def make_bullets(bullet_items):
    if len(bullet_items) > 0:
        return '\n\n  * ' + '\n\n  * '.join(filter(None, bullet_items)) + '\n'
    else:
        return ''


def format_value(coltype, value):
    """
    Depending on column type, format cell value:
    - if value is a type of string, strip and return
    - if value is a number, convert to string
    - if value is a list, join it into a string
    - if value is a list of linked record ids, fetch required information from a linked table (using the ids)
    - if value is a checkbox, return check mark
    - other types are returned as is

    Args:
        coltype:
        value:

    Returns:

    """

    if value == "":
        return ""
    else:
        if coltype in ["Single line text", "Long text", "Single select", "Date", "Phone number", "Email", "URL"]:
            return value.strip().replace('\n', ' \\\\ ').replace('\r', '')
        # TODO "Duration" is returned in seconds and should be converted
        elif coltype in ["Number", "Currency", "Percent", "Duration", "Rating"]:
            return str(value)
        elif coltype in ["Multiple select", "Lookup"]:
            return ", ".join(value)
        elif coltype == "Checkbox":
            return u'\u2713'
        elif coltype == "Single collaborator":
            return value["name"]
        elif coltype == "Multiple collaborator":
            return ", ".join(v["name"] for v in value)
        elif coltype == "Attachment":
            # we assume for now that all attachments are pictures
            return "{{" + value[0]["url"] + "?400}}\n"
        elif coltype in ["Link to another record", "External link", "Internal link", "Raw"]:
            return value
        else:
            print("Column type '{}' unrecognized".format(coltype))
            return ""


class Table:
    """
    Top-level Table class that provides a blueprint for all more specific tables and instantiates
    common methods and methods with default parameters.

    Each sub-class:
    - defines its own attribute values
    - redefines a number of methods (mostly construct_row and create_page)
    Together they specify the format of tables and pages for a given Airtable table.

    In order to create a new interface for some table in the Airtable database, a new class specific for that table
    needs to be defined here.

    Attributes:
        wiki (DokuWiki): the wiki object passed from the wikimanager
        airtable (Airtable): Airtable object that provides an API connection to the Airtable table
        records (list): a list of Airtable table records
        dw_table_page (str): wiki page link for the table
        included_in (str): wiki page link for where the table is included
        main_column (str): the name of the first column of the table
        header (str): the table header
        linked_pages (bool): whether there are wiki pages fed from this table
        dw_page_template (str): a template for page generated from this table
        dw_page_name_column (str): the column that is used for constructing a page link
        root_namespace (str): the namespace in which pages will be included

    """

    def __init__(self, wiki, base_name, table_name, user_key):
        """Instantiate a Table object.
        Whenever a table drawn from Airtable does not have a specific Table class associated with it,
        this top-level Table will be used.

        Args:
            wiki (Dokuwiki): the wiki object passed from the wikimanager
            base_name (str): API key to the Airtable base in which the table resides
            table_name (str): the name of the table in the Airtable base
            user_key (str): user API key to the Airtable
        """
        self.wiki = wiki
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        with open('tabledef.json', 'r') as f:
            self.tabledefs = json.load(f)
        self.dw_table_page = 'tables:test'
        self.included_in = None
        self.main_column = None
        self.header = ''
        self.columndefs = self.tabledefs.get(table_name, None)
        self.linked_pages = True
        # if the table feeds DW pages
        if self.linked_pages:
            self.dw_page_template = None
            self.dw_page_name_column = None
            self.root_namespace = None

    @staticmethod
    def construct_header(columndefs):
        header = []
        for k, v in columndefs.items():
            if v['table']['publish']:
                header.append((v['table']['pos'], v['table']['header']))
        header = [h[1] for h in sorted(header, key=lambda x: x[0])]
        formatted_header = "\n^ " + " ^ ".join(header) + " ^\n"
        return formatted_header

    @staticmethod
    def construct_placeholders(columndefs):
        keys = []
        for k, v in columndefs.items():
            if v['page']['publish']:
                keys.append((v['page']['pos'], v['page']['placeholder']))
        keys = [h[1] for h in sorted(keys, key=lambda x: x[0])]
        return keys

    def construct_row(self, record):
        """Construct a single table row for a given record.

        Args:
            record (dict): a single table record

        Returns:
            (str) formatted row for the table based on record content
        """
        row = "| "
        for key, value in record['fields'].items():
            row += repr(value)
            row += " | "
        row += " |\n"
        return row

    def fetch_row(self, columndefs, record, target_format='table'):
        row = []
        for k, v in columndefs.items():
            if v[target_format]['publish']:
                if v['type'] == "External link":
                    value = make_external_link(record, v[target_format]["URL"],
                                               v[target_format]['label_type'],
                                               v[target_format]['label'])
                elif v['type'] == "Internal link":
                    value = make_internal_link(record, v[target_format]['label'],
                                               v[target_format]['namespace'],
                                               v[target_format]['replacement_label'])
                elif v['type'] == "Link to another record":
                    value = get_linked_items(self.airtable, k, record,
                                             v[target_format]['linked_column_name'])
                else:
                    value = record['fields'].get(k, "")

                row.append((v[target_format]['pos'], format_value(v['type'], value)))

        row = [v[1] for v in sorted(row, key=lambda x: x[0])]
        return row

    def automatic_construct_row(self, record):
        row = self.fetch_row(self.columndefs, record)
        formatted_row = "| " + " | ".join(row) + " |\n"

        return formatted_row

    def format_table(self, page_length=None):
        """Construct a full table for Airtable table records.
        Loop through all records and collect all formatted rows.

        Returns:
            (str) formatted table
        """
        if page_length is not None:
            table_content = '<datatables page-length="{}">\n'.format(page_length)
        else:
            table_content = ''
        # initialize table content with the header
        table_content += self.header
        # construct the rows for all available records using the corresponding constructor function
        for record in self.records:
            # we only consider records in which the main column is not empty
            if (self.main_column is not None) and (self.main_column not in record['fields']):
                pass
            else:
                # print(record['fields']['Tool name'])
                if self.columndefs is None:
                    # this means we haven't defined the table yet
                    table_content += self.construct_row(record)
                else:
                    table_content += self.automatic_construct_row(record)
        if page_length is not None:
            table_content += '</datatables>\n'
        return table_content

    def set_table_page(self):
        new_page = self.format_table()
        self.wiki.pages.set(self.dw_table_page, new_page)

    def create_page(self, record):
        """Construct a default page for a single record.

        Args:
            record: a single record from the Airtable

        Returns:
            (str) a formatted page
        """
        page = ""
        for key, value in record['fields'].items():
            page += key.upper() + "\n\n"
            page += repr(value) + "\n"
            page += "\n"
        return page

    def format_pages(self, records):
        """Construct pages for all provided records.

        Args:
            records: Airtable records

        Returns:
            (dict) a set of pages indexed by their wiki link names
        """
        new_pages = {}
        if (self.main_column is None) and (self.dw_page_name_column is None):
            record = records[0]
            page_name = 'test:test_page'
            page = self.create_page(record)
            new_pages[page_name] = page
        else:
            for record in records:
                # print(record['fields']['Tool name'])
                if (self.main_column not in record['fields']) or (self.dw_page_name_column not in record['fields']):
                    pass
                else:
                    page_name = record['fields'][self.dw_page_name_column]
                    clean_page_name = page_name.translate(punctuation_translator)
                    full_page_name = self.root_namespace + clean_page_name
                    page = self.create_page(record)
                    new_pages[full_page_name] = page
        return new_pages

    def set_pages(self):
        """Format pages for table records and post them to the wiki."""
        new_pages = self.format_pages(self.records)
        # this has to be done with a break of at least 5s
        for page in new_pages:
            self.wiki.pages.set(page, new_pages[page])
            time.sleep(5)


class ToolTable(Table):
    """
    One of the sub-classes of the Table class that defines a specific format for tables and pages
    based on the Tools table in the Airtable database.
    """
    def __init__(self, wiki, base_name, table_name, user_key):
        super(ToolTable, self).__init__(wiki, base_name, table_name, user_key)  # call the top class initialization
        self.airtable = at.Airtable(base_name, table_name, user_key)  # create connection to the Airtable table
        self.records = self.airtable.get_all()  # fetch all records
        self.dw_table_page = 'tables:tools'  # define where the table will be posted on the Wiki
        self.included_in = 'tools:tools'  # define where the table will be actually displayed for the public
        self.main_column = 'Tool name'  # which column is the main one
        # define table header
        self.columndefs = self.tabledefs[table_name]
        self.header = self.construct_header(self.columndefs)
        self.placeholders = self.construct_placeholders(self.columndefs)
        # specify whether the table also feeds a set of Wiki pages
        self.linked_pages = True
        # define a Wiki page template; placeholders in uppercase to be replaced with actual data
        self.root_namespace = 'tools:'
        self.dw_page_template = wiki.pages.get(self.root_namespace+'pagetemplate')
        # which column will be used to create a page name (and its location on the Wiki)
        self.dw_page_name_column = 'Tool name'
        # under which namespace the pages will be placed


    def automatic_construct_row(self, record):
        """
        Construct a row for the tools table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        # only consider rows for which 'Wiki?' column is set to True
        if 'Wiki?' in record['fields']:
            row = self.fetch_row(self.columndefs, record)
            cat_pos = self.columndefs['Category']['table']['pos'] - 1
            category_ids = row[cat_pos]

            # create category pop-overs
            if len(category_ids) > 0:
                category_names = [self.airtable.get(cat_id)['fields']['(Sub)Category or theme'] for
                                  cat_id in category_ids]
                category_descriptions = [self.airtable.get(cat_id)['fields']['Description'].rstrip() for
                                         cat_id in category_ids]
                categories = ["<popover content=\"{}\" trigger='hover'>{}</popover>".format(description, name) for
                              description in category_descriptions for name in category_names]
            else:
                categories = ''

            row[cat_pos] = ', '.join(categories)
            # papers will also link to their pages, so we need to create those links
            paper_pos = self.columndefs['key_papers']['table']['pos'] - 1
            key_papers = get_paper_links(self.airtable, row[paper_pos], 'parencite', False)
            row[paper_pos] = ', '.join(key_papers)
            formatted_row = "| " + " | ".join(row) + " |\n"
        else:
            formatted_row = ''

        return formatted_row

    def create_page(self, record):
        """
        Construct a page for each tool.
        :param record: a single record from the Airtable
        :return: a formatted page
        """
        variables = self.fetch_row(self.columndefs, record, target_format="page")

        cat_pos = self.columndefs['Category']['page']['pos'] - 1
        variables[cat_pos] = get_linked_items(self.airtable, 'Category', record, '(Sub)Category or theme')

        # insert links to relevant papers
        paper_pos = self.columndefs['key_papers']['page']['pos'] - 1
        papers = get_paper_links(self.airtable, variables[paper_pos], 'title', True)
        variables[paper_pos] = make_bullets(papers)

        secondary_pos = self.columndefs['secondary papers']['page']['pos'] - 1
        secondary_papers = get_paper_links(self.airtable, variables[secondary_pos], '', True)
        variables[secondary_pos] = make_bullets(secondary_papers)

        keys = self.placeholders
        # define replacements: a set of tuples in which the first item is an uppercase placeholder
        # and the second item is the variable that is to replace it
        replacements = tuple(zip(keys, variables))

        # perform the replacements of placeholders with data for a given record and insert it into
        # the locations defined in the page template
        tool_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.dw_page_template)
        return tool_page

    def set_pages(self):
        # create pages only for the records in which 'Wiki?' is true
        relevant_records = []
        for record in self.records:
            if 'Wiki?' in record['fields']:
                relevant_records.append(record)
        new_pages = self.format_pages(relevant_records)
        # this has to be done with a break of at least 5s
        for page in new_pages:
            self.wiki.pages.set(page, new_pages[page])
            time.sleep(5)


class FtseTable(Table):
    def __init__(self, wiki, base_name, table_name, user_key, company_group):
        super(FtseTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.included_in = 'iifwiki:employee_giving_schemes'
        self.main_column = 'Company'
        self.columndefs = self.tabledefs['Giving_companies']
        self.header = self.construct_header(self.columndefs)
        self.placeholders = self.construct_placeholders(self.columndefs)
        self.linked_pages = True
        self.dw_page_template = '====COMPANY====\n\\\\\n' \
                                '**Sector**: SECTOR\n\n' \
                                '**Donation matching**: MATCH\n\n' \
                                '**Payroll giving**: PAYROLL\n\n' \
                                '**Pays PG fees**: FEES\n\n' \
                                '**PG provider**: PROVIDER\n\n' \
                                '**Endorsed charities**: ENDORSED\n\\\\\n\\\\\n' \
                                '===Details of matching schemes===\n\nMATCH_DETAILS\n\n' \
                                '**Total max EA benefit**: BENEFIT\n\\\\\n\\\\\n' \
                                '===Details of payroll giving and other programmes===\n\n' \
                                'PAYROLL_DETAILS\n\\\\\n\\\\\n' \
                                '===Other relevant information===\n\nOTHER_DETAILS\n\\\\\n\\\\\n' \
                                '===Outcomes===\n\nOUTCOMES\n\\\\\n\\\\\n' \
                                '===Sources, links to further information===\n\n' \
                                '\n\n  * REF \n' \
                                'LINKS\n\\\\\n'
        self.dw_page_name_column = 'Company'
        self.root_namespace = 'companies:'
        self.company_group = company_group  # (str) use this to differentiate between FTSE companies and other
        self.dw_table_page = 'tables:employee_giving_schemes_' + self.company_group

    def format_table(self, page_length=None):
        table_content = '<datatables page-length="50">\n'
        # initialize table content with the header
        table_content += self.header
        # construct the rows for all available records using the corresponding constructor function
        for record in self.records:
            # we only consider records in which the main column is not empty
            if (self.main_column is not None) and (self.main_column not in record['fields'])\
                    and record['fields']['Company group'] != self.company_group:
                pass
            else:
                table_content += self.automatic_construct_row(record)
        table_content += '</datatables>\n'
        return table_content

    def create_page(self, record):
        """
        Construct a page for each company.
        :param record: a single record from the Airtable
        :return: a formatted page
        """
        variables = self.fetch_row(self.columndefs, record, target_format="page")

        fee_pos = self.columndefs['Pays PG fees']['page']['pos']-1
        variables[fee_pos] = variables[fee_pos] + " Note: This field needs more research."

        link_pos = self.columndefs['Other links']['page']['pos']-1
        if len(variables[link_pos]) > 0:
            sources = record['fields']['Other links'].split("; ")
            sources = [s.strip() for s in sources]
            variables[link_pos] = make_bullets(sources)
        else:
            variables[link_pos] = ''
        keys = self.placeholders
        replacements = tuple(zip(keys, variables))

        ftse_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.dw_page_template)
        return ftse_page

    def set_pages(self):
        relevant_records = []
        for record in self.records:
            if record['fields']['Company group'] == self.company_group:
                relevant_records.append(record)
        new_pages = self.format_pages(relevant_records)
        # this has to be done with a break of at least 5s
        for page in new_pages:
            self.wiki.pages.set(page, new_pages[page])
            time.sleep(10)


class PapersTable(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(PapersTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:papers'
        self.included_in = 'papers:papers'
        self.main_column = 'parencite'
        self.columndefs = self.tabledefs['papers_mass_qualitative']
        self.header = self.construct_header(self.columndefs)
        self.placeholders = self.construct_placeholders(self.columndefs)
        self.linked_pages = True
        self.dw_page_template = '====PAPERTITLE====\n\n' \
                                'REFERENCE\n\n' \
                                'ILLUSTRATION' \
                                '**Keywords**: KEYWORDS\n\n' \
                                '**Discipline**: DISCIPLINE\n\n' \
                                '**Type of evidence**: EVIDENCE\n\n' \
                                '**Related tools**: TOOLS\n\n' \
                                '**Related theories**: THEORIES\n\n' \
                                '**Related critiques**: CRITIQUES\n\n' \
                                '**Charity target**: TARGETS\n\n' \
                                '**Donor population**: DONORS\n\\\\\n\\\\\n' \
                                '===Paper summary===\n\nSUMMARY\n\\\\\n' \
                                '===Discussion===\n\nDISCUSSION\n\\\\\n' \
                                '===Evaluation===\n\nEVALUATION\n\\\\\n' \
                                'META\n\\\\\n' \
                                'This paper has been added by CREATORS'  # and evaluated by EVALUATORS'
        self.dw_page_name_column = 'Title'
        self.root_namespace = 'papers:'

    def automatic_construct_row(self, record):
        """
        Construct a row for papers table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        row = self.fetch_row(self.columndefs, record)
        # related tools will also link to their pages, so we need to create those links
        tool_pos = self.columndefs['tools']['table']['pos'] - 1
        related_tools = get_tool_links(self.airtable, row[tool_pos])
        row[tool_pos] = ', '.join(related_tools)
        formatted_row = "| " + " | ".join(row) + " |\n"

        return formatted_row

    def set_table_page(self):
        new_page = self.format_table(page_length=100)
        self.wiki.pages.set(self.dw_table_page, new_page)

    def create_page(self, record):
        """
        Construct a page for each paper.
        :param record: a single record from the Airtable
        :return: a formatted page
        """
        variables = self.fetch_row(self.columndefs, record, target_format="page")

        tool_pos = self.columndefs['tools']['page']['pos'] - 1
        related_tools = get_tool_links(self.airtable, variables[tool_pos])
        variables[tool_pos] = ', '.join(related_tools)

        meta_pos = self.columndefs['meta']['page']['pos'] - 1
        variables[meta_pos] = self.make_meta(record)

        keys = self.placeholders
        replacements = tuple(zip(keys, variables))
        paper_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.dw_page_template)

        return paper_page

    def update_record(self, record):
        # if doi present
        if 'doi' in record['fields']:
            doi = record['fields']['doi']

            # fill in bibtex
            bib = dr.doi2bib(doi)
            self.airtable.update(record['id'], {'bibtexfull': bib})

            # fill in citation count
            citations = dr.doi2count(doi)
            self.airtable.update(record['id'], {'num_citations': int(citations)})

            # fill in bibliographic information
            self.fill_bibliography(record)

        elif 'bibtexfull' in record['fields']:
            # fill in bibliographic information
            self.fill_bibliography(record)

        else:
            print("This paper record has neither doi nor bibtex specified.")
            pass
        time.sleep(5)

    def fill_bibliography(self, record):
        bib_string = record['fields']['bibtexfull']

        # fill in citation data
        parser = bibtex.Parser()
        bib_data = parser.parse_string(bib_string)
        k = bib_data.entries.keys()[0]
        print(k)
        bib_type = bib_data.entries[k].type
        self.airtable.update(record['id'], {'Publication_type': bib_type})

        authors_list = [p.__str__() for p in bib_data.entries[k].persons['author']]
        authors = "; ".join(authors_list)
        year = bib_data.entries[k].fields.get('year', '')
        title = bib_data.entries[k].fields['title']

        link = record['fields'].get('URL', '')

        if link == '':
            title = '//{}//'.format(title)
        else:
            title = '//[[{}|{}]]//'.format(link, title)

        self.airtable.update(record['id'], {'Authors': authors})
        self.airtable.update(record['id'], {'Year': year})
        self.airtable.update(record['id'], {'Title': title})

        if bib_type == "article":
            # Author, N. (year). Title. Journal Name, Vol, Num, Pages.
            journal = bib_data.entries[k].fields['journal']
            journal = journal.translate(bibtex_translator).lower().title()
            volume = bib_data.entries[k].fields.get('volume', '')
            number = bib_data.entries[k].fields.get('number', '')
            pages = bib_data.entries[k].fields.get('pages', '')
            reference = '{}, ({}). {}. {}, {}, {}, {}.'.format(authors, year, title, journal, volume, number, pages)

            self.airtable.update(record['id'], {'Journal': journal})
            self.airtable.update(record['id'], {'Vol': volume})
            self.airtable.update(record['id'], {'Num': number})
            self.airtable.update(record['id'], {'Pages': pages})

        elif bib_type == "incollection":
            # Author, N. (year). Chapter title, Pages. In: Book title.
            book = bib_data.entries[k].fields['booktitle']
            book = book.lower().title()
            pages = bib_data.entries[k].fields.get('pages', '')
            reference = '{}, ({}). {}, {}. In: {}.'.format(authors, year, title, pages, book)

            self.airtable.update(record['id'], {'Book_title': book})
            self.airtable.update(record['id'], {'Pages': pages})

        elif bib_type == "techreport":
            # Author, N. (year). Title. Institution.
            institution = bib_data.entries[k].fields.get('institution', '')
            reference = '{}, ({}). {}. {}.'.format(authors, year, title, institution)

            self.airtable.update(record['id'], {'Institution': institution})

        else:
            # nothing to add for book and misc
            # Author, N. (year). Title.
            reference = '{}, ({}). {}.'.format(authors, year, title)

        self.airtable.update(record['id'], {'Reference': reference})

        # create parencite
        first_author = bib_data.entries[k].persons['author'][0].last_names[0]

        if len(authors_list) == 0:
            parencite = ""
        elif len(authors_list) == 1:
            parencite = "({}, '{})".format(first_author, year[-2:])
        elif len(authors_list) == 2:
            second_author = bib_data.entries[k].persons['author'][1].last_names[0]
            parencite = "({} & {}, '{})".format(first_author, second_author[0], year[-2:])
        else:
            parencite = "({} ea, '{})".format(first_author, year[-2:])

        self.airtable.update(record['id'], {'parencite': parencite})

    def make_meta(self, record):
        meta_template = '<button collapse="meta">Meta-analysis data</button><collapse id="meta" ' \
                        'collapsed="true"><well>'\
                        '<WRAP third column>' \
                        '**Study year**: R01\n\n' \
                        '**Data link**: R02\n\n' \
                        '**Peer reviewed**: R03\n\n' \
                        '**Journal rating**: R04\n\n' \
                        '**Citations**: R05\n\n' \
                        '**Replications**: R06\n\n' \
                        '**Replication success**: R07\n\n' \
                        '**Pre-registered**: R08\n\n' \
                        '**Verified**: R09\n\n' \
                        '**Participants aware**: R10\n\n' \
                        '**Demographics**: R11\n\n' \
                        '</WRAP>' \
                        '<WRAP third column>' \
                        '**Design**: R12\n\n' \
                        '**Simple comparison**: R13\n\n' \
                        '**Sample size**: R14\n\n' \
                        '**Share treated**: R15\n\n' \
                        '**Key components**: R16\n\n' \
                        '**Main treatment**: R17\n\n' \
                        '**Mean donation**: R18\n\n' \
                        '**SD donation**: R19\n\n' \
                        '**Endowment amount**: R20\n\n' \
                        '**Endowment description**: R21\n\n' \
                        '**Currency**: R22\n\n' \
                        '</WRAP>' \
                        '<WRAP third column>' \
                        '**Conversion rate**: R23\n\n' \
                        '**Effect size original**: R24\n\n' \
                        '**Effect size USD**: R25\n\n' \
                        '**SE effect size**: R26\n\n' \
                        '**SE calculation**: R27\n\n' \
                        '**Effect size share**: R28\n\n' \
                        '**Mean incidence**: R29\n\n' \
                        '**Effect size incidence**: R30\n\n' \
                        '**Headline p-val**: R31\n\n' \
                        '**P-val description**: R32\n\n' \
                        '</WRAP>' \
                        '</well></collapse>'

        variables = self.fetch_row(self.tabledefs['papers_mass_quantitative'], record)
        # we don't need the reference column here
        variables = variables[1:]
        keys = ['R0' + str(i) for i in range(1, 10)] + ['R' + str(i) for i in range(10, 33)]

        replacements = tuple(zip(keys, variables))
        meta_well = reduce(lambda a, kv: a.replace(*kv, 1), replacements, meta_template)
        return meta_well


class MetaAnalysisTable(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(MetaAnalysisTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:meta'
        self.included_in = 'papers:meta_analysis'
        self.main_column = 'parencite'
        self.columndefs = self.tabledefs['papers_mass_quantitative']
        self.header = self.construct_header(self.columndefs)
        self.linked_pages = False

    def set_table_page(self):
        new_page = self.format_table(page_length=100)
        self.wiki.pages.set(self.dw_table_page, new_page)


class CategoryTable(Table):
    def __init__(self, wiki, base_name, table_name, user_key):
        super(CategoryTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:tool_categories'
        self.included_in = 'tools:tool_categories'
        self.main_column = '(Sub)Category or theme'
        self.columndefs = self.tabledefs[table_name]
        self.header = self.construct_header(self.columndefs)
        self.linked_pages = False

    def set_table_page(self):
        new_page = self.format_table(page_length=100)
        self.wiki.pages.set(self.dw_table_page, new_page)


class ExperienceTable(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(ExperienceTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:experiences_of_workplace_activists'
        self.included_in = 'iifwiki:experiences_of_workplace_activists'
        self.main_column = 'Name'
        self.columndefs = self.tabledefs[table_name]
        default_header = self.construct_header(self.columndefs)
        header = list(OrderedDict.fromkeys(default_header[3:-3].split(" ^ ")))
        self.header = "\n^ " + " ^ ".join(header) + " ^\n"
        self.linked_pages = False

    def automatic_construct_row(self, record):
        """
        Construct a row for fundraising experiences table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        row = self.fetch_row(self.columndefs, record)

        concise_row = list()
        concise_row.append(row[self.columndefs['Name']['table']['pos']-1] + ", " +
                           row[self.columndefs['Role']['table']['pos']-1])
        concise_row.append(row[self.columndefs['Organisation']['table']['pos']-1] + ", " +
                           row[self.columndefs['Organisation type']['table']['pos']-1])
        emp_pos = self.columndefs['Number of employees']['table']['pos']-1
        motiv_pos = self.columndefs['Choice motivation']['table']['pos']-1
        concise_row.extend(row[emp_pos:motiv_pos])

        comm_pos = self.columndefs['Communication channel']['table']['pos']-1
        arg_pos = self.columndefs['Main arguments']['table']['pos'] - 1
        prob_pos = self.columndefs['Problems faced']['table']['pos'] - 1
        eval_pos = self.columndefs['Evaluation']['table']['pos'] - 1
        inf_pos = self.columndefs['Comments']['table']['pos'] - 1

        results = "**Choice motivation**: " + row[motiv_pos] + "\\\\ " +\
                  "**Communication channel**: " + row[comm_pos] + "\\\\ " +\
                  "**Main arguments**: " + row[arg_pos] + "\\\\ " +\
                  "**Problems faced**: " + row[prob_pos] + "\\\\ " +\
                  "**Evaluation**: " + row[eval_pos] + "\\\\ " +\
                  "**Additional information**: " + row[inf_pos]

        concise_row.append(results)

        formatted_row = "| " + " | ".join(concise_row) + " |\n"
        return formatted_row


class ExperimentTable(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(ExperimentTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:data_experiments'
        self.included_in = 'iifwiki:dataexperiments'
        self.main_column = 'Experiment'
        self.columndefs = self.tabledefs[table_name]
        self.header = self.construct_header(self.columndefs)
        self.linked_pages = False


class ThirdSectorTable(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(ThirdSectorTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:third_sector_infrastructure_details'
        self.included_in = 'iifwiki:third_sector_infrastructure_details'
        self.main_column = 'Name'
        self.columndefs = self.tabledefs[table_name]
        self.header = self.construct_header(self.columndefs)
        self.linked_pages = False


class EffectiveCharities(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(EffectiveCharities, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:effective_charities'
        self.included_in = 'iifwiki:earatings'
        self.main_column = 'charity_name'
        self.columndefs = self.tabledefs[table_name]
        self.header = self.construct_header(self.columndefs)
        self.linked_pages = False
