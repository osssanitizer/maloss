import os
import json
import shutil
import logging
import tempfile
import requests
import dateutil.parser
from os.path import join, exists, expanduser

from util.job_util import exec_command
from pm_proxy.pm_base import PackageManagerProxy


class PackagistProxy(PackageManagerProxy):
    # A script, in Composer's terms, can either be a PHP callback (defined as a static method) or any command-line
    # executable command.
    # https://getcomposer.org/doc/articles/scripts.md
    # Only scripts defined in the root package's composer.json are executed.
    # https://getcomposer.org/doc/articles/scripts.md#what-is-a-script-
    # extension_loaded - Find out whether an extension is loaded
    # http://php.net/manual/en/function.extension-loaded.php
    # Wrapping C++ Classes in a PHP Extension
    # https://devzone.zend.com/1435/wrapping-c-classes-in-a-php-extension/
    # Zend API: Hacking the Core of PHP
    # http://php.net/manual/en/internals2.ze1.zendapi.php
    def __init__(self, registry=None, cache_dir=None, isolate_pkg_info=False):
        super(PackagistProxy, self).__init__()
        self.registry = registry
        self.cache_dir = cache_dir
        self.isolate_pkg_info = isolate_pkg_info
        self.metadata_format = 'json'
        self.dep_format = 'json'

    def _get_version_info(self, versions, pkg_version=None):
        if len(versions) == 0:
            logging.error("there is no version!")
            return None
        if pkg_version:
            # get the specified version
            if pkg_version in versions:
                return versions[pkg_version]
            for version_info in versions.values():
                if version_info['version_normalized'].startswith(pkg_version):
                    return version_info
            logging.error("cannot find version info for %s among %s", pkg_version, versions.keys())
            return versions.values()[0]
        else:
            # get the latest version
            pkg_version_norm2info = {v_info['version_normalized']: v_info for v_info in versions.values()}
            pkg_version_norm2info_sorted = sorted(pkg_version_norm2info.items(), key=lambda k: k[0], reverse=True)
            pkg_version_norm2info_sorted_filtered = filter(lambda k: '9999999' not in k[0] and k[0][0].isdigit(),
                                                           pkg_version_norm2info_sorted)
            if len(pkg_version_norm2info_sorted_filtered) > 0:
                latest_version = pkg_version_norm2info_sorted_filtered[0]
                logging.info("default to latest version: %s", latest_version[0])
                return latest_version[1]
            else:
                latest_version = pkg_version_norm2info_sorted[0]
                logging.info("default to latest version: %s", latest_version[0])
                return latest_version[1]

    def _get_pkg_fname(self, pkg_name, pkg_version, suffix='zip'):
        return '%s.%s.%s' % (pkg_name, pkg_version, suffix)

    def download(self, pkg_name, pkg_version=None, outdir=None, binary=False, with_dep=False):
        # maybe extract the download link and metadata from json description
        # metadata from packagist, for the whole package
        # http://repo.packagist.org/p/google/protobuf%2433e4a753c56e2dfb44962115259d93682cf3d2f8b33e4a7af972bcd8a0513ef2.json
        # reference id from the package metadata, can be used to construct the download URL.
        # https://api.github.com/repos/google/protobuf/zipball/48cb18e5c419ddd23d9badcfe4e9df7bde1979b2
        pkg_info = self.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
        if not ('package' in pkg_info and 'versions' in pkg_info['package']):
            logging.error("download: cannot find a download link for %s", pkg_name)
            return
        versions = pkg_info['package']['versions']
        version_info = self._get_version_info(versions=versions, pkg_version=pkg_version)
        if not version_info:
            logging.error("download: cannot get version info for %s ver %s", pkg_name, pkg_version)
            return
        dist_link = version_info['dist']['url']
        dist_type = version_info['dist']['type']
        download_fname = self._get_pkg_fname(pkg_name=self.get_sanitized_pkgname(pkg_name=pkg_name),
                                             pkg_version=version_info['version'], suffix=dist_type)
        download_cmd = ['wget', dist_link, '-O', download_fname]
        if binary:
            logging.warning("support for binary downloading is not added yet!")
        if with_dep:
            logging.warning("support for packing dependencies is not added yet!")
        exec_command('composer download (wget)', download_cmd, cwd=outdir)
        download_path = join(outdir, download_fname)
        if exists(download_path):
            return download_path
        logging.error("failed to download pkg %s ver %s", pkg_name, pkg_version)
        return None

    def _install_init(self, install_dir, sudo=False):
        # configure stability to be dev
        if sudo:
            init_cmd = ['sudo', 'composer', 'global', 'init', '--stability', 'dev', '--no-interaction']
        else:
            init_cmd = ['composer', 'init', '--stability', 'dev', '--no-interaction']
        exec_command('composer init', init_cmd, cwd=install_dir)

    def install(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, install_dir=None, outdir=None,
                sudo=False):
        # use composer require or composer install
        # printf '{\n\t"require": {\n\t\t"%s":"*.*"\n\t}\n}' $1 >> composer.json && php /usr/local/bin/composer install
        # how require command is implemented internally
        # https://github.com/composer/composer/blob/master/src/Composer/Command/RequireCommand.php
        # there is an extension that supports installing or writing to arbitrary path
        # https://github.com/composer/installers#current-supported-package-types
        self._install_init(install_dir=install_dir, sudo=sudo)
        if sudo:
            # You can use this to install CLI utilities globally, all you need is to add the COMPOSER_HOME/vendor/bin
            # dir to your PATH env var.
            # https://github.com/consolidation/cgr/issues/2
            install_cmd = ['sudo', 'composer', 'global', 'require', pkg_name]
        else:
            install_cmd = ['composer', 'require', pkg_name]
        if pkg_version:
            install_cmd += [pkg_version]
        install_cmd = self.decorate_strace(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace,
                                           trace_string_size=trace_string_size, sudo=sudo, outdir=outdir,
                                           command=install_cmd)
        exec_command('composer require', install_cmd, cwd=install_dir)

    def install_file(self, infile, trace=False, trace_string_size=1024, sudo=False, install_dir=None, outdir=None):
        logging.error("support for install_file is not added yet!")

    def uninstall(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                  outdir=None):
        uninstall_cmd = ['composer', 'remove', pkg_name]
        if pkg_version:
            # there is no need to specify version during uninstall
            pass
        if sudo:
            uninstall_cmd = ['sudo'] + uninstall_cmd
        uninstall_cmd = self.decorate_strace(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace,
                                             trace_string_size=trace_string_size, sudo=sudo, outdir=outdir,
                                             command=uninstall_cmd)
        exec_command('composer remove', uninstall_cmd, cwd=install_dir)

    def get_metadata(self, pkg_name, pkg_version=None):
        # load cached metadata information
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            metadata_fname = self.get_metadata_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                     fmt=self.metadata_format)
            metadata_file = join(pkg_info_dir, metadata_fname)
            if exists(metadata_file):
                logging.warning("get_metadata: using cached metadata_file %s!", metadata_file)
                if self.metadata_format == 'json':
                    try:
                        return json.load(open(metadata_file, 'r'))
                    except:
                        logging.debug("fail to load metadata_file: %s, regenerating!", metadata_file)
                else:
                    logging.error("get_metadata: output format %s is not supported!", self.metadata_format)
                    return None
        try:
            # The easiest way to work with the packagist API
            # https://github.com/spatie/packagist-api/blob/master/src/Packagist.php
            # PHP API for Packagist
            # https://github.com/KnpLabs/packagist-api
            metadata_url = "https://packagist.org/packages/%s.json" % pkg_name
            metadata_content = requests.request('GET', metadata_url)
            pkg_info = json.loads(metadata_content.text)
        except:
            logging.error("fail in get_metadata for pkg %s, ignoring!", pkg_name)
            return None
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            metadata_fname = self.get_metadata_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                     fmt=self.metadata_format)
            metadata_file = join(pkg_info_dir, metadata_fname)
            if self.metadata_format == 'json':
                json.dump(pkg_info, open(metadata_file, 'w'), indent=2)
            else:
                logging.error("get_metadata: output format %s is not supported!", self.metadata_format)
        return pkg_info

    def get_versions(self, pkg_name, max_num=15, min_gap_days=30, with_time=False):
        pkg_info = self.get_metadata(pkg_name=pkg_name)
        if pkg_info is None or 'package' not in pkg_info:
            return []
        version_date = [(ver, dateutil.parser.parse(info['time'])) for ver, info in pkg_info['package']['versions'].items() if 'time' in info]
        # packagist versions may have '#' or '/' character in the version, skip them
        version_date = filter(lambda k: '#' not in k[0] and '/' not in k[0], version_date)
        return self.filter_versions(version_date=version_date, max_num=max_num, min_gap_days=min_gap_days,
                                    with_time=with_time)

    def get_author(self, pkg_name):
        pkg_info = self.get_metadata(pkg_name=pkg_name)
        if pkg_info is None or 'package' not in pkg_info:
            return {}
        maintainers = pkg_info['package'].get('maintainers', None)
        # each version has an author field
        authors = {ver: info.get('authors', None) for ver, info in pkg_info['package']['versions'].items() if 'time' in info}
        return {'authors': authors, 'maintainers': maintainers}

    def get_dep(self, pkg_name, pkg_version=None, flatten=False, cache_only=False):
        super(PackagistProxy, self).get_dep(pkg_name=pkg_name, pkg_version=pkg_version, flatten=flatten,
                                            cache_only=False)
        # load cached dependency information
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            if flatten:
                dep_fname = self.get_flatten_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            else:
                dep_fname = self.get_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            dep_file = join(pkg_info_dir, dep_fname)
            if exists(dep_file):
                logging.warning("get_dep: using cached dep_file %s!", dep_file)
                if self.dep_format == 'json':
                    try:
                        return json.load(open(dep_file, 'r'))
                    except:
                        logging.debug("fail to load dep_file: %s, regenerating!", dep_file)
                else:
                    logging.error("get_dep: output format %s is not supported!", self.dep_format)
                    return None
        if cache_only:
            return None
        # use composer require to get the dependencies
        temp_install_dir = tempfile.mkdtemp(prefix='get_dep-')
        self.install(pkg_name=pkg_name, pkg_version=pkg_version, install_dir=temp_install_dir)
        temp_composer_lock = join(temp_install_dir, 'composer.lock')
        dep_pkgs = {}
        flatten_dep_pkgs = {}
        if not exists(temp_composer_lock):
            logging.error("fail to get dependency for %s", pkg_name)
        else:
            try:
                pkg_lock_info = json.load(open(temp_composer_lock, 'r'))
                if 'packages' in pkg_lock_info and pkg_name in {pinfo['name'] for pinfo in pkg_lock_info['packages']}:
                    pkg_name2info = {dep_info['name']: dep_info for dep_info in pkg_lock_info['packages']}
                    flatten_dep_pkgs = {dep_info['name']: dep_info['version'] for dep_name, dep_info
                                        in pkg_name2info.items() if dep_info['name'] != pkg_name}
                    if 'require' in pkg_name2info[pkg_name]:
                        dep_pkg_names = pkg_name2info[pkg_name]['require'].keys()
                        dep_pkgs = {dep_name: dep_version for dep_name, dep_version in flatten_dep_pkgs.items()
                                    if dep_name in dep_pkg_names}
                else:
                    logging.error("no dependency including self is found for %s, info: %s", pkg_name, pkg_lock_info)
            except Exception as e:
                logging.error("failed while getting dependencies (%s) for pkg %s: %s!", flatten_dep_pkgs, pkg_name, str(e))
        logging.warning("%s has %d deps and %d flatten deps", pkg_name, len(dep_pkgs), len(flatten_dep_pkgs))
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            dep_fname = self.get_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            dep_file = join(pkg_info_dir, dep_fname)
            flatten_dep_fname = self.get_flatten_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            flatten_dep_file = join(pkg_info_dir, flatten_dep_fname)
            if self.dep_format == 'json':
                json.dump(dep_pkgs, open(dep_file, 'w'), indent=2)
                json.dump(flatten_dep_pkgs, open(flatten_dep_file, 'w'), indent=2)
            else:
                logging.error("get_dep: output format %s is not supported!", self.dep_format)
        # remove the installation directory
        shutil.rmtree(temp_install_dir)
        return flatten_dep_pkgs if flatten else dep_pkgs

    def install_dep(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                    outdir=None):
        # sanity check
        if install_dir is None and not sudo:
            logging.error("for packagist nonsudo, install_dir in install_dep is None, doesn't make sense!")
            return
        # get package dependency, and then install them
        dep_pkgs = self.get_dep(pkg_name=pkg_name, pkg_version=pkg_version)
        dep_pkgs_args = ['%s:%s' % (dep_name, dep_version) for dep_name, dep_version in dep_pkgs.items()]
        self._install_init(install_dir=install_dir, sudo=sudo)
        if sudo:
            install_dep_cmd = ['sudo', 'composer', 'global', 'require'] + dep_pkgs_args
        else:
            install_dep_cmd = ['composer', 'require'] + dep_pkgs_args
        install_dep_cmd = self.decorate_strace(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace,
                                               trace_string_size=trace_string_size, sudo=sudo, outdir=outdir,
                                               command=install_dep_cmd, is_dep=True)
        exec_command('composer install dependency', install_dep_cmd, cwd=install_dir)

    def has_install(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        return True

    def test(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        pass

    def has_test(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        return False

    def _get_composer_root(self, sudo, install_dir):
        if not sudo and install_dir is None:
            logging.error("for packagist nonsudo, install_dir in main is None, doesn't make sense!")
            return
        if sudo:
            composer_root = expanduser('~/.composer')
        else:
            composer_root = install_dir
        return composer_root

    def main(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        # assume that the package is installed and check for folder bin, and executables there
        main_cmd = ['python', 'main.py', pkg_name, '-m', 'packagist', '-r',
                    self._get_composer_root(sudo=sudo, install_dir=install_dir)]
        # get the binaries to run
        pkg_info = self.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
        versions = pkg_info['package']['versions']
        binaries = self._get_version_info(versions=versions, pkg_version=pkg_version)['bin']
        for binary in binaries:
            main_cmd += ['-b', binary]
        exec_command('python main.py', main_cmd, cwd="pm_proxy/scripts", timeout=timeout)

    def has_main(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        """
        Note: Only scripts defined in the root package's composer.json are executed. If a dependency of the root
        package specifies its own scripts, Composer does not execute those additional scripts.
        """
        pkg_info = self.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
        if not ('package' in pkg_info and 'versions' in pkg_info['package']):
            logging.error("has_main: cannot get version info for %s", pkg_name)
            return False
        versions = pkg_info['package']['versions']
        version_info = self._get_version_info(versions=versions, pkg_version=pkg_version)
        if not version_info:
            logging.error("has_main: cannot get version info for %s ver %s", pkg_name, pkg_version)
            return False
        return 'bin' in version_info

    def exercise(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                 outdir=None, timeout=None):
        # run the php script created for package exercise.
        composer_root = self._get_composer_root(sudo=sudo, install_dir=install_dir)
        exercise_cmd = ['php', 'exercise.php', pkg_name]
        # require(pkg_name) and trigger the events or initialize its global classes or objects
        exercise_src_location = 'pm_proxy/scripts/exercise.php'
        exercise_tgt_location = join(composer_root, 'exercise.php')
        if sudo:
            # FIXME: ~/.composer is generated by sudo user and requires sudo privilege to write to it
            copyfile_cmd = ['sudo', 'cp', exercise_src_location, exercise_tgt_location]
            exec_command('copy exercise.php', copyfile_cmd)
        else:
            shutil.copyfile(exercise_src_location, exercise_tgt_location)
        # parse dependencies and install them
        dep_names = json.load(open('pm_proxy/scripts/composer.json', 'r'))['require']
        for dep_name in dep_names:
            self.install(pkg_name=dep_name, install_dir=composer_root, sudo=sudo)
        dump_classmap_command = ['composer', 'dumpautoload', '--optimize']
        if sudo:
            dump_classmap_command = ['sudo'] + dump_classmap_command
        exec_command('dump classmap', dump_classmap_command, cwd=composer_root)
        exec_command('php exercise.php', exercise_cmd, cwd=composer_root, timeout=timeout)

    def has_exercise(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        pkg_info = self.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
        if not ('package' in pkg_info and 'type' in pkg_info['package']):
            logging.error("has_exercise: cannot get exercise info for %s", pkg_name)
            return False
        # FIXME: not sure if this is correct or not
        return pkg_info['package']['type'] == 'library'
