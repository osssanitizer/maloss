#!/usr/bin/python3
import sys
import argparse


class Options(object):
    __arg_list = []

    def argv(self):
        return self.__mode, self.__arg_list

    def __init__(self, argv):
        parser = argparse.ArgumentParser(prog="detector",
                                         usage="usage: detector cmd [options] args",
                                         description="Perform malware analysis on OSS in package managers")
        subparsers = parser.add_subparsers(help='Command (e.g. install)', dest='cmd')

        # GetMetadata sub-command
        parser_get_metadata = subparsers.add_parser('get_metadata', help='Get metadata and versions for package(s)')
        parser_get_metadata.add_argument("-i", "--infile", required=True, help="Path to the list of input packages")
        parser_get_metadata.add_argument("-s", "--skipfile", help="Path to the list of analyzed packages")

        # GetDep sub-command
        parser_get_dep = subparsers.add_parser('get_dep', help='Get metadata and dependency for package(s)')
        parser_get_dep.add_argument("-i", "--infile", required=True, help="Path to the list of input packages")
        parser_get_dep.add_argument("-s", "--skipfile", help="Path to the list of analyzed packages")
        parser_get_dep.add_argument("-n", "--native", action="store_true",
                                    help="Run the get_dep command natively, instead of one job per docker container")

        # Compare sub-command
        parser_compare = subparsers.add_parser('compare', help='Compare package(s) and/or their versions(s), natively')
        parser_compare.add_argument("-i", "--infile", required=True, help="Path to the list of input packages")
        parser_compare.add_argument("-s", "--skipfile", help="Path to the list of analyzed packages")

        # AstfilterLocal sub-command
        parser_astfilter_local = subparsers.add_parser('astfilter_local', help='Perform astfilter locally for package(s)')
        parser_astfilter_local.add_argument("-i", "--infile", required=True, help="Path to the list of input packages")
        parser_astfilter_local.add_argument("-s", "--skipfile", help="Path to the list of analyzed packages")

        # TaintLocal sub-command
        parser_taint_local = subparsers.add_parser('taint_local', help='Perform taint locally for package(s)')
        parser_taint_local.add_argument("-i", "--infile", required=True, help="Path to the list of input packages")
        parser_taint_local.add_argument("-s", "--skipfile", help="Path to the list of analyzed packages")

        # Install sub-command
        parser_install = subparsers.add_parser('install', help='Install package(s)')
        parser_install.add_argument("-i", "--infile", required=True, help="Path to the list of input packages")
        parser_install.add_argument("-s", "--skipfile", help="Path to the list of analyzed packages")

        # Dynamic sub-command
        parser_dynamic = subparsers.add_parser('dynamic', help='Analyze package(s) dynamically')
        parser_dynamic.add_argument("-i", "--infile", required=True, help="Path to the list of input packages")
        parser_dynamic.add_argument("-s", "--skipfile", help="Path to the list of analyzed packages")

        # Crawl website
        parser_crawl_website = subparsers.add_parser('crawl_website', help='Crawl website(s)')
        parser_crawl_website.add_argument("-i", "--infile", required=True, help="Path to the list of input urls")
        parser_crawl_website.add_argument("-s", "--skipfile", help="Path to the list of analyzed urls")

        args = parser.parse_args(argv)
        self.__arg_list.append(args.infile)
        self.__arg_list.append(args.skipfile)
        if args.cmd == "get_metadata":
            self.__mode = "Metadata"
        elif args.cmd == "get_dep":
            self.__mode = "Dependency"
            self.__arg_list.append(args.native)
        elif args.cmd == "compare":
            self.__mode = "Compare"
        elif args.cmd == "astfilter_local":
            self.__mode = "AstfilterLocal"
        elif args.cmd == "taint_local":
            self.__mode = "TaintLocal"
        elif args.cmd == "install":
            self.__mode = "Install"
        elif args.cmd == "dynamic":
            self.__mode = "Dynamic"
        elif args.cmd == "crawl_website":
            self.__mode = "CrawlWebsite"
        else:
            raise Exception("Unhandled command: %s" % args.cmd)


if __name__ == '__main__':
    opts = Options(sys.argv[1:])
    print(opts.argv())

