import requests
from habanero import counts
from habanero import Crossref

# import scholar.scholar as sch
#
# querier = sch.ScholarQuerier()
# settings = sch.ScholarSettings()
# settings.set_citation_format(4) #4 is for BibTex
# querier.apply_settings(settings)


def doi2bib(doi):
    """ Return a bibTeX string of metadata for a given DOI."""

    url = "http://dx.doi.org/" + doi

    headers = {"accept": "application/x-bibtex"}
    r = requests.get(url, headers = headers)

    return r.text


def doi2count(doi):
    return counts.citation_count(doi=doi)


def title2doi(title):
    title = title.lower()
    clean_title = ''.join(e for e in title if e.isalnum())
    cr = Crossref()
    res = cr.works(query_title=title, select="title,DOI", limit=5)
    for r in res['message']['items']:
        fetched_title = r['title'][0].lower()
        clean_fetched = ''.join(e for e in fetched_title if e.isalnum())
        if clean_fetched == clean_title:
            return r['DOI']


# def title2bib(title):
#     query = sch.SearchScholarQuery()
#     query.set_words(title)
#     query.set_num_page_results(1)
#     querier.send_query(query)
#     if len(querier.articles) > 0:
#         bib = querier.articles[0].citation_data
#         return bib.decode('utf-8')
#     else:
#         return ""
