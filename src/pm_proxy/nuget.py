import os
import json
import logging
import requests
import dateutil.parser
from os.path import join, exists

from util.job_util import exec_command
from pm_proxy.pm_base import PackageManagerProxy


class NugetProxy(PackageManagerProxy):
    # Understanding NuGet v3 feeds
    # https://emgarten.com/posts/understanding-nuget-v3-feeds
    def __init__(self, registry=None, cache_dir=None, isolate_pkg_info=False):
        super(NugetProxy, self).__init__()
        self.registry = registry
        self.cache_dir = cache_dir
        self.isolate_pkg_info = isolate_pkg_info
        self.metadata_format = 'json'
        self.dep_format = 'json'

    def _get_pkg_name(self, pkg_name, pkg_version=None, suffix='nupkg'):
        if pkg_version is None:
            return '%s.latest.%s' % (pkg_name, suffix)
        else:
            return '%s.%s.%s' % (pkg_name, pkg_version, suffix)

    def download(self, pkg_name, pkg_version=None, outdir=None, binary=False, with_dep=False):
        # Nuget v2 API for package downloading
        # https://www.nuget.org/api/v2/package/{packageID}/{packageVersion}
        # FIXME: move to v3 API
        if pkg_version:
            dist_link = "https://www.nuget.org/api/v2/package/%s/%s" % (pkg_name.lower(), pkg_version.lower())
        else:
            dist_link = "https://www.nuget.org/api/v2/package/%s" % pkg_name.lower()
        download_fname = self._get_pkg_name(pkg_name=pkg_name, pkg_version=pkg_version)
        download_cmd = ['wget', dist_link, '-O', download_fname]
        if not binary:
            # FIXME: add source download if available, suffix tar.gz?
            logging.warning("support for non-binary downloading is not added yet!")
        if with_dep:
            logging.warning("support for packing dependencies is not added yet!")
        exec_command('nuget download (wget)', download_cmd, cwd=outdir)
        download_path = join(outdir, download_fname)
        if exists(download_path):
            return download_path
        logging.error("failed to download pkg %s ver %s", pkg_name, pkg_version)
        return None

    def install(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, install_dir=None, outdir=None,
                sudo=False):
        # Managing the global packages, cache, and temp folders
        # https://docs.microsoft.com/en-us/nuget/consume-packages/managing-the-global-packages-and-cache-folders
        if sudo:
            # FIXME: nuget doesn't seem to have a separate global/sudo install
            install_cmd = ['sudo', 'nuget', 'install', pkg_name, '-DirectDownload']
        else:
            install_cmd = ['nuget', 'install', pkg_name, '-DirectDownload']
        if pkg_version:
            install_cmd += ['-Version', pkg_version]
        install_cmd = self.decorate_strace(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace,
                                           trace_string_size=trace_string_size, sudo=sudo, outdir=outdir,
                                           command=install_cmd)
        exec_command('nuget install', install_cmd, cwd=install_dir)

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
        # fetch metadata from json api
        if pkg_version:
            metadata_url = "https://api.nuget.org/v3/registration1/%s/%s.json" % (pkg_name.lower(), pkg_version.lower())
        else:
            metadata_url = "https://api.nuget.org/v3/registration1/%s/index.json" % pkg_name.lower()
        try:
            metadata_content = requests.request('GET', metadata_url)
            pkg_info = json.loads(metadata_content.text)
        except:
            logging.error("fail in get_metadata for pkg %s, ignoring!", pkg_name)
            return None
        # optionally cache metadata
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
        if pkg_info is None or 'items' not in pkg_info:
            return []
        # published, version
        version_date = []
        for versions_info in pkg_info['items']:
            for item_info in versions_info['items']:
                version_date.append((item_info['version'], dateutil.parser.parse(item_info['published'])))
        return self.filter_versions(version_date=version_date, max_num=max_num, min_gap_days=min_gap_days,
                                    with_time=with_time)

    def get_author(self, pkg_name):
        pkg_info = self.get_metadata(pkg_name=pkg_name)
        if pkg_info is None or 'items' not in pkg_info:
            return {}
        authors = set()
        for versions_info in pkg_info['items']:
            if 'items' not in versions_info:
                continue
            authors.update([item_info['authors'] for item_info in versions_info['items']])
        return {'authors': list(authors)}

    def get_dep(self, pkg_name, pkg_version=None, flatten=False, cache_only=False):
        # install the package and check what are the dependencies
        pass

    def install_dep(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                    outdir=None):
        pass

    def has_install(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        return True

    def test(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        pass

    def has_test(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        return False

    def main(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        pass

    def has_main(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        pass

    def exercise(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                 outdir=None, timeout=None):
        pass

    def has_exercise(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        pass
