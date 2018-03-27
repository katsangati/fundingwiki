"""
This is a script for manipulating Airtable data and redirecting it to
an Innovations in Fundraising DokuWiki.

What we're using:
http://lotar.altervista.org/wiki/wiki/plugin/datatables
http://python-dokuwiki.readthedocs.io/en/latest/
http://airtable-python-wrapper.readthedocs.io/en/master/api.html
"""
import dokuwiki
import airtable as at
import os
from functools import reduce
import string
import re


# define a punctuation stripper for using later in pagename constructors
punctuation_translator = str.maketrans('', '', string.punctuation)

"""
Set up the APIs
"""

# for DokuWiki we need url, user name and password
usr = "katja"  # this has to be added to the remoteuser in config:authentication

# the official DW
url = "http://innovationsinfundraising.org/"
pss = os.environ['DOKUWIKI_PASS']

# local testing ground
url_test = "http://localhost/~katja/dokuwiki"
pss_test = os.environ['DOKUWIKI_PASS_TEST']

# for Airtable we need database key, user key and names of the requested tables
basekey_giving_researchers_shared = 'appBzOSifwBqSuVfH'
basekey_giving_impact = "apprleNrkR7dTtW60"

userkey = os.environ['AIRTABLE_API_KEY']

tools_sample = 'tools_public_sample'
theories = 'Theories'
papers = 'papers_mass'
ftse = "ftse100+givingpolicies"
experiments = "Charity experiments"


"""
Fetch the relevant tables from Airtable
"""

tools_table = at.Airtable(basekey_giving_researchers_shared, tools_sample, api_key=userkey)
tools_records = tools_table.get_all()

theories_table = at.Airtable(basekey_giving_researchers_shared, theories, api_key=userkey)
theories_records = theories_table.get_all(fields=['Theory'])

papers_table = at.Airtable(basekey_giving_researchers_shared, papers, api_key=userkey)
papers_records = papers_table.get_all(fields=['Authors', 'Title', 'Journal', 'Year', 'Pages', 'URL'])

ftse_table = at.Airtable(basekey_giving_impact, ftse, api_key=userkey)
ftse_records = ftse_table.get_all()

experiments_table = at.Airtable(basekey_giving_researchers_shared, experiments, api_key=userkey)
experiments_records = experiments_table.get_all()


"""
Initialize the wiki object
"""

wiki = dokuwiki.DokuWiki(url, usr, pss)
wiki_test = dokuwiki.DokuWiki(url_test, usr, pss_test)


"""
Define functions for constructing the DW tables from Airtable content
"""


def tool_row_constructor(record):
    """
    Construct a row for the tools table based on data delivered by Airtable.
    :param record: a single record from the Airtable
    :return: a formatted row for DW
    """
    tool_name = record['fields']['Toolname']
    page_name= tool_name.translate(punctuation_translator)
    tool_page_name = '[[iifwiki:tools:{}|{}]]'.format(page_name, tool_name)

    category = record['fields'].get('Category', [""])
    findings = record['fields'].get('Findings summarized', [""])

    if 'Theories' not in record['fields']:
        theory_names = ''
    else:
        theory_names = [theories_table.get(theory_id)['fields']['Theory'] for
                        theory_id in record['fields']['Theories']]
    row = "| " + tool_page_name + " | " + category[0] + " | " +\
        findings[0].rstrip() + " | " + ', '.join(theory_names) + " |\n"
    return row


def ftse_row_constructor(record):
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


def experiment_row_constructor(record):
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


def format_table(page_content, header, records, main_column, constructor):
    # define the relevant portion of the page, whatever is between the datatables tags
    # we're assuming for now there's one table per page
    start_tag = '<datatables>'
    end_tag = '</datatables>'
    start_index = page_content.find(start_tag) + len(start_tag)
    end_index = page_content.find(end_tag)

    # initialize table content with the header
    table_content = header
    # construct the rows for all available records using the corresponding constructor function
    for record in records:
        # we only consider records in which the main column is not empty
        if main_column not in record['fields']:
            pass
        else:
            table_content += constructor(record)

    # combine the table with the rest of the page
    new_page = page_content[:start_index] + table_content + page_content[end_index:]
    return new_page


# tools table address
tools_page_link = "iifwiki:tools:tools"
tools_page = wiki.pages.get(tools_page_link)
# define the header of the tools table
tools_header = "\n^ Tool name ^ Category ^ Description ^ Theories ^\n"
# create the new page content
new_tools_page = format_table(tools_page, tools_header, tools_records, 'Toolname', tool_row_constructor)
# publish it to DW
wiki.pages.set(tools_page_link, new_tools_page)


# ftse table
ftse_page_link = "iifwiki:employee_giving_schemes"
ftse_page = wiki.pages.get(ftse_page_link)
ftse_header = "\n^ Company ^ Sector ^ Donation Matching ^ Payroll Giving Provider ^ Details ^ Outcomes ^ Reference\n"
new_ftse_page = format_table(ftse_page, ftse_header, ftse_records, 'Company [(cite:LSE)]', ftse_row_constructor)
wiki.pages.set(ftse_page_link, new_ftse_page)


# experiments table
experiments_page_link = "iifwiki:dataexperiments"
experiments_page = wiki.pages.get(experiments_page_link)
experiments_header = "\n^ Experiment ^ N ^ Endowment ^ Share donating ^ Share donated ^ Mean donation ^\
                        SD ^ SD/Mean ^ Effect Size ^ References\n"
new_experiments_page = format_table(experiments_page, experiments_header, experiments_records,
                                    'Experiment', experiment_row_constructor)
wiki.pages.set(experiments_page_link, new_experiments_page)


# # local testing ground
# page_link_test = "datatables:experiments"
# page_test = wiki_test.pages.get(page_link_test)
# new_page = format_table(page_test, experiments_header, experiments_records,
#                                     'Experiment', experiment_row_constructor)
# wiki_test.pages.set(page_link_test, new_page)


"""
Define functions for constructing wiki pages from Airtable content
"""

# define a page template for each tool page
tool_page_template = '==== TOOLNAME ====\n\n**Category**: CATEGORY \n\n**Sub-category**: SUBCATEGORY\n\n' \
                     '**Relevant theories**: THEORIES\n\n**Type of evidence**: EVIDENCE\n\\\\\n\\\\\n' \
                     '=== Main findings ===\n\nFINDINGS\n\\\\\n\\\\\n=== Key papers ===PAPERS'


def create_tool_page(record, template):
    """
    Construct a page for each tool.
    :param record: a single record from the Airtable
    :param template: a template that defines the structure of the page
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
        theory_names = ', '.join([theories_table.get(theory_id)['fields']['Theory'] for
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
        p_title = papers_table.get(paper_id)['fields']['Title']
        p_url = papers_table.get(paper_id)['fields']['URL']
        papers.append('[[' + p_url + ' | ' + p_title + ']]')

    paper_items = '\n\n * ' + '\n\n * '.join(papers) + '\n'

    replacements = ('TOOLNAME', tn), ('CATEGORY', cat), ('SUBCATEGORY', subcat), \
                   ('THEORIES', theory_names), ('EVIDENCE', evid), ('FINDINGS', summary), \
                   ('PAPERS', paper_items)
    tool_page = reduce(lambda a, kv: a.replace(*kv, 1), replacements, template)
    return tool_page


page_names = []
pages = []

for record in tools_records:
    if 'Toolname' not in record['fields']:
        pass
    else:
        tool_name = record['fields']['Toolname']
        page_name= tool_name.translate(punctuation_translator)
        tool_page_name = 'iifwiki:tools:{}'.format(page_name)
        page_names.append(tool_page_name)
        tool_page = create_tool_page(record, tool_page_template)
        pages.append(tool_page)

# # this has to be done with a break of at least 60s
# n_pages = len(page_names)
# for i in range(n_pages):
#     wiki.pages.set(page_names[i], pages[i])


# when a record gets updated in Airtable, its "Edited" field will be set to "checked"
# we will regenerate the relevant page and reset the "Edited" field
# record = airtable.match('Employee Id', 'DD13332454')
# fields = {'Status': 'Fired'}
# airtable.update(record['id'], fields)


