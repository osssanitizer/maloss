import shutil
import tempfile
import logging

from os.path import abspath

from util.enum_util import LanguageEnum
from util.enum_util import PackageManagerEnum
from pm_proxy.maven import MavenProxy
from pm_proxy.jcenter import JcenterProxy
from pm_proxy.jitpack import JitpackProxy
from pm_proxy.npmjs import NpmjsProxy
from pm_proxy.nuget import NugetProxy
from pm_proxy.packagist import PackagistProxy
from pm_proxy.pypi import PypiProxy
from pm_proxy.rubygems import RubygemsProxy


def get_pm_proxy_for_language(language, registry=None, cache_dir=None, isolate_pkg_info=False):
    if language == LanguageEnum.python:
        return PypiProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif language == LanguageEnum.javascript:
        return NpmjsProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif language == LanguageEnum.java:
        return MavenProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif language == LanguageEnum.php:
        return PackagistProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif language == LanguageEnum.ruby:
        return RubygemsProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif language == LanguageEnum.csharp:
        return NugetProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    else:
        raise Exception("Proxy not available for language: %s" % language)


def get_pm_proxy(pm, registry=None, cache_dir=None, isolate_pkg_info=False):
    if pm == PackageManagerEnum.pypi:
        return PypiProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif pm == PackageManagerEnum.npmjs:
        return NpmjsProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif pm == PackageManagerEnum.maven:
        return MavenProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif pm == PackageManagerEnum.jcenter:
        return JcenterProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif pm == PackageManagerEnum.jitpack:
        return JitpackProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif pm == PackageManagerEnum.packagist:
        return PackagistProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif pm == PackageManagerEnum.rubygems:
        return RubygemsProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    elif pm == PackageManagerEnum.nuget:
        return NugetProxy(registry=registry, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    else:
        raise Exception("Proxy not available for package manager: %s" % pm)


def get_metadata(pkg_name, language, cache_dir=None, pkg_version=None, isolate_pkg_info=False):
    if cache_dir:
        cache_dir = abspath(cache_dir)
    # Get metadata and versions
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    pkg_info = pm_proxy.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
    pkg_versions = pm_proxy.get_versions(pkg_name=pkg_name, max_num=-1)
    logging.warning("pkg %s has %d versions", pkg_name, len(pkg_versions))
    logging.info("pkg %s has info %s and versions %s", pkg_name, pkg_info, pkg_versions)


def get_dep(pkg_name, language, cache_dir=None, pkg_version=None, isolate_pkg_info=False):
    if cache_dir:
        cache_dir = abspath(cache_dir)
    # Get dependency packages
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=isolate_pkg_info)
    pm_proxy.get_dep(pkg_name=pkg_name, pkg_version=pkg_version)


def install(pkg_name, language, outdir, install_dir=None, cache_dir=None, trace=False, trace_string_size=1024,
            sudo=False, pkg_version=None):
    if outdir:
        outdir = abspath(outdir)
    if install_dir:
        install_dir = abspath(install_dir)
    if cache_dir:
        cache_dir = abspath(cache_dir)
    # FIXME: if the package to be analyzed is already installed by the system, maybe ignore them since they are trusted.
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir)
    is_temp_install_dir = False
    # js and php requires an installation directory
    is_js_user_install = (language == LanguageEnum.javascript and install_dir is None and not sudo)
    is_php_user_install = (language == LanguageEnum.php and install_dir is None and not sudo)
    if is_js_user_install or is_php_user_install:
        install_dir = tempfile.mkdtemp(prefix='install-')
        is_temp_install_dir = True
    # Install dependency packages
    pm_proxy.install_dep(pkg_name=pkg_name, pkg_version=pkg_version, sudo=sudo, install_dir=install_dir)
    logging.warning("installed dependency to temp dir: %s", install_dir)
    # Install the main package
    pm_proxy.install(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace, trace_string_size=trace_string_size,
                     install_dir=install_dir, outdir=outdir, sudo=sudo)
    if is_temp_install_dir:
        shutil.rmtree(install_dir)


def dynamic_scan(pkg_name, language, outdir, cache_dir=None, trace=False, trace_string_size=1024, sudo=False,
                 pkg_version=None, timeout=300):
    # TODO: how about code coverage tracking?
    if outdir:
        outdir = abspath(outdir)
    if cache_dir:
        cache_dir = abspath(cache_dir)
    # FIXME: if the package to be analyzed is already installed by the system, maybe ignore them since they are trusted.
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir)

    # install_dir, js and php requires and installation directory
    is_temp_install_dir = False
    is_js_user_install = (language == LanguageEnum.javascript and not sudo)
    is_php_user_install = (language == LanguageEnum.php and not sudo)
    if is_js_user_install or is_php_user_install:
        install_dir = tempfile.mkdtemp(prefix='install-')
        is_temp_install_dir = True
    else:
        install_dir = None

    # install, optional, needed for customized installs
    if pm_proxy.has_install(pkg_name=pkg_name, pkg_version=pkg_version):
        # Install dependency packages
        pm_proxy.install_dep(pkg_name=pkg_name, pkg_version=pkg_version, sudo=sudo, install_dir=install_dir)
        logging.warning("installed dependency to temp dir: %s", install_dir)
        # Install main package
        pm_proxy.install(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace, trace_string_size=trace_string_size,
                         install_dir=install_dir, outdir=outdir, sudo=sudo)

    # main, optional, needed for ones with main binaries and executables
    if pm_proxy.has_main(pkg_name=pkg_name, pkg_version=pkg_version):
        pm_proxy.main(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace, trace_string_size=trace_string_size,
                      sudo=sudo, install_dir=install_dir, outdir=outdir, timeout=timeout)

    # exercise, optional, import and execute events, can be enabled/disabled
    if pm_proxy.has_exercise(pkg_name=pkg_name, pkg_version=pkg_version):
        pm_proxy.exercise(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace, trace_string_size=trace_string_size,
                          sudo=sudo, install_dir=install_dir, outdir=outdir, timeout=timeout)

    # test, optional, needed for ones with test commands, can be enabled/disabled
    if pm_proxy.has_test(pkg_name=pkg_name, pkg_version=pkg_version):
        pm_proxy.test(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace, trace_string_size=trace_string_size,
                      sudo=sudo, install_dir=install_dir, outdir=outdir, timeout=timeout)

    # clean up install_dir
    if is_temp_install_dir:
        shutil.rmtree(install_dir)
