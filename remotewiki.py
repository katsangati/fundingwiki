"""
This is a script that defines the main classes for manipulating Airtable data and
redirecting it to the Innovations in Fundraising DokuWiki (or its local test version).
"""
import airtable as at
import os
from functools import reduce
import string
import re
import time


# define a punctuation stripper for using later in pagename constructors
punctuation_translator = str.maketrans('', '', string.punctuation)
user_key = os.environ['AIRTABLE_API_KEY']

"""
Define classes that represent DW tables fed by Airtable content
"""


class Table:
    def __init__(self, wiki):
        self.wiki = wiki
        self.base_name = None
        self.table_name = None
        self.records = None
        self.page_link = None
        self.div_id = None
        self.main_column = None
        self.header = None

    def format_table(self, wiki_page):
        start_tag = '<div id="{}">'.format(self.div_id)
        end_tag = '</div>'
        start_index = wiki_page.find(start_tag) + len(start_tag)
        end_index = wiki_page.find(end_tag)

        # placement_tag = 'TABLEHERE'
        # start_index = page_content.find(placement_tag)
        # end_index = start_index + len(placement_tag)

        # initialize table content with the header
        table_content = self.header
        # construct the rows for all available records using the corresponding constructor function
        for record in self.records:
            # we only consider records in which the main column is not empty
            if self.main_column not in record['fields']:
                pass
            else:
                table_content += self.construct_row(record)

        # combine the table with the rest of the page
        new_page = wiki_page[:start_index] + table_content + wiki_page[end_index:]
        return new_page

    def set_table_page(self):
        wiki_page = self.wiki.pages.get(self.page_link)
        new_page = self.format_table(wiki_page)
        self.wiki.pages.set(self.page_link, new_page)

    def construct_row(self, record):
        row = record
        return row

    def reload_records(self):
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()


class ToolTable(Table):
    def __init__(self, wiki):
        super(ToolTable, self).__init__(wiki)
        self.base_name = 'appBzOSifwBqSuVfH'
        self.table_name = 'tools_public_sample'
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()
        self.linked_tables = {'theories': at.Airtable(self.base_name, self.table_name, user_key),
                              'papers': at.Airtable(self.base_name, self.table_name, user_key)}
        self.page_link = 'tools:tools'
        self.div_id = 'tool_table'
        self.main_column = 'Toolname'
        self.header = "\n^ Tool name ^ Category ^ Description ^ Key papers ^ Theories ^\n"

    def construct_row(self, record):
        """
        Construct a row for the tools table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        tool_name = record['fields']['Toolname']
        tool_page_name = tool_name.translate(punctuation_translator)
        tool_page_link = '[[tools:{}|{}]]'.format(tool_page_name, tool_name)

        category = record['fields'].get('Category', [""])
        findings = record['fields'].get('Findings summarized', [""])

        if 'Theories' not in record['fields']:
            theory_names = ''
        else:
            theory_names = [self.linked_tables['theories'].get(theory_id)['fields']['Theory'] for
                            theory_id in record['fields']['Theories']]

        key_papers = []
        for paper_id in record['fields']['Keypapers']:
            paper_name = self.linked_tables['papers'].get(paper_id)['fields']['parencite']
            title = self.linked_tables['papers'].get(paper_id)['fields']['Title']
            paper_page_name = title.translate(punctuation_translator)
            paper_page_link = '[[papers:{}|{}]]'.format(paper_page_name, paper_name)
            key_papers.append(paper_page_link)

        row = "| " + tool_page_link + " | " + category[0] + " | " +\
            findings[0].rstrip() + " | " + '; '.join(key_papers) + " | " + ', '.join(theory_names) + " |\n"
        return row


class FtseTable(Table):
    def __init__(self, wiki):
        super(FtseTable, self).__init__(wiki)
        self.base_name = 'apprleNrkR7dTtW60'
        self.table_name = 'ftse100+givingpolicies'
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()
        self.page_link = 'iifwiki:employee_giving_schemes'
        self.div_id = 'ftse_table'
        self.main_column = 'Company [(cite:LSE)]'
        self.header = "\n^ Company ^ Sector ^ Donation Matching ^ Payroll Giving Provider ^ Details ^ " \
                      "Outcomes ^ Reference ^\n"

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
    def __init__(self, wiki):
        super(ExperimentTable, self).__init__(wiki)
        self.base_name = 'appBzOSifwBqSuVfH'
        self.table_name = 'Charity experiments'
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()
        self.page_link = 'iifwiki:dataexperiments'
        self.div_id = 'experiments_table'
        self.main_column = 'Experiment'
        self.header = "\n^ Experiment ^ N ^ Endowment ^ Share donating ^ Share donated ^ Mean donation ^\
                            SD ^ SD/Mean ^ Effect Size ^ References ^\n"

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
    def __init__(self, wiki):
        super(ExperienceTable, self).__init__(wiki)
        self.base_name = 'appBzOSifwBqSuVfH'
        self.table_name = 'Experiences'
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()
        self.page_link = 'iifwiki:experiences_of_workplace_activists'
        self.div_id = 'experiences_table'
        self.main_column = 'Name'
        self.header = "\n^ Name ^ Organisation ^ Employees ^ " \
                      "Charity ^ Description ^ Participants ^ Raised ^ Results ^\n"

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
    def __init__(self, wiki):
        super(ThirdSectorTable, self).__init__(wiki)
        self.base_name = 'appBzOSifwBqSuVfH'
        self.table_name = 'Third sector'
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()
        self.page_link = 'iifwiki:third_sector_infrastructure_details'
        self.div_id = 'third_sector_table'
        self.main_column = 'Name'
        self.header = "\n^ Name ^ Whom does it help? ^ Role ^ Example activity ^ " \
                      "Size ^ Established ^ CEO/Chairman ^\n"

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
    def __init__(self, wiki):
        super(PapersTable, self).__init__(wiki)
        self.base_name = 'appBzOSifwBqSuVfH'
        self.table_name = 'papers_mass'
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()
        self.page_link = 'papers:papers'
        self.div_id = 'papers_table'
        self.main_column = 'parencite'
        self.header = "\n^ Reference ^ Type of evidence ^ Sample size ^ Effect size ^ Link ^\n"

    def construct_row(self, record):
        """
        Construct a row for papers table based on data delivered by Airtable.
        :param record: a single record from the Airtable
        :return: a formatted row for DW
        """
        paper_name = record['fields']['parencite']
        title = record['fields']['Title']

        paper_page_name = title.translate(punctuation_translator)
        paper_page_link = '[[papers:{}|{}]]'.format(paper_page_name, paper_name)

        evidence = record['fields'].get('Type of evidence', [''])
        size = record['fields'].get('Sample size', '')
        effect = record['fields'].get('Effect size (Share of mean donation)', '')

        if 'URL' not in record['fields']:
            link = ''
        else:
            link = '[[{}|{}]]'.format(record['fields']['URL'], 'Full text')

        row = "| " + " | ".join([paper_page_link, evidence[0], str(size), str(effect), link]) + " |\n"
        return row


"""
Define classes that represent pages fed by Airtable content
"""


class DokuWikiPage:
    def __init__(self, wiki):
        self.wiki = wiki
        self.page_template = None
        self.records = None
        self.main_column = None
        self.page_name_column = None
        self.root_namespace = None

    def create_page(self, record):
        return record + self.page_template

    def set_pages(self):
        page_names = []
        pages = []

        for record in self.records:
            if (self.main_column not in record['fields']) or (self.page_name_column not in record['fields']):
                pass
            else:
                page_name = record['fields'][self.page_name_column]
                clean_page_name = page_name.translate(punctuation_translator)
                full_page_name = self.root_namespace + clean_page_name
                page_names.append(full_page_name)
                page = self.create_page(record)
                pages.append(page)

        # this has to be done with a break of at least 5s
        n_pages = len(page_names)
        for i in range(n_pages):
            self.wiki.pages.set(page_names[i], pages[i])
            time.sleep(5)


class ToolPage(DokuWikiPage):
    def __init__(self, wiki):
        super(ToolPage, self).__init__(wiki)
        self.base_name = 'appBzOSifwBqSuVfH'
        self.table_name = 'tools_public_sample'
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()
        self.linked_tables = {'theories': at.Airtable(self.base_name, self.table_name, user_key),
                              'papers': at.Airtable(self.base_name, self.table_name, user_key)}
        self.page_template = '==== TOOLNAME ====\n\n**Category**: CATEGORY \n\n**Sub-category**: SUBCATEGORY\n\n' \
                             '**Relevant theories**: THEORIES\n\n**Type of evidence**: EVIDENCE\n\\\\\n\\\\\n' \
                             '=== Main findings ===\n\nFINDINGS\n\\\\\n\\\\\n=== Key papers ===PAPERS'
        self.main_column = 'Toolname'
        self.page_name_column = 'Toolname'
        self.root_namespace = 'tools:'

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
            theory_names = ', '.join([self.linked_tables['theories'].get(theory_id)['fields']['Theory'] for
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
            p_title = self.linked_tables['papers'].get(paper_id)['fields']['Title']
            p_url = self.linked_tables['papers'].get(paper_id)['fields']['URL']
            papers.append('[[' + p_url + ' | ' + p_title + ']]')

        paper_items = '\n\n * ' + '\n\n * '.join(papers) + '\n'

        replacements = ('TOOLNAME', tn), ('CATEGORY', cat), ('SUBCATEGORY', subcat), \
                       ('THEORIES', theory_names), ('EVIDENCE', evid), ('FINDINGS', summary), \
                       ('PAPERS', paper_items)
        tool_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.page_template)
        return tool_page


class PaperPage(DokuWikiPage):
    def __init__(self, wiki):
        super(PaperPage, self).__init__(wiki)
        self.base_name = 'appBzOSifwBqSuVfH'
        self.table_name = 'papers_mass'
        self.records = at.Airtable(self.base_name, self.table_name, user_key).get_all()
        self.page_template = '====PAPERTITLE====\n\n<div class="full_reference">REFERENCE</div>\n\n' \
                             '<div class="evidence_type">**Type of evidence**: EVIDENCE</div>\n\n' \
                             '<div class="paper_keywords">**Keywords**: KEYWORDS</div>\n\\\\\n' \
                             '===Paper summary===\n\n<div class="paper_summary">SUMMARY</div>\n\\\\\n' \
                             '===Discussion===\n\n<div class="paper_discussion">DISCUSSION</div>'

        self.main_column = 'parencite'
        self.page_name_column = 'Title'
        self.root_namespace = 'papers:'

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
        paper_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, self.page_template)
        return paper_page

# when a record gets updated in Airtable, its "Edited" field will be set to "checked"
# we will regenerate the relevant page and reset the "Edited" field
# record = airtable.match('Employee Id', 'DD13332454')
# fields = {'Status': 'Fired'}
# airtable.update(record['id'], fields)
