import argparse
import sys

from util.enum_util import PackageManagerEnum, LanguageEnum, DistanceAlgorithmEnum, TraceTypeEnum, DataTypeEnum


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="maloss", description="Parse arguments")
    subparsers = parser.add_subparsers(help='Command (e.g. crawl )', dest='cmd')

    # select pm
    parser_select_pm = subparsers.add_parser("select_pm", help="Select the package manager satisfying criteria!")
    parser_select_pm.add_argument("-t", "--threshold", default=100000, type=int,
                                  help="Threshold for number of packages to pick package managers")

    # select packages
    parser_select_pkg = subparsers.add_parser("select_pkg", help="Select packages based on popularity!")
    parser_select_pkg.add_argument("infile", help="Path to the input file.")
    parser_select_pkg.add_argument("outfile", help="Path to the output file.")
    parser_select_pkg.add_argument("-f", "--field", dest="field",
            help="The field to rank/filter on packages. Can be overall or last_month or use_count. "
                 "default is overall and then last_month.")
    select_pkg_criteria = parser_select_pkg.add_mutually_exclusive_group(required=True)
    select_pkg_criteria.add_argument("-n", "--top_n_pkgs", default=0, type=int,
                                     help="Pick the top n packages ranked by total downloads")
    select_pkg_criteria.add_argument("-t", "--threshold", default=0, type=int,
                                     help="Threshold for total number of downloads to pick packages")

    # crawl
    parser_crawl = subparsers.add_parser("crawl", help="Crawl the source sites for different package managers!")
    parser_crawl.add_argument("package_manager", default=PackageManagerEnum.pypi, type=PackageManagerEnum,
                              choices=list(PackageManagerEnum), help="Name of the package manager to crawl")
    parser_crawl.add_argument("-i", "--infile", dest="infile", help="Path to the input file.")
    parser_crawl.add_argument("-s", "--stats", dest="stats", action="store_true", help="Crawl statistics.")
    parser_crawl.add_argument("-p", "--processes", dest="processes", default=1, type=int,
                              help="Number of processes to use if stats is enabled")
    parser_crawl.add_argument("outfile", help="Path to the output file, format is csv.")

    # edit distance
    parser_edit_dist = subparsers.add_parser("edit_dist", help="Compute the edit distance for packages!")
    parser_edit_dist.add_argument("source", help="Path to the list of packages as source in comparison")
    parser_edit_dist.add_argument("-t", "--target", dest="target",
            help="Optional path to list of packages as target in comparison. If not specified, use source as target.")
    parser_edit_dist.add_argument("outfile", help="Path to the output file, format is csv.")
    parser_edit_dist.add_argument("--pair_outfile", help="Path to the optional pair output file, format is csv.")
    parser_edit_dist.add_argument("-a", "--algorithm", dest="algorithm", default=DistanceAlgorithmEnum.py_edit_distance,
            type=DistanceAlgorithmEnum, choices=list(DistanceAlgorithmEnum), help="Distance algorithm to use")
    parser_edit_dist.add_argument("-b", "--batch_size", dest="batch_size", default=10000, type=int,
                                  help="Batch size of packages in comparison. Split large list to avoid out of memory.")
    parser_edit_dist.add_argument("--threshold", dest="threshold", default=2, type=int,
                                  help="The threshold of edit distance to filter comparison results.")
    parser_edit_dist.add_argument("-p", "--processes", dest="processes", default=1, type=int,
                                  help="Number of processes to use")

    # get versions
    parser_get_versions = subparsers.add_parser("get_versions", help="Get versions for the packages!")
    parser_get_versions.add_argument("infile", help="Path to the input file of packages.")
    parser_get_versions.add_argument("outfile", help="Path to the output file.")
    parser_get_versions.add_argument("-c", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_get_versions.add_argument("--max_num", dest="max_num", type=int, help="Maximum number of versions to consider")
    parser_get_versions.add_argument("--min_gap_days", dest="min_gap_days", type=int,
                                     help="If max_num is specified (>=), the minimum gap days for filtering versions")
    parser_get_versions.add_argument("--with_time", dest="with_time", action="store_true", help="Fetch timestamp as well")
    parser_get_versions.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                     type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")

    # get author
    parser_get_author = subparsers.add_parser("get_author", help="Get author for the packages!")
    parser_get_author.add_argument("infile", help="Path to the input file of packages.")
    parser_get_author.add_argument("outfile", help="Path to the output file.")
    parser_get_author.add_argument("-c", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_get_author.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                   type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")

    # get stats
    parser_get_stats = subparsers.add_parser("get_stats", help="Get stats for the packages!")
    parser_get_stats.add_argument("infile", help="Path to the input file of packages.")
    parser_get_stats.add_argument("outfile", help="Path to the output file.")
    parser_get_stats.add_argument("-m", "--package_manager", type=PackageManagerEnum, choices=list(PackageManagerEnum),
                                  help="Package manager of the specified input.")

    # get package metadata and versions
    parser_get_metadata = subparsers.add_parser("get_metadata", help="Get metadata and versions for the specified package!")
    parser_get_metadata.add_argument("-n", "--package_name", required=True, dest="package_name", help="Package name.")
    parser_get_metadata.add_argument("-c", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_get_metadata.add_argument("-i", "--isolate_pkg_info", action="store_true",
                                     help="Isolate package info into different directories!")
    parser_get_metadata.add_argument("-v", "--package_version", dest="package_version", help="Package version")
    parser_get_metadata.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                     type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")

    # get package dependency
    parser_get_dep = subparsers.add_parser("get_dep", help="Get dependency for the specified package!")
    parser_get_dep.add_argument("-n", "--package_name", required=True, dest="package_name", help="Package name.")
    parser_get_dep.add_argument("-c", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_get_dep.add_argument("-i", "--isolate_pkg_info", action="store_true",
                                help="Isolate package info into different directories!")
    parser_get_dep.add_argument("-v", "--package_version", dest="package_version", help="Package version")
    parser_get_dep.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")

    # build package dependency tree for airflow DAG execution
    parser_build_dep = subparsers.add_parser("build_dep", help="Build the dependency graph!")
    parser_build_dep.add_argument("infile", help="Path to the input file of packages.")
    parser_build_dep.add_argument("outfile", help="Path to the output file.")
    parser_build_dep.add_argument("-c", "--cache_dir", dest="cache_dir", required=True,
                                  help="Path to the cache dir for metadata/dep.")
    parser_build_dep.add_argument("-v", "--record_version", dest="record_version", action="store_true",
                                  help="Record versions in the dep graph. Default is to consider the latest version.")
    parser_build_dep.add_argument("-l", "--language", dest="language", default=LanguageEnum.python, type=LanguageEnum,
                                  choices=list(LanguageEnum), help="Language of the specified input.")

    # build author package graph
    parser_build_author = subparsers.add_parser("build_author", help="Build the author-package graph!")
    parser_build_author.add_argument("outfile", help="Path to the output file.")
    parser_build_author.add_argument("-i", "--infiles", dest="infiles", nargs='+', help="List of input files.")
    parser_build_author.add_argument("-t", "--top_authors", dest="top_authors",
                                     help="Path to the top authors output file.")
    parser_build_author.add_argument("-l", "--languages", dest="languages", nargs='+', type=LanguageEnum,
                                     choices=list(LanguageEnum), help="Language of the specified input.")

    # split package dependency tree into n copies
    parser_split_graph = subparsers.add_parser("split_graph", help="Split a graph into n copies!")
    parser_split_graph.add_argument("infile", help="Path to the input file of packages.")
    parser_split_graph.add_argument("out_dir", help="Path to the output directory.")
    parser_split_graph.add_argument("-k", "--k_out_dirs", type=int, help="Number of out_dirs to store splitted files")
    split_graph_algo = parser_split_graph.add_mutually_exclusive_group(required=True)
    split_graph_algo.add_argument("-n", "--num_outputs", type=int,
                                  help="Number of outputs to split the input file into!")
    split_graph_algo.add_argument("-s", "--seedfile", help="List of seed packages that must be in subgraph.")
    parser_split_graph.add_argument("-d", "--dagfile", dest="dagfile", help="Path to the dag file for infile.")

    # install specified package
    parser_install = subparsers.add_parser("install", help="Install the specified package!")
    parser_install.add_argument("-n", "--package_name", required=True, dest="package_name", help="Package name.")
    parser_install.add_argument("-i", "--install_dir", dest="install_dir", help="path to the install dir.")
    parser_install.add_argument("-c", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_install.add_argument("-o", "--out_dir", dest="out_dir", help="Path to the tracing output.")
    parser_install.add_argument("-t", "--trace", dest="trace", action="store_true", help="Trace the program.")
    parser_install.add_argument("--trace_string_size", dest="trace_string_size", type=int, help="String size in trace")
    parser_install.add_argument("-s", "--sudo", dest="sudo", action="store_true", help="Run with sudo privilege.")
    parser_install.add_argument("-v", "--package_version", dest="package_version", help="Package version")
    parser_install.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")

    # parse source file and generate ast
    parser_astgen = subparsers.add_parser("astgen", help="Generate Abstract Syntax Tree from source files")
    parser_astgen.add_argument("inpath", help="Path to the input directory or file")
    parser_astgen.add_argument("outfile", help="Path to the output file.")
    parser_astgen.add_argument("-b", "--root", dest="root", help="Path to the root of the source.")
    parser_astgen.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                               type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_astgen.add_argument("-n", "--package_name", dest="package_name",
                               help="Package name of the specified input.")
    parser_astgen.add_argument("-v", "--package_version", dest="package_version",
                               help="Package version of the specified input.")
    parser_astgen.add_argument("-e", "--evaluate_smt", dest="evaluate_smt", action="store_true",
                               help="Evaluate the smt formula in the astgen output.")
    parser_astgen.add_argument("-c", "--configpath", dest="configpath",
            help="Optional path to the filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).")

    # filter the packages based on specified SMT formula
    parser_astfilter = subparsers.add_parser("astfilter", help="Filter the packages based on specified SMT formula")
    parser_astfilter.add_argument("-n", "--package_name", required=True, dest="package_name",
                                  help="Package name of the specified input.")
    parser_astfilter.add_argument("-v", "--package_version", dest="package_version",
                                  help="Package version of the specified input.")
    parser_astfilter.add_argument("--ignore_dep_version", dest="ignore_dep_version", action="store_true",
                                  help="Ignore the version for dependencies and use their latest versions.")
    parser_astfilter.add_argument("--ignore_dep", dest="ignore_dep", action="store_true",
                                  help="Ignore the dependencies and analyze only the specified package.")
    parser_astfilter.add_argument("-d", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_astfilter.add_argument("-o", "--out_dir", required=True, dest="out_dir", help="Path to analysis output dir.")
    parser_astfilter.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                  type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_astfilter.add_argument("-m", "--package_manager", type=PackageManagerEnum, choices=list(PackageManagerEnum),
                                  help="Package manager of the specified input.")
    parser_astfilter.add_argument("-c", "--configpath", dest="configpath",
            help="Optional path to the filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).")

    # run taint analysis on the specified package
    parser_taint = subparsers.add_parser("taint", help="Run taint analysis on the specified package")
    parser_taint.add_argument("-n", "--package_name", required=True, dest="package_name",
                              help="Package name of the specified input.")
    parser_taint.add_argument("-v", "--package_version", dest="package_version",
                              help="Package version of the specified input.")
    parser_taint.add_argument("-i", "--inpath", dest="inpath",
                              help="Path to the input directory or file. If specified, don't check dependencies.")
    parser_taint.add_argument("--ignore_dep_version", dest="ignore_dep_version", action="store_true",
                              help="Ignore the version for dependencies and use their latest versions.")
    parser_taint.add_argument("--ignore_dep", dest="ignore_dep", action="store_true",
                              help="Ignore the dependencies and analyze only the specified package.")
    parser_taint.add_argument("-d", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_taint.add_argument("-o", "--out_dir", required=True, dest="out_dir", help="Path to analysis output dir.")
    parser_taint.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                              type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_taint.add_argument("-c", "--configpath", dest="configpath",
            help="Optional path to the filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).")

    # run filter_pkg analysis on list of packages
    parser_filter_pkg = subparsers.add_parser("filter_pkg", help="Filter package based on selected criteria, e.g. api, flow")
    parser_filter_pkg.add_argument("infile", help="Path to the input file of packages.")
    parser_filter_pkg.add_argument("outfile", help="Path to the output file.")
    parser_filter_pkg.add_argument("-d", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_filter_pkg.add_argument("-o", "--out_dir", required=True, dest="out_dir", help="Path to analysis output dir.")
    parser_filter_pkg.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                   type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_filter_pkg.add_argument("-c", "--configpath", dest="configpath",
            help="Reduced filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).")

    # run danger api analysis on the specified package
    parser_danger = subparsers.add_parser("danger", help="Run danger api analysis on the specified package")
    parser_danger.add_argument("-n", "--package_name", required=True, dest="package_name",
                               help="Package name of the specified input.")
    parser_danger.add_argument("-v", "--package_version", dest="package_version",
                               help="Package version of the specified input.")
    parser_danger.add_argument("--ignore_dep_version", dest="ignore_dep_version", action="store_true",
                               help="Ignore the version for dependencies and use their latest versions.")
    parser_danger.add_argument("-d", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_danger.add_argument("-o", "--out_dir", required=True, dest="out_dir", help="Path to analysis output dir.")
    parser_danger.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                               type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_danger.add_argument("-c", "--configpath", dest="configpath",
            help="Optional path to the filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).")

    # run static analysis on the specified package
    parser_static = subparsers.add_parser("static", help="Run static analysis on the specified package")
    parser_static.add_argument("-n", "--package_name", required=True, dest="package_name",
                               help="Package name of the specified input.")
    parser_static.add_argument("-v", "--package_version", dest="package_version",
                               help="Package version of the specified input.")
    parser_static.add_argument("--ignore_dep_version", dest="ignore_dep_version", action="store_true",
                               help="Ignore the version for dependencies and use their latest versions.")
    parser_static.add_argument("-d", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_static.add_argument("-o", "--out_dir", required=True, dest="out_dir", help="Path to analysis output dir.")
    parser_static.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                               type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_static.add_argument("-c", "--configpath", dest="configpath",
            help="Optional path to the filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).")

    # run dynamic analysis on the specified package
    parser_dynamic = subparsers.add_parser("dynamic", help="Run dynamic analysis on the specified package")
    parser_dynamic.add_argument("-n", "--package_name", required=True, dest="package_name",
                                help="Package name of the specified input.")
    parser_dynamic.add_argument("-v", "--package_version", dest="package_version",
                                help="Package version of the specified input.")
    parser_dynamic.add_argument("-c", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_dynamic.add_argument("-o", "--out_dir", required=True, dest="out_dir", help="Path to the tracing output.")
    parser_dynamic.add_argument("-t", "--trace", dest="trace", action="store_true", help="Trace the program.")
    parser_dynamic.add_argument("--trace_string_size", dest="trace_string_size", type=int, help="String size in trace")
    parser_dynamic.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_dynamic.add_argument("-s", "--sudo", dest="sudo", action="store_true", help="Run with sudo privilege.")

    # format and interpret traces (strace, sysdig etc.) for packages
    parser_interpret_trace = subparsers.add_parser("interpret_trace", help="Interpret the collected dynamic traces")
    parser_interpret_trace.add_argument("--trace_type", dest="trace_type", default=TraceTypeEnum.sysdig, type=TraceTypeEnum,
                                        choices=list(TraceTypeEnum), help="Trace type of the specified log.")
    parser_interpret_trace.add_argument("--trace_dir", required=True, dest="trace_dir", help="Path to the trace log directory.")
    parser_interpret_trace.add_argument("-n", "--package_name", dest="package_name",
                                        help="Package name of the specified input. Optional if trace type is sysdig.")
    parser_interpret_trace.add_argument("-v", "--package_version", dest="package_version",
                                        help="Package version of the specified input. Optional if trace type is sysdig.")
    parser_interpret_trace.add_argument("-c", "--cache_dir", dest="cache_dir", help="Path to the cache directory.")
    parser_interpret_trace.add_argument("-o", "--out_dir", required=True, dest="out_dir", help="Path to analysis output dir.")
    parser_interpret_trace.add_argument("-l", "--language", dest="language", default=LanguageEnum.python, type=LanguageEnum,
                                        choices=list(LanguageEnum), help="Language of the specified input.")
    parser_interpret_trace.add_argument("-p", "--processes", dest="processes", default=1, type=int,
                                        help="Number of processes to use")
    parser_interpret_trace.add_argument("-b", "--binary", dest="binary", action="store_true",
                                        help="Save analysis result in binary format.")
    parser_interpret_trace.add_argument("-s", "--skip_file", dest="skip_file", help="Path to list of packages already analyzed.")

    # summarize analysis results and plot them if applicable.
    parser_interpret_result = subparsers.add_parser("interpret_result", help="Read the specific data, summarize and plot them.")
    parser_interpret_result.add_argument("infile", help="Path to the input file of packages.")
    parser_interpret_result.add_argument("outfile", help="Path to the output file.")
    parser_interpret_result.add_argument("--data_type", default=DataTypeEnum.api, type=DataTypeEnum,
                                         choices=list(DataTypeEnum),
                                         help="Type of data to summarize and plot distribution on.")
    parser_interpret_result.add_argument("-c", "--cache_dir", dest="cache_dir", help="Path to the cache directory.")
    parser_interpret_result.add_argument("-s", "--skip_file", dest="skip_file", help="Path to the cases to ignore. Iteratively increase/update this list.")
    parser_interpret_result.add_argument("-o", "--out_dir", dest="out_dir", help="Path to analysis output dir.")
    parser_interpret_result.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                         type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_interpret_result.add_argument("-m", "--package_manager", dest="package_manager", default=PackageManagerEnum.pypi,
                                         type=PackageManagerEnum, choices=list(PackageManagerEnum), help="Name of the package manager")
    parser_interpret_result.add_argument("-d", "--detail_mapping", dest="detail_mapping", action="store_true", help="Dump detail mapping in the output file.")
    parser_interpret_result.add_argument("--compare_ast_options_file", dest="compare_ast_options_file",
                                         help="Options used in filtering compare_ast results. It's a json file containing a list of enabled options.")
    parser_interpret_result.add_argument("--detail_filename", dest="detail_filename", action="store_true",
                                         help="Dump filename in static analysis in the output file. Useful for filtering.")

    # compare static API analysis across input files, packages and their versions
    parser_compare_ast = subparsers.add_parser("compare_ast", help="Compare ast results of the specified packages")
    compare_ast_input = parser_compare_ast.add_mutually_exclusive_group(required=True)
    compare_ast_input.add_argument("-i", "--infiles", dest="infiles", nargs='+', help="List of input files.")
    compare_ast_input.add_argument("-n", "--package_names", dest="package_names", nargs='+', help="List of packages.")
    parser_compare_ast.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                    type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_compare_ast.add_argument("-d", "--cache_dir", dest="cache_dir", help="Path to the cache dir for metadata/dep.")
    parser_compare_ast.add_argument("-o", "--out_dir", required=True, dest="out_dir", help="Path to analysis output dir.")
    parser_compare_ast.add_argument("-c", "--configpath", dest="configpath",
            help="Optional path to the filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).")
    parser_compare_ast.add_argument("--outfile", dest="outfile", help="Path to the output file.")

    # filter versions to further investigate based on the compare ast results
    parser_filter_versions = subparsers.add_parser("filter_versions", help="Filter versions based on compare ast results")
    parser_filter_versions.add_argument("versions_infile", help="The output of get_versions job, containing packages and their versions which we care.")
    parser_filter_versions.add_argument("compare_ast_infile", help="The output of compare_ast job, containing the api analysis of packages and their versions.")
    parser_filter_versions.add_argument("outfile", help="The resulting packages and their versions that we want.")

    # compare package hash values of same packages across different package managers (e.g. maven vs. jcenter)
    parser_compare_hash = subparsers.add_parser("compare_hash", help="Compare hash values of the specified packages among multiple registries")
    parser_compare_hash.add_argument("-i", "--infiles", required=True, dest="infiles", nargs='+',
                                     help="List of packages from different registries.")
    parser_compare_hash.add_argument("-d", "--cache_dirs", required=True, dest="cache_dirs", nargs='+',
                                     help="List of cache dirs for different registries. Use the same order as infiles.")
    parser_compare_hash.add_argument("--compare_hash_cache", dest="compare_hash_cache",
                                     help="Cache of compare hash results to save loading/comparison time!")
    parser_compare_hash.add_argument("--inspect_content", dest="inspect_content", action="store_true",
                                     help="Inspect the content of compressed files for equity comparison.")
    parser_compare_hash.add_argument("--inspect_api", dest="inspect_api", action="store_true",
                                     help="Inspect the api of jar/aar for equity comparison.")
    parser_compare_hash.add_argument("-c", "--configpath", dest="configpath",
            help="Optional path to the filter of nodes, stored in proto buffer format (AstLookupConfig in ast.proto).")
    parser_compare_hash.add_argument("-o", "--outfile", dest="outfile", help="Path to the output file.")

    # grep simply string within packages.
    parser_grep = subparsers.add_parser("grep_pkg", help="Download the packages and grep through their content.")
    parser_grep.add_argument("infile", help="Path to the input file of packages.")
    parser_grep.add_argument("outfile", help="Path to the output folder.")
    parser_grep.add_argument("pattern", help="Pattern to grep for in packages.")
    parser_grep.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                             type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    parser_grep.add_argument("-p", "--processes", dest="processes", default=1, type=int,
                             help="Number of processes")

    # cross check behaviors of one package manager in other package managers
    parser_cross_check = subparsers.add_parser("cross_check", help="search for malware with the same name or activities across package managers")
    parser_cross_check.add_argument("base_behavior_file", help="The list of base behaviors, we search for these behaviors")
    parser_cross_check.add_argument("base_package_manager", help="The base package manager, we search for package managers excluding this one.")

    # measure speed up
    parser_speedup = subparsers.add_parser("speedup", help="Measure the speedup with summaries vs. without summaries")
    parser_speedup.add_argument("infile", help="Path to the input file of packages.")
    parser_speedup.add_argument("outfile", help="Path to the otuput file of analysis logs.")
    parser_speedup.add_argument("-n", "--number", default=1000, type=int, help="Randomly select n packages from infile")
    parser_speedup.add_argument("-l", "--language", dest="language", default=LanguageEnum.python,
                                type=LanguageEnum, choices=list(LanguageEnum), help="Language of the specified input.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    if args.cmd == "select_pm":
        from interpret_util import select_pm
        select_pm(threshold=args.threshold)
    elif args.cmd == "select_pkg":
        from interpret_util import select_pkg
        select_pkg(infile=args.infile, outfile=args.outfile, top_n_pkgs=args.top_n_pkgs, threshold=args.threshold,
                   field=args.field)
    elif args.cmd == "crawl":
        from crawl import crawl
        crawl(package_manager=args.package_manager, outfile=args.outfile, infile=args.infile, stats=args.stats,
              processes=args.processes)
    elif args.cmd == "edit_dist":
        from edit_dist import edit_dist
        edit_dist(source=args.source, target=args.target, algorithm=args.algorithm, outfile=args.outfile,
                  pair_outfile=args.pair_outfile, batch_size=args.batch_size, threshold=args.threshold,
                  processes=args.processes)
    elif args.cmd == "get_versions":
        from interpret_util import get_versions
        get_versions(infile=args.infile, outfile=args.outfile, language=args.language, max_num=args.max_num,
                     min_gap_days=args.min_gap_days, with_time=args.with_time, cache_dir=args.cache_dir)
    elif args.cmd == "get_author":
        from interpret_util import get_author
        get_author(infile=args.infile, outfile=args.outfile, language=args.language, cache_dir=args.cache_dir)
    elif args.cmd == "get_stats":
        from crawl import get_stats_wrapper
        get_stats_wrapper(infile=args.infile, outfile=args.outfile, package_manager=args.package_manager)
    elif args.cmd == "get_metadata":
        from pm_util import get_metadata
        get_metadata(pkg_name=args.package_name, language=args.language, cache_dir=args.cache_dir,
                     pkg_version=args.package_version, isolate_pkg_info=args.isolate_pkg_info)
    elif args.cmd == "get_dep":
        from pm_util import get_dep
        get_dep(pkg_name=args.package_name, language=args.language, cache_dir=args.cache_dir,
                pkg_version=args.package_version, isolate_pkg_info=args.isolate_pkg_info)
    elif args.cmd == "build_dep":
        from interpret_util import build_dep
        build_dep(infile=args.infile, outfile=args.outfile, cache_dir=args.cache_dir, language=args.language,
                  record_version=args.record_version)
    elif args.cmd == "build_author":
        from interpret_util import build_author
        build_author(infiles=args.infiles, languages=args.languages, outfile=args.outfile, top_authors=args.top_authors)
    elif args.cmd == "split_graph":
        from interpret_util import split_graph
        split_graph(infile=args.infile, outdir=args.out_dir, k_outdirs=args.k_out_dirs, num_outputs=args.num_outputs,
                    seedfile=args.seedfile, dagfile=args.dagfile)
    elif args.cmd == "install":
        from pm_util import install
        install(pkg_name=args.package_name, language=args.language, outdir=args.out_dir, install_dir=args.install_dir,
                cache_dir=args.cache_dir, trace=args.trace, trace_string_size=args.trace_string_size, sudo=args.sudo,
                pkg_version=args.package_version)
    elif args.cmd == "astgen":
        from static_util import astgen
        astgen(inpath=args.inpath, outfile=args.outfile, root=args.root, configpath=args.configpath,
               language=args.language, pkg_name=args.package_name, pkg_version=args.package_version,
               evaluate_smt=args.evaluate_smt)
    elif args.cmd == "astfilter":
        from static_util import astfilter
        astfilter(pkg_name=args.package_name, language=args.language, outdir=args.out_dir, cache_dir=args.cache_dir,
                  configpath=args.configpath, pkg_version=args.package_version, pkg_manager=args.package_manager,
                  ignore_dep_version=args.ignore_dep_version, ignore_dep=args.ignore_dep)
    elif args.cmd == "taint":
        from static_util import taint
        taint(pkg_name=args.package_name, language=args.language, outdir=args.out_dir, cache_dir=args.cache_dir,
              configpath=args.configpath, pkg_version=args.package_version, ignore_dep_version=args.ignore_dep_version,
              ignore_dep=args.ignore_dep, inpath=args.inpath)
    elif args.cmd == "filter_pkg":
        from interpret_util import filter_pkg
        filter_pkg(infile=args.infile, outfile=args.outfile, language=args.language, out_dir=args.out_dir,
                   cache_dir=args.cache_dir, configpath=args.configpath)
    elif args.cmd == "danger":
        from static_util import danger
        danger(pkg_name=args.package_name, language=args.language, outdir=args.out_dir, cache_dir=args.cache_dir,
               configpath=args.configpath, pkg_version=args.package_version,
               ignore_dep_version=args.ignore_dep_version)
    elif args.cmd == "static":
        from static_util import static_scan
        static_scan(pkg_name=args.package_name, language=args.language, outdir=args.out_dir, cache_dir=args.cache_dir,
                    configpath=args.configpath, pkg_version=args.package_version,
                    ignore_dep_version=args.ignore_dep_version)
    elif args.cmd == "dynamic":
        from pm_util import dynamic_scan
        dynamic_scan(pkg_name=args.package_name, language=args.language, outdir=args.out_dir, cache_dir=args.cache_dir,
                     trace=args.trace, trace_string_size=args.trace_string_size, sudo=args.sudo,
                     pkg_version=args.package_version)
    elif args.cmd == "interpret_trace":
        from interpret_util import interpret_trace
        interpret_trace(language=args.language, outdir=args.out_dir, cache_dir=args.cache_dir,
                        trace_type=args.trace_type, trace_dir=args.trace_dir, pkg_name=args.package_name,
                        pkg_version=args.package_version, binary=args.binary, processes=args.processes, skip_file=args.skip_file)
    elif args.cmd == "interpret_result":
        from interpret_util import interpret_result
        interpret_result(infile=args.infile, outfile=args.outfile, data_type=args.data_type, language=args.language,
                         package_manager=args.package_manager, outdir=args.out_dir, cache_dir=args.cache_dir,
                         skip_file=args.skip_file, detail_mapping=args.detail_mapping,
                         compare_ast_options_file=args.compare_ast_options_file,
                         detail_filename=args.detail_filename)
    elif args.cmd == "compare_ast":
        from interpret_util import compare_ast
        compare_ast(infiles=args.infiles, package_names=args.package_names,  language=args.language,
                    outdir=args.out_dir, cache_dir=args.cache_dir, configpath=args.configpath, outfile=args.outfile)
    elif args.cmd == "filter_versions":
        from interpret_util import filter_versions
        filter_versions(versions_infile=args.versions_infile, compare_ast_infile=args.compare_ast_infile,
                        outfile=args.outfile)
    elif args.cmd == "compare_hash":
        from interpret_util import compare_hash
        compare_hash(infiles=args.infiles, cache_dirs=args.cache_dirs, outfile=args.outfile,
                     compare_hash_cache=args.compare_hash_cache, inspect_content=args.inspect_content,
                     inspect_api=args.inspect_api, configpath=args.configpath)
    elif args.cmd == "grep_pkg":
        from interpret_util import grep
        grep(infile=args.infile, outfile=args.outfile, pattern=args.pattern, language=args.language,
             processes=args.processes)
    elif args.cmd == "cross_check":
        from interpret_util import cross_check
        cross_check(base_behavior_file=args.base_behavior_file, base_package_manager=args.base_package_manager)
    elif args.cmd == "speedup":
        from interpret_util import speedup
        speedup(infile=args.infile, outfile=args.outfile, number=args.number, language=args.language)
    else:
        raise Exception("unexpected cmd %s" % args.cmd)
