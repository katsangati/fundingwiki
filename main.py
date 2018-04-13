import wikimanager


manager = wikimanager.WikiManager('official')
# local test
# manager = wikimanager.WikiManager('test')

manager.setup_table('tools_public_sample')

manager.create_table()
manager.create_pages()

manager.update_table()
manager.update_pages()

