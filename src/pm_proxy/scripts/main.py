import os
import sys
import logging
import argparse
import subprocess
import pkg_resources
import timeout_decorator

from os.path import join, exists, basename


@timeout_decorator.timeout(20)
def try_entry_cmd(entry_cmd, cwd=None):
    logging.warning("calling the entry script: %s", entry_cmd)

    # execute the command without argments
    logging.info("running command %s", entry_cmd)
    subprocess.call(entry_cmd, cwd=cwd)

    # execute the command with help flag
    entry_cmd += ['--help']
    logging.info("running command %s", entry_cmd)
    subprocess.call(entry_cmd, cwd=cwd)


def pypi_main(pkg_name):
    pkg_dist = pkg_resources.get_distribution(pkg_name)
    significant_groups = {'console_scripts', 'gui_scripts'}
    entry_points = {k: v for k, v in pkg_dist.get_entry_map().items() if k in significant_groups}
    for entry_group, entry_scripts in entry_points.items():
        for entry_name, entry_parse in entry_scripts.items():
            entry_cmd = [entry_name]
            try:
                try_entry_cmd(entry_cmd=entry_cmd)
            except Exception as e:
                logging.error("error running command: %s", entry_cmd)


def rubygems_main(pkg_name):
    gem_path_cmd = ['gem', 'path', pkg_name.replace('-', '/')]
    gem_path = subprocess.check_output(gem_path_cmd).strip()
    bin_path = join(gem_path, 'bin')
    if not exists(bin_path):
        logging.error("bin path %s doesn't exist for pkg %s", bin_path, pkg_name)
        return
    bin_executables = [join(bin_path, executable) for executable in os.listdir(bin_path)]
    for entry_point in bin_executables:
        entry_cmd = [entry_point]
        try:
            try_entry_cmd(entry_cmd=entry_cmd)
        except Exception as e:
            logging.error("error running command: %s", entry_cmd)


def npmjs_main(pkg_name, binaries, scripts, root):
    logging.warning("running %d binaries and %d scripts from %s", len(binaries), len(scripts), pkg_name)
    # npx works outside package dir
    for binary in binaries:
        npx_cmd = ['npx', '--no-install', binary]
        try:
            try_entry_cmd(entry_cmd=npx_cmd, cwd=root)
        except Exception as e:
            logging.error("error running command: %s", npx_cmd)
    # npm run works inside package dir
    for script in scripts:
        npm_run_cmd = ['npm', 'run', script]
        try:
            try_entry_cmd(entry_cmd=npm_run_cmd, cwd=join(root, pkg_name))
        except Exception as e:
            logging.error("error running command: %s", npm_run_cmd)


def packagist_main(pkg_name, binaries, root):
    logging.warning("runinng %d binaries from %s", len(binaries), pkg_name)
    # composer
    vendor_bin_path = join(root, 'vendor/bin')
    bin_executables = [join(vendor_bin_path, basename(binary)) for binary in binaries]
    for entry_point in bin_executables:
        entry_cmd = [entry_point]
        try:
            try_entry_cmd(entry_cmd=entry_cmd)
        except Exception as e:
            logging.error("error running command: %s", entry_cmd)


def maven_main(pkg_name):
    maven_path_cmd = [pkg_name]
    raise Exception("maven main is not implemented yet!")


def nuget_main(pkg_name):
    nuget_path_cmd = [pkg_name]
    raise Exception("nuget main is not implemented yet!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="main.py", description="Run executables")
    parser.add_argument("package_name", help="Package name.")
    parser.add_argument("-m", "--package_manager", dest="package_manager", default="pypi",
                        choices=["pypi", "rubygems", "npmjs", "packagist", "maven", "nuget"],
                        help="Name of the package manager.")
    parser.add_argument("-b", "--binary", action='append', dest="binaries",
                        help="Binaries, specify multiple times if there are more than one binary")
    parser.add_argument("-s", "--script", action='append', dest="scripts",
                        help="Scripts, specify multiple times if there are more than one script")
    parser.add_argument("-r", "--root", dest="root",
                        help="Path to the root of each package manager, i.e. npm root [-g] output")
    args = parser.parse_args(sys.argv[1:])

    pkg_name = args.package_name
    pkg_manager = args.package_manager
    if pkg_manager == 'pypi':
        pypi_main(pkg_name)
    elif pkg_manager == 'rubygems':
        rubygems_main(pkg_name)
    elif pkg_manager == 'npmjs':
        npmjs_main(pkg_name=pkg_name, binaries=args.binaries, scripts=args.scripts, root=args.root)
    elif pkg_manager == 'packagist':
        packagist_main(pkg_name=pkg_name, binaries=args.binaries, root=args.root)
    elif pkg_manager == 'maven':
        maven_main(pkg_name=pkg_name)
    elif pkg_manager == 'nuget':
        nuget_main(pkg_name=pkg_name)
    else:
        raise Exception("Unexpected package manager: %s" % pkg_manager)

