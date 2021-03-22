from pm_proxy.pm_base import PackageManagerProxy


class DockerHubProxy(PackageManagerProxy):
    def __init__(self, registry=None, cache_dir=None, isolate_pkg_info=False):
        super(DockerHubProxy, self).__init__()
        self.registry = registry
        self.cache_dir = cache_dir
        self.isolate_pkg_info = isolate_pkg_info
        self.metadata_format = 'json'
        self.dep_format = 'json'

    def download(self, pkg_name, pkg_version=None, outdir=None, binary=False, with_dep=False):
        pass

    def install(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, install_dir=None, outdir=None,
                sudo=False):
        pass

    def main(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        pass

    def exercise(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                 outdir=None, timeout=None):
        pass

