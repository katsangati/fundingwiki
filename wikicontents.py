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


class Table:

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
        self.main_column = 'Toolname'
        self.header = "\n^ Tool name ^ Category ^ Description ^ Key papers ^ Theories ^\n"
        self.linked_pages = True
        self.dw_page_template = '==== TOOLNAME ====\n\n**Category**: CATEGORY \n\n**Sub-category**: SUBCATEGORY\n\n' \
                                '**Relevant theories**: THEORIES\n\n**Type of evidence**: EVIDENCE\n\\\\\n\\\\\n' \
                                '=== Main findings ===\n\nFINDINGS\n\\\\\n\\\\\n=== Key papers ===PAPERS'
        self.dw_page_name_column = 'Toolname'
        self.root_namespace = 'tools:'

    def construct_row(self, record):
        """
        Construct a row for the tools table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        tool_name = record['fields']['Toolname']
        tool_page_name = tool_name.translate(punctuation_translator)
        tool_dw_table_page = '[[tools:{}|{}]]'.format(tool_page_name, tool_name)

        category = record['fields'].get('Category', [""])
        findings = record['fields'].get('Findings summarized', [""])

        if 'Theories' not in record['fields']:
            theory_names = ''
        else:
            theory_names = [self.airtable.get(theory_id)['fields']['Theory'] for
                            theory_id in record['fields']['Theories']]

        key_papers = []
        for paper_id in record['fields']['Keypapers']:
            paper_name = self.airtable.get(paper_id)['fields']['parencite']
            title = self.airtable.get(paper_id)['fields']['Title']
            paper_page_name = title.translate(punctuation_translator)
            paper_dw_table_page = '[[papers:{}|{}]]'.format(paper_page_name, paper_name)
            key_papers.append(paper_dw_table_page)

        row = "| " + tool_dw_table_page + " | " + category[0] + " | " +\
            findings[0].rstrip() + " | " + '; '.join(key_papers) + " | " + ', '.join(theory_names) + " |\n"
        return row

    def create_page(self, record):
        """
        Construct a page for each tool.
        :param record: a single record from the Airtable
        :return: a formatted page
        """
        tn = record['fields']['Toolname']

        if 'Category' not in record['fields']:
            cat = ""
        else:
            cat = record['fields']['Category'][0]

        if 'Subcategory' not in record['fields']:
            subcat = ""
        else:
            subcat = record['fields']['Subcategory'][0]

        if 'Theories' not in record['fields']:
            theory_names = ''
        else:
            theory_names = ', '.join([self.airtable.get(theory_id)['fields']['Theory'] for
                                      theory_id in record['fields']['Theories']])

        if 'Types of evidence' not in record['fields']:
            evid = ''
        else:
            evid = record['fields']['Types of evidence'][0]

        if 'Findings summarized' not in record['fields']:
            summary = record['fields']['Findings summarized'] = [""]
        else:
            summary = record['fields']['Findings summarized'][0].rstrip()

        papers = []
        for paper_id in record['fields']['Keypapers']:
            p_title = self.airtable.get(paper_id)['fields']['Title']
            p_url = self.airtable.get(paper_id)['fields']['URL']
            papers.append('[[' + p_url + ' | ' + p_title + ']]')

        paper_items = '\n\n * ' + '\n\n * '.join(papers) + '\n'

        replacements = ('TOOLNAME', tn), ('CATEGORY', cat), ('SUBCATEGORY', subcat), \
                       ('THEORIES', theory_names), ('EVIDENCE', evid), ('FINDINGS', summary), \
                       ('PAPERS', paper_items)
        tool_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.dw_page_template)
        return tool_page


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
        self.header = "\n^ Reference ^ Type of evidence ^ Sample size ^ Effect size ^ Link ^\n"
        self.linked_pages = True
        self.dw_page_template = '====PAPERTITLE====\n\n<div class="full_reference">REFERENCE</div>\n\n' \
                                '<div class="evidence_type">**Type of evidence**: EVIDENCE</div>\n\n' \
                                '<div class="paper_keywords">**Keywords**: KEYWORDS</div>\n\\\\\n' \
                                '===Paper summary===\n\n<div class="paper_summary">SUMMARY</div>\n\\\\\n' \
                                '===Discussion===\n\n<div class="paper_discussion">DISCUSSION</div>'
        self.dw_page_name_column = 'Title'
        self.root_namespace = 'papers:'

    def construct_row(self, record):
        """
        Construct a row for papers table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        paper_name = record['fields']['parencite']
        title = record['fields']['Title']

        paper_page_name = title.translate(punctuation_translator)
        paper_dw_table_page = '[[papers:{}|{}]]'.format(paper_page_name, paper_name)

        evidence = record['fields'].get('Type of evidence', [''])
        size = record['fields'].get('Sample size', '')
        effect = record['fields'].get('Effect size (Share of mean donation)', '')

        if 'URL' not in record['fields']:
            link = ''
        else:
            link = '[[{}|{}]]'.format(record['fields']['URL'], 'Full text')

        row = "| " + " | ".join([paper_dw_table_page, evidence[0], str(size), str(effect), link]) + " |\n"
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
        if link == '':
            reference = '{}, ({}). {}. {}, {}.'.format(authors, year, title, journal, pages)
        else:
            reference = '{}, ({}). [[{}|{}]]. {}, {}.'.format(authors, year, link, title, journal, pages)

        evidence = record['fields'].get('Type of evidence', [''])
        keywords = ', '.join(record['fields'].get('keywords', ['']))

        summary = record['fields'].get('Wiki-notes', '')
        discussion = record['fields'].get('Discussion/evaluation by', '')

        replacements = ('PAPERTITLE', title), ('REFERENCE', reference), ('EVIDENCE', evidence[0]), \
                       ('KEYWORDS', keywords), ('SUMMARY', summary), ('DISCUSSION', discussion)
        paper_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.dw_page_template)
        return paper_page
