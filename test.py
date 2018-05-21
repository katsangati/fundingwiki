import json
import os
import dokuwiki as dw

with open('config.json', 'r') as f:
    config = json.load(f)
wiki = dw.DokuWiki(config['official']["wiki_url"], "david", "321con")
p = wiki.pages.get('tables:papers')
print(p)
