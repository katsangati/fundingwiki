import os
import dokuwiki as dw
import remotewiki

"""
Set up the DW API information
"""
# for DokuWiki we need url, user name and password
usr = "katja"  # this has to be added to the remoteuser in config:authentication

# the official DW
url = "http://innovationsinfundraising.org/"
pss = os.environ['DOKUWIKI_PASS']

# local testing ground
url_test = "http://localhost/~katja/dokuwiki"
pss_test = os.environ['DOKUWIKI_PASS_TEST']

wiki = dw.DokuWiki(url, usr, pss)
wiki_test = dw.DokuWiki(url_test, usr, pss_test)


# local test
# table = remotewiki.PapersTable(wiki_test)
# table = remotewiki.ToolTable(wiki_test)

# official dw
table = remotewiki.PapersTable(wiki)
table.set_table_page()

# page = remotewiki.ToolPage(wiki_test)
page = remotewiki.ToolPage(wiki)
page.set_pages()
