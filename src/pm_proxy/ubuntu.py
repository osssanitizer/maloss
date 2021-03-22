from pm_proxy.pm_base import PackageManagerProxy


class UbuntuProxy(PackageManagerProxy):
    # https://packages.ubuntu.com/
    def download(self, pkg_name, pkg_version=None, outdir=None, binary=False, with_dep=False):
        pass

    def get_dep(self, pkg_name, pkg_version=None, flatten=False, cache_only=False):
        # use apt-rdepends, e.g. apt-rdepends -r bash
        # https://askubuntu.com/questions/128524/how-to-list-dependent-packages-reverse-dependencies
        pass

    def install(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, install_dir=None, outdir=None,
                sudo=False):
        pass
