import logging
from os.path import exists, join, basename
from util.enum_util import LanguageEnum
from static_proxy.py_analyzer import PyAnalyzer
from static_proxy.js_analyzer import JsAnalyzer
from static_proxy.java_analyzer import JavaAnalyzer
from static_proxy.php_analyzer import PhpAnalyzer
from static_proxy.ruby_analyzer import RubyAnalyzer


def get_static_proxy_for_language(language):
    if language == LanguageEnum.python:
        return PyAnalyzer()
    elif language == LanguageEnum.javascript:
        return JsAnalyzer()
    elif language == LanguageEnum.java:
        return JavaAnalyzer()
    elif language == LanguageEnum.php:
        return PhpAnalyzer()
    elif language == LanguageEnum.ruby:
        return RubyAnalyzer()
    else:
        raise Exception("Proxy not available for language: %s" % language)


def astgen(inpath, outfile, root=None, configpath=None, language=LanguageEnum.python, pkg_name=None, pkg_version=None,
           evaluate_smt=False):
    """
    Parse source file, generate ast and record specified ast nodes.
    """
    static_proxy = get_static_proxy_for_language(language=language)
    static_proxy.astgen(inpath=inpath, outfile=outfile, root=root, configpath=configpath, pkg_name=pkg_name,
                        pkg_version=pkg_version, evaluate_smt=evaluate_smt)


def astfilter(pkg_name, language, outdir, cache_dir=None, configpath=None, pkg_version=None, pkg_manager=None,
              ignore_dep_version=False, ignore_dep=False):
    """
    Run astgen on the specified package and its dependencies, filter the package based on the specified smt formula
    """
    static_proxy = get_static_proxy_for_language(language=language)
    static_proxy.astfilter(pkg_name=pkg_name, outdir=outdir, cache_dir=cache_dir, configpath=configpath,
                           pkg_version=pkg_version, pkg_manager=pkg_manager, ignore_dep_version=ignore_dep_version,
                           ignore_dep=ignore_dep)


def taint(pkg_name, language, outdir, cache_dir=None, configpath=None, pkg_version=None, ignore_dep_version=False,
          ignore_dep=False, inpath=None):
    """
    Run taint flow analysis on the specified package and its dependencies or the specified file.
    """
    static_proxy = get_static_proxy_for_language(language=language)
    if inpath is not None and exists(inpath):
        outfile = join(outdir, basename(inpath.rstrip('/')) + ".astgen.txt")
        static_proxy.taint(inpath=inpath, outfile=outfile, configpath=configpath, pkg_name=pkg_name,
                           pkg_version=pkg_version)
        logging.warning("output is located at %s", outfile)
    else:
        static_proxy.taint_tree(pkg_name=pkg_name, outdir=outdir, cache_dir=cache_dir, configpath=configpath,
                                pkg_version=pkg_version, ignore_dep_version=ignore_dep_version, ignore_dep=ignore_dep)


def danger(pkg_name, language, outdir, cache_dir=None, configpath=None, pkg_version=None, ignore_dep_version=False,
           ignore_dep=False):
    """
    Run danger api analysis on the specified package
    """
    static_proxy = get_static_proxy_for_language(language=language)
    static_proxy.danger_tree(pkg_name=pkg_name, outdir=outdir, cache_dir=cache_dir, configpath=configpath,
                             pkg_version=pkg_version, ignore_dep_version=ignore_dep_version, ignore_dep=ignore_dep)


def static_scan(pkg_name, language, outdir, cache_dir=None, configpath=None, pkg_version=None,
                ignore_dep_version=False, ignore_dep=False):
    """
    Run static analysis on the specified package, both taint flow analysis and danger api analysis
    """
    # run static api analysis and flow analysis
    static_proxy = get_static_proxy_for_language(language=language)
    static_proxy.astfilter(pkg_name=pkg_name, outdir=outdir, cache_dir=cache_dir, configpath=configpath,
                           pkg_version=pkg_version, ignore_dep_version=ignore_dep_version, ignore_dep=ignore_dep)
    static_proxy.taint_tree(pkg_name=pkg_name, outdir=outdir, cache_dir=cache_dir, configpath=configpath,
                            pkg_version=pkg_version, ignore_dep_version=ignore_dep_version, ignore_dep=ignore_dep)
    # TODO: not implemented yet
    static_proxy.danger_tree(pkg_name=pkg_name, outdir=outdir, cache_dir=cache_dir, configpath=configpath,
                             pkg_version=pkg_version, ignore_dep_version=ignore_dep_version, ignore_dep=ignore_dep)
