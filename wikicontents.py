"""
Define functions and classes for representing Airtable data, manipulating it and redirecting it to the Wiki
in different formats (as tables or pages).
"""
import airtable as at
from functools import reduce
import string
import re
import time
import doi_resolver as dr
from pybtex.database.input import bibtex


# define a punctuation stripper for using later in pagename constructors
punctuation_translator = str.maketrans('', '', string.punctuation)
bibtex_translator = str.maketrans('', '', '\\{}')


def insert_check(value, record):
    if value not in record['fields']:
        return ""
    else:
        return u'\u2713'


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


def format_citation(record):
    """Format publication citation for paper pages according to its type.

    Args:
        record: which record to use to format the reference

    Returns:
        str: formatted reference

    """
    bib_type = record['fields']['Publication_type']

    authors = record['fields'].get('Authors', '')
    year = record['fields'].get('Year', '')
    title = record['fields']['Title']
    link = record['fields'].get('URL', '')

    if link == '':
        title = '//{}//'.format(title)
    else:
        title = '//[[{}|{}]]//'.format(link, title)

    if bib_type == "article":
        journal = record['fields'].get('Journal', '')
        journal = journal.translate(bibtex_translator).lower().title()
        volume = record['fields'].get('Vol', '')
        number = record['fields'].get('Num', '')
        pages = record['fields'].get('Pages', '')
        # Author, N. (year). Title. Journal Name, Vol, Num, Pages.
        reference = '{}, ({}). {}. {}, {}, {}, {}.'.format(authors, year, title, journal, volume, number, pages)

    elif bib_type == "incollection":
        book = record['fields'].get('Book_title', '')
        pages = record['fields'].get('Pages', '')
        # Author, N. (year). Chapter title, Pages. In: Book title.
        reference = '{}, ({}). {}, {}. In: {}.'.format(authors, year, title, pages, book)

    elif bib_type == "techreport":
        institution = record['fields'].get('Institution', '')
        # Author, N. (year). Title. Institution.
        reference = '{}, ({}). {}. {}.'.format(authors, year, title, institution)

    else:
        # Author, N. (year). Title.
        reference = '{}, ({}). {}.'.format(authors, year, title)

    return reference


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
        self.dw_table_page = 'tables:test'
        self.included_in = None
        self.main_column = None
        self.header = ''
        self.linked_pages = True
        # if the table feeds DW pages
        if self.linked_pages:
            self.dw_page_template = None
            self.dw_page_name_column = None
            self.root_namespace = None

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

    def format_table(self):
        """Construct a full table for Airtable table records.
        Loop through all records and collect all formatted rows.

        Returns:
            (str) formatted table
        """
        # initialize table content with the header
        table_content = self.header
        # construct the rows for all available records using the corresponding constructor function
        for record in self.records:
            # we only consider records in which the main column is not empty
            if (self.main_column is not None) and (self.main_column not in record['fields']):
                pass
            else:
                # print(record['fields']['Tool name'])
                table_content += self.construct_row(record)
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
        self.header = "\n^ Tool name ^ Category ^ Description ^ Main findings ^ Key papers ^\n"
        # specify whether the table also feeds a set of Wiki pages
        self.linked_pages = True
        # define a Wiki page template; placeholders in uppercase to be replaced with actual data
        self.dw_page_template = '===== TOOLNAME =====\n\n' \
                                '//DESCRIPTION//\n\\\\\n\\\\\n' \
                                '**Alternative tool name:** AKA\n\n' \
                                '**Tool variation**: TOOLVAR\n\n' \
                                '**Category**: CATEGORY \n\n' \
                                '**Sub-category**: SUBCATEGORY\n\n' \
                                '**Relevant theories**: THEORIES\n\n' \
                                '**Type of evidence**: EVIDENCE\n\n' \
                                '**Evidence strength** (ad hoc assessment): STRENGTH\n\\\\\n\\\\\n' \
                                '==== Main findings ====\n\nFINDINGS\n\\\\\n\\\\\n' \
                                '==== Discussion ====\n\nDISCUSSION\n\\\\\n\\\\\n' \
                                '==== Practical relevance ====\n\nRELEVANCE\n\\\\\n\\\\\n' \
                                '=== Use cases ===\n\nCASES\n\\\\\n\\\\\n' \
                                '**Prevalence:**\n\nPREVALENCE\n\\\\\n\\\\\n' \
                                '==== Key papers ====PAPERS\n\n' \
                                '==== Secondary papers ====PAPERS2\n\n' \
                                '**Contributors** CONTRIBUTOR'
        # which column will be used to create a page name (and its location on the Wiki)
        self.dw_page_name_column = 'Tool name'
        # under which namespace the pages will be placed
        self.root_namespace = 'tools:'

    def construct_row(self, record):
        """
        Construct a row for the tools table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        # only consider rows for which 'Wiki?' column is set to True
        if 'Wiki?' in record['fields']:
            tool_name = record['fields']['Tool name']  # fetch the 'Tool name' column
            # the tool name will be used for the page name and we have to remove all punctuation for this purpose
            # (because a web link cannot have punctuation marks on DokuWiki)
            tool_page_name = tool_name.translate(punctuation_translator)
            # create a DW link to each tool page that will appear in the table
            tool_dw_table_page = '[[tools:{}|{}]]'.format(tool_page_name, tool_name)

            # fetch other columns
            categories = record['fields'].get('Category', [""])
            description = record['fields'].get('Description', "")
            description = description.replace('\n', ' ').replace('\r', '')
            findings = record['fields'].get('Findings summarized', "")
            findings = findings.replace('\n', ' ').replace('\r', '')

            # create category pop-overs
            if len(categories) > 0:
                category_names = [self.airtable.get(cat_id)['fields']['(Sub)Category or theme'] for
                                  cat_id in categories]
                category_descriptions = [self.airtable.get(cat_id)['fields']['Description'].rstrip() for
                                         cat_id in categories]
                cat_column = ["<popover content=\"{}\" trigger='hover'>{}</popover>".format(description, name) for
                              description in category_descriptions for name in category_names]
            else:
                cat_column = ''
            # if 'Theories' not in record['fields']:
            #     theory_names = ''
            # else:
            #     theory_names = [self.airtable.get(theory_id)['fields']['Theory'] for
            #                     theory_id in record['fields']['Theories']]

            # papers will also link to their pages, so we need to create those links
            paper_ids = record['fields'].get('key_papers', '')
            key_papers = []
            # create links only if there are papers in the table for a given tool
            if len(paper_ids) > 0:
                for paper_id in record['fields']['key_papers']:
                    # the table contains parencite text which links to a paper page
                    # paper pages use paper Titles for their web address and main heading
                    paper_name = self.airtable.get(paper_id)['fields'].get('parencite', '')
                    title = self.airtable.get(paper_id)['fields'].get('Title', '')
                    # if a paper has either no parencite or no title filled, skip it
                    if paper_name == '' or title == '':
                        pass
                    else:
                        # remove punctuation from paper title to be used as web address
                        paper_page_name = title.translate(punctuation_translator)
                        # create a DW link to paper page
                        paper_dw_table_page = '[[papers:{}|{}]]'.format(paper_page_name, paper_name)
                        key_papers.append(paper_dw_table_page)

            # construct a row with row separators and all the column variables of interest
            # these have to appear in the same order as defined in the header
            row = "| " + tool_dw_table_page + " | " + ', '.join(cat_column) + " | " + \
                  description.rstrip() + " |" + findings.rstrip() + " | " + '; '.join(key_papers) + " |\n"
        else:
            row = ''
        return row

    def create_page(self, record):
        """
        Construct a page for each tool.
        :param record: a single record from the Airtable
        :return: a formatted page
        """
        # fetch some column data
        tn = record['fields']['Tool name']
        alt_tn = ', '.join(record['fields'].get('AKA', ''))
        tool_var = record['fields'].get('Tool variation', '')

        # fetch column data from linked tables using a separate function (defined above)
        categories = get_linked_items(self.airtable, 'Category', record, '(Sub)Category or theme')
        sub_categories = get_linked_items(self.airtable, 'subcat', record, '(Sub)Category or theme')
        theories = get_linked_items(self.airtable, 'Theories', record, 'Theory')
        cases = get_linked_items(self.airtable, 'Relevant use cases', record, 'Name')

        evid = record['fields'].get('Types of evidence', [""])
        evid_types = ', '.join(evid)

        evid_str = str(record['fields'].get('Evidence strength', ''))
        description = record['fields'].get('Description', "")
        # strip new line from the end of some column data - otherwise the formatting is inconsistent
        summary = record['fields'].get('Findings summarized', "").rstrip()
        discuss = record['fields'].get('Full discussion', "").rstrip()

        relevance = record['fields'].get('Relevance to EA charities', [""])[0].rstrip()
        preval = record['fields'].get('Prevalence', "")

        # insert links to relevant papers - see construct row for explanation on this
        paper_ids = record['fields'].get('key_papers', '')
        if len(paper_ids) > 0:
            papers = []
            for paper_id in record['fields']['key_papers']:
                p_title = self.airtable.get(paper_id)['fields'].get('Title', '')
                paper_page_name = p_title.translate(punctuation_translator)
                p_url = self.airtable.get(paper_id)['fields'].get('URL', '')
                paper_page = ''
                if p_title == '':
                    pass
                else:
                    paper_page = '[[papers:{}|{}]]'.format(paper_page_name, p_title)
                if p_url != '':
                    # we also link to paper full text when available
                    fulltext_link = '[[{}|Full text]]'.format(p_url)
                    paper_page += ', ' + fulltext_link
                papers.append(paper_page)

            if len(papers) > 0:
                # papers appear as a bulleted list
                paper_items = '\n\n  * ' + '\n\n  * '.join(papers) + '\n'
            else:
                paper_items = ''

        else:
            paper_items = ''

        secondary_paper_ids = record['fields'].get('secondary papers', '')
        if len(secondary_paper_ids) > 0:
            secondary_papers = []
            for paper_id in record['fields']['secondary papers']:
                p_title = self.airtable.get(paper_id)['fields'].get('Title', '')
                p_url = self.airtable.get(paper_id)['fields'].get('URL', '')
                if p_title == '' or p_url == '':
                    pass
                else:
                    secondary_papers.append('[[' + p_url + ' | ' + p_title + ']]')
            if len(secondary_papers) > 0:
                secondary_paper_items = '\n\n  * ' + '\n\n  * '.join(secondary_papers) + '\n'
            else:
                secondary_paper_items = ''
        else:
            secondary_paper_items = ''

        contrib = get_linked_items(self.airtable, 'Contributors', record, 'Name, Institution')

        # define replacements: a set of tuples in which the first item is an uppercase placeholder
        # and the second item is the variable that is to replace it
        replacements = ('TOOLNAME', tn), ('DESCRIPTION', description), ('AKA', alt_tn), ('TOOLVAR', tool_var),\
                       ('CATEGORY', categories), ('SUBCATEGORY', sub_categories), \
                       ('THEORIES', theories), ('EVIDENCE', evid_types), ('STRENGTH', evid_str),\
                       ('FINDINGS', summary), ('DISCUSSION', discuss),\
                       ('RELEVANCE', relevance), ('CASES', cases), ('PREVALENCE', preval),\
                       ('PAPERS', paper_items), ('PAPERS2', secondary_paper_items),\
                       ('CONTRIBUTOR', contrib)
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
        self.header = "\n^ Company ^ Sector ^ Donation Matching ^ Payroll Giving ^ DM Details ^ " \
                      "Total EA benefit ^ PG Details ^ Other Details ^ Endorsed ^ Outcomes ^ Reference ^\n"

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
                                'LINKS\n\\\\\n'
        self.dw_page_name_column = 'Company'
        self.root_namespace = 'companies:'
        self.company_group = company_group  # (str) use this to differentiate between FTSE companies and other
        self.dw_table_page = 'tables:employee_giving_schemes_' + self.company_group

    def construct_row(self, record):
        """
        Construct a row for the ftse companies table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """

        # include only rows where the relevant group option appears
        if record['fields']['Company group'] != self.company_group:
            return ''

        company_name = record['fields']['Company']
        company_page_name = company_name.translate(punctuation_translator)
        company_dw_table_page = '[[companies:{}|{}]]'.format(company_page_name, company_name)

        sector = record['fields'].get('Sector', '')

        if 'Donation Matching' not in record['fields']:
            donation = ""
        else:
            donation = "X"

        if 'Payroll Giving' not in record['fields']:
            payroll = ""
        else:
            payroll = "X"

        # possibly merge the 'details' rows if it improves table format
        details_match = record['fields'].get('Details: Matching', '').replace('\n', ' \\\\ ')
        details_payroll = record['fields'].get('Details: Payroll giving', '').replace('\n', ' \\\\ ')
        details_other = record['fields'].get('Details: Other', '').replace('\n', ' \\\\ ')

        endorsed = record['fields'].get('Endorsed charity(s)', [''])
        outcomes = record['fields'].get('Outcomes', '')
        benefit = record['fields'].get('Total max EA-benefit', '')

        if 'Reference' in record['fields'] and 'Reference link' in record['fields']:
            ref_text = re.sub('\[(.*)\]', '', record['fields']['Reference']).rstrip()
            ref_url = record['fields']['Reference link']
            ref = '[[{}|{}]]'.format(ref_url, ref_text)
        else:
            ref = ''

        row = "| " + company_dw_table_page + " | " + sector + " | " + \
              donation + " | " + payroll + " | " + details_match + " | " + \
              str(benefit) + " | " + details_payroll + " | " + details_other + " | " + \
              ', '.join(endorsed) + " | " + outcomes + " | " + ref + " |\n"

        return row

    def create_page(self, record):
        """
        Construct a page for each paper.
        :param record: a single record from the Airtable
        :return: a formatted page
        """

        company_name = record['fields']['Company']
        sector = record['fields'].get('Sector', '')

        if 'Donation Matching' not in record['fields']:
            donation = ""
        else:
            donation = "yes"

        if 'Payroll Giving' not in record['fields']:
            payroll = ""
        else:
            payroll = "yes"

        if 'Pays PG fees' not in record['fields']:
            fees = ""
        else:
            fees = "yes. This field needs more research."

        provider = record['fields'].get('PG: provider name', '')

        # possibly merge the 'details' rows if it improves table format
        details_match = record['fields'].get('Details: Matching', '')
        details_payroll = record['fields'].get('Details: Payroll giving', '')
        details_other = record['fields'].get('Details: Other', '')

        endorsed = record['fields'].get('Endorsed charity(s)', [''])
        outcomes = record['fields'].get('Outcomes', '')
        benefit = record['fields'].get('Total max EA-benefit', '')

        if 'Reference' in record['fields'] and 'Reference link' in record['fields']:
            ref_text = re.sub('\[(.*)\]', '', record['fields']['Reference']).rstrip()
            ref_url = record['fields']['Reference link']
            ref = '[[{}|{}]]'.format(ref_url, ref_text)
        else:
            ref = ''

        sources = [ref]

        if 'Other links' in record['fields']:
            sources.extend(record['fields']['Other links'].split(";"))
            sources = [s.strip() for s in sources]

        if len(sources) > 0:
            source_items = '\n\n  * ' + '\n\n  * '.join(filter(None, sources)) + '\n'
        else:
            source_items = ''

        replacements = ('COMPANY', company_name), ('SECTOR', sector), ('MATCH', donation), \
                       ('PAYROLL', payroll), ('FEES', fees), \
                       ('PROVIDER', provider), ('ENDORSED', ', '.join(endorsed)), \
                       ('MATCH_DETAILS', details_match), ('BENEFIT', str(benefit)), \
                       ('PAYROLL_DETAILS', details_payroll), \
                       ('OTHER_DETAILS', details_other), \
                       ('OUTCOMES', outcomes), ('LINKS', source_items)
        paper_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.dw_page_template)
        return paper_page

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
        self.header = "\n^ Reference ^ Title ^ Type of evidence ^ Discussion ^ Tools ^ Link ^\n"
        self.linked_pages = True
        self.dw_page_template = '====PAPERTITLE====\n\n' \
                                'REFERENCE\n\n' \
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
        # TODO incorporate illustration when available Shang2009
        self.dw_page_name_column = 'Title'
        self.root_namespace = 'papers:'
        # TODO bottom tabular
        """ At the bottom of the page there should be some expandable table with a header
        'Meta-analysis and evaluation content' """

    def construct_row(self, record):
        """
        Construct a row for papers table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        paper_name = record['fields']['parencite']
        title = record['fields'].get('Title', '')

        paper_page_name = title.translate(punctuation_translator)
        paper_dw_table_page = '[[papers:{}|{}]]'.format(paper_page_name, paper_name)

        discussion = record['fields'].get('Discussion/findings', '')
        discussion = discussion.replace('\n', ' ').replace('\r', '')

        tool_ids = record['fields'].get('tools', '')
        related_tools = []
        if len(tool_ids) > 0:
            for tool_id in record['fields']['tools']:
                tool_name = self.airtable.get(tool_id)['fields'].get('Tool name', '')
                if tool_name == '':
                    pass
                else:
                    tool_page_name = tool_name.translate(punctuation_translator)
                    tool_dw_table_page = '[[tools:{}|{}]]'.format(tool_page_name, tool_name)
                    related_tools.append(tool_dw_table_page)

        evidence = record['fields'].get('Type of evidence', [''])

        if 'URL' not in record['fields']:
            link = ''
        else:
            link = '[[{}|{}]]'.format(record['fields']['URL'], 'Full text')

        row = "| " + paper_dw_table_page + " | " + title + " | " + \
              evidence[0] + " | " + discussion + " | " + ', '.join(related_tools) + " | " + link + " |\n"

        return row

    def create_page(self, record):
        """
        Construct a page for each paper.
        :param record: a single record from the Airtable
        :return: a formatted page
        """

        title = record['fields']['Title']
        reference = format_citation(record)

        evidence = record['fields'].get('Type of evidence', [''])
        keywords = ', '.join(record['fields'].get('keywords', ['']))
        charities = ', '.join(record['fields'].get('Charity-target', ['']))
        donors = ', '.join(record['fields'].get('Donor population', ['']))
        discipline = ', '.join(record['fields'].get('Discipline/field', ['']))

        tool_ids = record['fields'].get('tools', '')
        related_tools = []
        if len(tool_ids) > 0:
            for tool_id in record['fields']['tools']:
                tool_name = self.airtable.get(tool_id)['fields'].get('Tool name', '')
                if tool_name == '':
                    pass
                else:
                    tool_page_name = tool_name.translate(punctuation_translator)
                    tool_dw_table_page = '[[tools:{}|{}]]'.format(tool_page_name, tool_name)
                    related_tools.append(tool_dw_table_page)

        summary = record['fields'].get('Wiki-notes', '')
        discussion = record['fields'].get('Discussion/findings', '')
        evaluation = record['fields'].get('Evaluation', '')

        creators = get_linked_items(self.airtable, 'Added by', record, 'Name, Institution')
        # # this is currently not a link to persons
        # evaluators = get_linked_items(self.airtable, 'Discussion/evaluation by', record, 'Name, Institution')
        theories = get_linked_items(self.airtable, 'Theories', record, 'Theory')
        critiques = get_linked_items(self.airtable, 'critiques', record, 'Name')

        replacements = ('PAPERTITLE', title), ('REFERENCE', reference), ('KEYWORDS', keywords), \
                       ('DISCIPLINE', discipline), ('EVIDENCE', evidence[0]), \
                       ('TOOLS', ', '.join(related_tools)), ('THEORIES', theories), \
                       ('CRITIQUES', critiques), ('TARGETS', charities), ('DONORS', donors), \
                       ('SUMMARY', summary), ('DISCUSSION', discussion), \
                       ('EVALUATION', evaluation), ('META', self.make_meta(record)), \
                       ('CREATORS', creators)  # , ('EVALUATORS', evaluators)
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
        self.airtable.update(record['id'], {'Authors': authors})

        year = bib_data.entries[k].fields.get('year', '')
        self.airtable.update(record['id'], {'Year': year})

        title = bib_data.entries[k].fields['title']
        self.airtable.update(record['id'], {'Title': title})

        if bib_type == "article":
            journal = bib_data.entries[k].fields['journal']
            self.airtable.update(record['id'], {'Journal': journal})
            volume = bib_data.entries[k].fields.get('volume', '')
            self.airtable.update(record['id'], {'Vol': volume})
            number = bib_data.entries[k].fields.get('number', '')
            self.airtable.update(record['id'], {'Num': number})
            pages = bib_data.entries[k].fields.get('pages', '')
            self.airtable.update(record['id'], {'Pages': pages})

        elif bib_type == "incollection":
            book = bib_data.entries[k].fields['booktitle']
            book = book.lower().title()
            self.airtable.update(record['id'], {'Book_title': book})
            pages = bib_data.entries[k].fields.get('pages', '')
            self.airtable.update(record['id'], {'Pages': pages})

        elif bib_type == "techreport":
            institution = bib_data.entries[k].fields.get('institution', '')
            self.airtable.update(record['id'], {'Institution': institution})

        # nothing to add for book and misc

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

    @staticmethod
    def make_meta(record):
        numcit = str(record['fields'].get('num_citations', ''))
        data = ', '.join(record['fields'].get('Link to raw data', ''))  # link?
        peerrev = insert_check('Peer-reviewed pub?', record)
        rating = str(record['fields'].get('Journal rating (1-5)', ''))
        replic_link = ', '.join(record['fields'].get('Exact replications link?', ''))  # link?
        replic_res = insert_check('Replication success?', record)
        prereg = insert_check('Preregistered?', record)
        verified = insert_check('Verified collection?', record)
        aware = insert_check('Participants aware?', record)
        demog = ', '.join(record['fields'].get('Sample demog?', ''))
        design = insert_check('Between-subject design?', record)
        compar = insert_check('Simple_comparison?', record)
        sampsize = str(record['fields'].get('Sample size', ''))
        share = str(record['fields'].get('Share treated', ''))
        components = ', '.join(record['fields'].get('Key components of ask', ''))
        treat = record['fields'].get('Main treatment', '')
        mean_don = str(record['fields'].get('Mean don (usd-2018); control group', ''))
        sd_don = str(record['fields'].get('SD: don', ''))
        endow_descr = record['fields'].get('Endowment_description', '')
        endow_usd = record['fields'].get('Endowment (usd-2018)', '')
        curr = record['fields'].get('Currency', '')
        year = str(record['fields'].get('year_run', ''))
        convert = str(record['fields'].get('conversion rate', ''))
        eff_orig = str(record['fields'].get('Effect-size-original-units', ''))
        eff_usd = str(record['fields'].get('Effect size (USD-2018)', ''))
        se_eff = str(record['fields'].get('SE of effect size', ''))
        se_calc = str(record['fields'].get('SE calc method', ''))
        eff_share = str(record['fields'].get('Effect size (Share of mean donation)', ''))
        mean_inc = str(record['fields'].get('Mean incidence', ''))
        eff_inc = str(record['fields'].get('Effect size (incidence)', ''))
        pval = str(record['fields'].get('Headline p-value', ''))
        pval_descr = record['fields'].get('Describe headline p-val', '')

        meta_template = '<button collapse="meta">Meta-analysis data</button><collapse id="meta" collapsed="true"><well>'\
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

        vars = [year, data, peerrev, rating, numcit, replic_link, replic_res,
                prereg, verified, aware, demog, design, compar, sampsize, share, components, treat,
                mean_don, sd_don, endow_usd, endow_descr, curr, convert, eff_orig, eff_usd, se_eff,
                se_calc, eff_share, mean_inc, eff_inc, pval, pval_descr]
        keys = ['R0' + str(i) for i in range(1, 10)] + ['R' + str(i) for i in range(10, 33)]

        replacements = tuple(zip(keys, vars))
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
        self.header = "\n^ Reference ^ Study year ^ Data link ^ Peer reviewed ^ Journal rating ^ " \
                      "Citations ^ Replications ^ Replication success ^ Pre-registered ^" \
                      "Verified ^ Participants aware ^ Demographics ^ Design ^" \
                      "Simple comparison ^ Sample size ^ Share treated ^ Key components ^" \
                      "Main treatment ^ Mean donation ^ SD donation ^ Endowment amount ^" \
                      "Endowment description ^ Currency ^ Conversion rate ^" \
                      "Effect size original ^ Effect size USD ^ SE effect size ^" \
                      "SE calculation ^ Effect size share ^ Mean incidence ^" \
                      "Effect size incidence ^ Headline p-val ^ P-val description" \
                      "^\n"
        self.linked_pages = False

    def construct_row(self, record):
        """
        Construct a row for papers table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        paper_name = record['fields']['parencite']
        title = record['fields'].get('Title', '')
        paper_page_name = title.translate(punctuation_translator)
        # create a DW link to paper page
        paper_dw_table_page = '[[papers:{}|{}]]'.format(paper_page_name, paper_name)

        numcit = str(record['fields'].get('num_citations', ''))
        data = ', '.join(record['fields'].get('Link to raw data', ''))  # link?
        peerrev = insert_check('Peer-reviewed pub?', record)
        rating = str(record['fields'].get('Journal rating (1-5)', ''))
        replic_link = ', '.join(record['fields'].get('Exact replications link?', ''))  # link?
        replic_res = insert_check('Replication success?', record)
        prereg = insert_check('Preregistered?', record)
        verified = insert_check('Verified collection?', record)
        aware = insert_check('Participants aware?', record)
        demog = ', '.join(record['fields'].get('Sample demog?', ''))
        design = insert_check('Between-subject design?', record)
        compar = insert_check('Simple_comparison?', record)
        sampsize = str(record['fields'].get('Sample size', ''))
        share = str(record['fields'].get('Share treated', ''))
        components = ', '.join(record['fields'].get('Key components of ask', ''))
        treat = record['fields'].get('Main treatment', '')
        mean_don = str(record['fields'].get('Mean don (usd-2018); control group', ''))
        sd_don = str(record['fields'].get('SD: don', ''))
        endow_descr = record['fields'].get('Endowment_description', '')
        endow_usd = record['fields'].get('Endowment (usd-2018)', '')
        curr = record['fields'].get('Currency', '')
        year = str(record['fields'].get('year_run', ''))
        convert = str(record['fields'].get('conversion rate', ''))
        eff_orig = str(record['fields'].get('Effect-size-original-units', ''))
        eff_usd = str(record['fields'].get('Effect size (USD-2018)', ''))
        se_eff = str(record['fields'].get('SE of effect size', ''))
        se_calc = str(record['fields'].get('SE calc method', ''))
        eff_share = str(record['fields'].get('Effect size (Share of mean donation)', ''))
        mean_inc = str(record['fields'].get('Mean incidence', ''))
        eff_inc = str(record['fields'].get('Effect size (incidence)', ''))
        pval = str(record['fields'].get('Headline p-value', ''))
        pval_descr = record['fields'].get('Describe headline p-val', '')

        row = "| " + " | ".join([paper_dw_table_page, year, data, peerrev, rating, numcit, replic_link, replic_res,
                                 prereg, verified, aware, demog, design, compar, sampsize, share,
                                 components, treat, mean_don, sd_don, endow_usd, endow_descr,
                                 curr, convert, eff_orig, eff_usd, se_eff, se_calc, eff_share,
                                 mean_inc, eff_inc, pval, pval_descr]) + " |\n"

        return row


class CategoryTable(Table):
    def __init__(self, wiki, base_name, table_name, user_key):
        super(CategoryTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:tool_categories'
        self.included_in = 'tools:tool_categories'
        self.main_column = '(Sub)Category or theme'
        self.header = "\n^ Category ^ Description ^\n"
        self.linked_pages = False

    def construct_row(self, record):
        """
        Construct a row for the tools table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        cat_name = record['fields']['(Sub)Category or theme']
        description = record['fields']['Description'].rstrip()

        row = "| " + cat_name + " | " + description + " |\n"
        return row

    def format_table(self):
        table_content = '<datatables dom="t" page-length="100">\n'
        # initialize table content with the header
        table_content += self.header
        # construct the rows for all available records using the corresponding constructor function
        for record in self.records:
            # we only consider records in which the main column is not empty
            if (self.main_column is not None) and (self.main_column not in record['fields']):
                pass
            else:
                table_content += self.construct_row(record)
        table_content += '</datatables>\n'
        return table_content


class ExperimentTable(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(ExperimentTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:data_experiments'
        self.included_in = 'iifwiki:dataexperiments'
        self.main_column = 'Experiment'
        self.header = "\n^ Experiment ^ N ^ Endowment ^ Share donating ^ Share donated ^ Mean donation ^\
                            SD ^ SD/Mean ^ Effect Size ^ References ^\n"
        self.linked_pages = False

    def construct_row(self, record):
        """
        Construct a row for the charity experiments table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        experiment_name = record['fields']['Experiment']
        n = record['fields'].get('N ', '')
        endowment = record['fields'].get('Endowment', '')
        share_donating = record['fields'].get('Share donating', '')
        share_donated = record['fields'].get('Share donated', '')
        exp_mean = record['fields'].get('Mean donation', '')
        exp_sd = record['fields'].get('SD', '')
        sd_mean = record['fields'].get('SD/Mean', '')
        effect = record['fields'].get('Effect Size %', '')
        ref = record['fields'].get('References', '')

        row = "| " + experiment_name + " | " + n + " | " + endowment + " | " +\
              share_donating + " | " + share_donated + " | " + exp_mean + " | " +\
              exp_sd + " | " + sd_mean + " | " + effect + " | " + ref + " |\n"
        return row


class ExperienceTable(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(ExperienceTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:experiences_of_workplace_activists'
        self.included_in = 'iifwiki:experiences_of_workplace_activists'
        self.main_column = 'Name'
        self.header = "\n^ Name ^ Organisation ^ Employees ^ " \
                      "Charity ^ Description ^ Participants ^ Raised ^ Results ^\n"
        self.linked_pages = False

    def construct_row(self, record):
        """
        Construct a row for fundraising experiences table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        person_name_role = record['fields']['Name'] + ", " + record['fields'].get('Role', '')
        organisation = record['fields'].get('Organisation', '') + ", " + record['fields'].get('Organisation type', '')
        num_employees = record['fields'].get('Number of employees', '')
        # experience_type = record['fields'].get('Experience type', '')
        charity = record['fields'].get('Charity', '')
        description = record['fields'].get('Event description', '')
        num_participants = record['fields'].get('Number of participants', '')
        raised = record['fields'].get('Amount raised', '')

        results = "**Choice motivation**: " + record['fields'].get('Choice motivation', '') + "\\\\ " +\
                  "**Communication channel**: " + record['fields'].get('Communication channel', '') + "\\\\ " +\
                  "**Main arguments**: " + record['fields'].get('Main arguments', '') + "\\\\ " +\
                  "**Problems faced**: " + record['fields'].get('Problems faced', '') + "\\\\ " +\
                  "**Evaluation**: " + record['fields'].get('Evaluation', '') + "\\\\ " +\
                  "**Additional information**: " + record['fields'].get('Comments', '')

        row = "| " + " | ".join([person_name_role, organisation, str(num_employees), charity,
                                description, str(num_participants), raised, results]) + " |\n"
        return row


class ThirdSectorTable(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(ThirdSectorTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:third_sector_infrastructure_details'
        self.included_in = 'iifwiki:third_sector_infrastructure_details'
        self.main_column = 'Name'
        self.header = "\n^ Name ^ Whom does it help? ^ Role ^ Example activity ^ " \
                      "Size ^ Established ^ CEO/Chairman ^\n"
        self.linked_pages = False

    def construct_row(self, record):
        """
        Construct a row for third-sector organisations table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        name = record['fields']['Name']
        link = record['fields'].get('Link', '')
        if link != '':
            name_link = '[[{}|{}]]'.format(link, name)
        else:
            name_link = name

        target = record['fields'].get('Target', '')
        role = record['fields'].get('Role', '')
        activity = record['fields'].get('Example activity', '')
        size = record['fields'].get('Size', '')
        established = record['fields'].get('Established', '')
        ceo = record['fields'].get('CEO/Chairman', '')

        row = "| " + " | ".join([name_link, target, role, activity, size, established, ceo]) + " |\n"
        return row


class EffectiveCharities(Table):

    def __init__(self, wiki, base_name, table_name, user_key):
        super(EffectiveCharities, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:effective_charities'
        self.included_in = 'iifwiki:effective_charities'
        self.main_column = 'Name'
        self.header = "\n^ Charity Name ^ Registration Number ^ Just Giving ID ^ Cause area ^ " \
                      "Rater ^ EAF ^ GiveWell Top'17 ^ GiveWell Standout'17 ^ Life You Can Save ^ ACE ^\n"
        self.linked_pages = False

    def construct_row(self, record):
        """
        Construct a row for third-sector organisations table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        name = record['fields']['Name']
        link = record['fields'].get('Link', '')
        if link != '':
            name_link = '[[{}|{}]]'.format(link, name)
        else:
            name_link = name

        target = record['fields'].get('Target', '')
        role = record['fields'].get('Role', '')
        activity = record['fields'].get('Example activity', '')
        size = record['fields'].get('Size', '')
        established = record['fields'].get('Established', '')
        ceo = record['fields'].get('CEO/Chairman', '')

        row = "| " + " | ".join([name_link, target, role, activity, size, established, ceo]) + " |\n"
        return row
