"""
This is a standalone script for updating records in the Papers table in the database.
A proper call to these functions is included in the update_all script.
"""
import airtable as at
import doi_resolver as dr
import os
from pybtex.database.input import bibtex
import time

bibtex_translator = str.maketrans('', '', '\\{}')
# textquotesingle

user_key = os.environ['AIRTABLE_API_KEY']
table_name = 'papers_mass'
table_base = 'appBzOSifwBqSuVfH'

table = at.Airtable(table_base, table_name, user_key)
records = table.get_all()

for record in records:
    title = record['fields'].get('Title', '')
    title_clean1 = title.replace('{\Textquotesingle}', "'")
    title_clean2 = title_clean1.replace('{\Textemdash}', "-")
    title_clean3 = title_clean2.translate(bibtex_translator).lower().title()
    table.update(record['id'], {'Title': title_clean3})


def update_paper_table():
    for record in records:
        if 'Modified' in record['fields']:
            fill_paper(record)


def fill_paper(record):
    # if doi present
    if 'doi' in record['fields']:
        doi = record['fields']['doi']

        # fill in bibtex
        bib = dr.doi2bib(doi)
        airtable.update(record['id'], {'bibtexfull': bib})

        # fill in citation count
        citations = dr.doi2count(doi)
        airtable.update(record['id'], {'num_citations': int(citations)})

        # fill in bibliographic information
        fill_bibliography(record)

    elif 'bibtexfull' in record['fields']:
        # fill in bibliographic information
        fill_bibliography(record)

    else:
        print("This paper record has neither doi nor bibtex specified.")

    time.sleep(5)


def fill_bibliography(record):
    bib_string = record['fields']['bibtexfull']

    # fill in citation data
    parser = bibtex.Parser()
    bib_data = parser.parse_string(bib_string)
    k = bib_data.entries.keys()[0]
    print(k)
    bib_type = bib_data.entries[k].type
    airtable.update(record['id'], {'Publication_type': bib_type})

    authors_list = [p.__str__() for p in bib_data.entries[k].persons['author']]
    authors = "; ".join(authors_list)
    airtable.update(record['id'], {'Authors': authors})

    year = bib_data.entries[k].fields.get('year', '')
    airtable.update(record['id'], {'Year': year})

    title = bib_data.entries[k].fields['title']
    airtable.update(record['id'], {'Title': title})

    if bib_type == "article":
        journal = bib_data.entries[k].fields['journal']
        airtable.update(record['id'], {'Journal': journal})
        volume = bib_data.entries[k].fields.get('volume', '')
        airtable.update(record['id'], {'Vol': volume})
        number = bib_data.entries[k].fields.get('number', '')
        airtable.update(record['id'], {'Num': number})
        pages = bib_data.entries[k].fields.get('pages', '')
        airtable.update(record['id'], {'Pages': pages})

    elif bib_type == "incollection":
        book = bib_data.entries[k].fields['booktitle']
        airtable.update(record['id'], {'Book_title': book})
        pages = bib_data.entries[k].fields.get('pages', '')
        airtable.update(record['id'], {'Pages': pages})

    elif bib_type == "techreport":
        institution = bib_data.entries[k].fields.get('institution', '')
        airtable.update(record['id'], {'Institution': institution})

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

    airtable.update(record['id'], {'parencite': parencite})

    time.sleep(1)


"""
TODO: replace inproceedings with incollection
replace any undefined categories with misc

1) article: a paper published in a journal will be cited as Author, N. (year). Title. Journal Name, Vol, Num, Pages.
2) incollection: a book chapter cited as Author, N. (year). Chapter title, Pages. In: Book title.
3) book: a whole book (is this needed?) cited as Author, N. (year). Title.
4) techreport: a paper published by some institution (e.g. long-term study, review) as Author, N. (year). Title. Institution.
5) misc: an unpublished manuscript, thesis (other items?) as Author, N. (year). Title.
"""

"""
When filling out the existing table, we ran the following operations:

for r in records:
    # fill in doi
    if 'doi' not in record['fields']:
        title = record['fields'].get("Title", "")
        if title != "":
            doi = dr.title2doi(title)
            airtable.update(record['id'], {'doi': doi})
    time.sleep(5)

for r in records:
    fill_paper(r)
for r in records:
    fill_bibliography(r) 
"""
