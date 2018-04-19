import wikimanager
import argparse


def main(wiki_version, table_name, mode, resource_type):
    manager = wikimanager.WikiManager(wiki_version)
    manager.setup_table(table_name)

    if mode == 'create':
        if resource_type == 'table':
            manager.create_table()
        elif resource_type == 'pages':
            manager.create_pages()
    elif mode == 'update':
        if resource_type == 'table':
            manager.update_table()
        elif resource_type == 'pages':
            manager.update_pages()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("wiki_version", type=str, help="Specify the DW version",
                        choices=["official", "test"])
    parser.add_argument("table_name", type=str, help="Specify which table you want to use")
    parser.add_argument("mode", type=str,
                        help="Specify whether you want to create a new resource or update an existing one",
                        choices=["create", "update"])
    parser.add_argument("resource_type", type=str, help="Specify if your resource is a table or a set of pages",
                        choices=["table", "pages"])
    args = parser.parse_args()
    main(args.wiki_version, args.table_name, args.mode, args.resource_type)
