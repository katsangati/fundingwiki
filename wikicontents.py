"""
This is a script for manipulating Airtable data and redirecting it to the Innovations in Fundraising DokuWiki
(or its local test version). It defines classes that represent Airtable tables that feed DW content
(as tables or pages).
"""
import airtable as at
from functools import reduce
import string
import re
import time


# define a punctuation stripper for using later in pagename constructors
punctuation_translator = str.maketrans('', '', string.punctuation)


def get_linked_items(airtable, column_name, record, linked_column_name):
    """Fetch linked item names from a given column in a given record.

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


class Table:
    """
    Top-level Table class that provides a blueprint for all more specific tables and instantiates
    common methods and methods with default parameters.
    """

    def __init__(self, wiki, base_name, table_name, user_key):
        self.wiki = wiki
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()

        # self.airtable = None
        # self.records = None
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
        row = "| "
        for key, value in record['fields'].items():
            row += repr(value)
            row += " | "
        row += " |\n"
        return row

    def format_table(self):
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
        """
        Construct a default page for a single record.
        :param record: a single record from the Airtable
        :return: a formatted page
        """
        page = ""
        for key, value in record['fields'].items():
            page += key.upper() + "\n\n"
            page += repr(value) + "\n"
            page += "\n"
        return page

    def format_pages(self, records):
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
        new_pages = self.format_pages(self.records)
        # this has to be done with a break of at least 5s
        for page in new_pages:
            self.wiki.pages.set(page, new_pages[page])
            time.sleep(5)


class ToolTable(Table):
    def __init__(self, wiki, base_name, table_name, user_key):
        super(ToolTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:tools'
        self.included_in = 'tools:tools'
        self.main_column = 'Tool name'
        self.header = "\n^ Tool name ^ Category ^ Description ^ Main findings ^ Key papers ^\n"
        self.linked_pages = True
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
        self.dw_page_name_column = 'Tool name'
        self.root_namespace = 'tools:'

    def construct_row(self, record):
        """
        Construct a row for the tools table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        if 'Wiki?' in record['fields']:
            tool_name = record['fields']['Tool name']
            tool_page_name = tool_name.translate(punctuation_translator)
            tool_dw_table_page = '[[tools:{}|{}]]'.format(tool_page_name, tool_name)

            categories = record['fields'].get('Category', [""])
            description = record['fields'].get('Description', "")
            description = description.replace('\n', ' ').replace('\r', '')
            findings = record['fields'].get('Findings summarized', "")
            findings = findings.replace('\n', ' ').replace('\r', '')

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

            paper_ids = record['fields'].get('key_papers', '')
            key_papers = []
            if len(paper_ids) > 0:
                for paper_id in record['fields']['key_papers']:
                    paper_name = self.airtable.get(paper_id)['fields'].get('parencite', '')
                    title = self.airtable.get(paper_id)['fields'].get('Title', '')
                    if paper_name == '' or title == '':
                        pass
                    else:
                        paper_page_name = title.translate(punctuation_translator)
                        paper_dw_table_page = '[[papers:{}|{}]]'.format(paper_page_name, paper_name)
                        key_papers.append(paper_dw_table_page)

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
        tn = record['fields']['Tool name']
        alt_tn = ', '.join(record['fields'].get('AKA', ''))
        tool_var = record['fields'].get('Tool variation', '')

        categories = get_linked_items(self.airtable, 'Category', record, '(Sub)Category or theme')
        sub_categories = get_linked_items(self.airtable, 'subcat', record, '(Sub)Category or theme')
        theories = get_linked_items(self.airtable, 'Theories', record, 'Theory')
        cases = get_linked_items(self.airtable, 'Relevant use cases', record, 'Name')

        evid = record['fields'].get('Types of evidence', [""])
        evid_types = ', '.join(evid)

        evid_str = str(record['fields'].get('Evidence strength', ''))
        description = record['fields'].get('Description', "")
        summary = record['fields'].get('Findings summarized', "").rstrip()
        discuss = record['fields'].get('Full discussion', "").rstrip()

        relevance = record['fields'].get('Relevance to EA charities', [""])[0].rstrip()
        preval = record['fields'].get('Prevalence', "")

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
                    fulltext_link = '[[{}|Full text]]'.format(p_url)
                    paper_page += ', ' + fulltext_link
                papers.append(paper_page)

            if len(papers) > 0:
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

        if 'Contributors' in record['fields']:
            contribs = record['fields']['Contributors']
            contrib_names = [self.airtable.get(contrib_id)['fields']['Name, Institution'] for
                             contrib_id in contribs]
            contrib = ', '.join(contrib_names)
        else:
            contrib = ''

        replacements = ('TOOLNAME', tn), ('DESCRIPTION', description), ('AKA', alt_tn), ('TOOLVAR', tool_var),\
                       ('CATEGORY', categories), ('SUBCATEGORY', sub_categories), \
                       ('THEORIES', theories), ('EVIDENCE', evid_types), ('STRENGTH', evid_str),\
                       ('FINDINGS', summary), ('DISCUSSION', discuss),\
                       ('RELEVANCE', relevance), ('CASES', cases), ('PREVALENCE', preval),\
                       ('PAPERS', paper_items), ('PAPERS2', secondary_paper_items),\
                       ('CONTRIBUTOR', contrib)
        tool_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.dw_page_template)
        return tool_page

    def set_pages(self):
        relevant_records = []
        for record in self.records:
            if 'Wiki?' in record['fields']:
                relevant_records.append(record)
        new_pages = self.format_pages(relevant_records)
        # this has to be done with a break of at least 5s
        for page in new_pages:
            self.wiki.pages.set(page, new_pages[page])
            time.sleep(5)


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


class FtseTable(Table):
    def __init__(self, wiki, base_name, table_name, user_key):
        super(FtseTable, self).__init__(wiki, base_name, table_name, user_key)
        self.airtable = at.Airtable(base_name, table_name, user_key)
        self.records = self.airtable.get_all()
        self.dw_table_page = 'tables:employee_giving_schemes'
        self.included_in = 'iifwiki:employee_giving_schemes'
        self.main_column = 'Company [(cite:LSE)]'
        self.header = "\n^ Company ^ Sector ^ Donation Matching ^ Payroll Giving Provider ^ Details ^ " \
                      "Outcomes ^ Reference ^\n"
        self.linked_pages = False

    def construct_row(self, record):
        """
        Construct a row for the ftse companies table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        company_name = record['fields']['Company [(cite:LSE)]']

        industry = record['fields'].get('industry', '')
        details = record['fields'].get('Details', '')
        outcomes = record['fields'].get('Outcomes', '')

        if 'Donation Matching' not in record['fields']:
            donation = ""
        else:
            donation = "X"

        if 'Payroll Giving Provider' not in record['fields']:
            payroll = ""
        else:
            payroll = "X"

        if 'Reference' in record['fields'] and 'web link' in record['fields']:
            ref_text = re.sub('\[(.*)\]', '', record['fields']['Reference']).rstrip()
            ref_url = record['fields']['web link']
            ref = '[[{}|{}]]'.format(ref_url, ref_text)
        else:
            ref = ''

        row = "| " + company_name + " | " + industry + " | " +\
              donation + " | " + payroll + " | " + details + " | " +\
              outcomes + " | " + ref + " |\n"
        return row


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
                                'This paper has been added by CREATORS'  # and evaluated by EVALUATORS'
        # TODO incorporate illustration when available
        self.dw_page_name_column = 'Title'
        self.root_namespace = 'papers:'
        # TODO bottom tabular
        """
        At the bottom of the page there should be some expandable table with a header
        'Meta-analysis and evaluation content'
        that will draw from a meta-analysis table
        The following columns are relevant:
        peer-reviewed - rating - paper citations - replications - repl success - pre-registered - verified -
        participants aware - sample demo - design - link to raw data - simple comparison - sample size -
        share treated - key components - main treatment - mean don - sd don - endowment - curr -
        year_run - conversion rate - Effect size original units - Effect size(USD - 2018) -
        SE of effect size - SE calc method - Effect size(Share of mean donation) - Mean incidence-
        Effect size(incidence) - Headline p - value
        """

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
        authors = record['fields'].get('Authors', '')
        journal = record['fields'].get('Journal', '')
        pages = record['fields'].get('Pages', '')
        year = record['fields'].get('Year', '')
        link = record['fields'].get('URL', '')
        # doi = record['fields'].get('doi', '') none of this is filled or works yet
        if link == '':
            reference = '{}, ({}). {}. {}, {}.'.format(authors, year, title, journal, pages)
        else:
            reference = '{}, ({}). [[{}|{}]]. {}, {}.'.format(authors, year, link, title, journal, pages)

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
                       ('EVALUATION', evaluation), ('CREATORS', creators)  # , ('EVALUATORS', evaluators)
        paper_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.dw_page_template)
        return paper_page

