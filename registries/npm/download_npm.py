import os
import sys
import glob
import json
import ijson
import logging
import datetime
import requests
import argparse
import subprocess

from functools import partial
from os.path import join, exists
from multiprocessing import Pool


def get_pkgs(outfile, with_data=False):
    if with_data:
        # get all packages with data
        subprocess.call(["wget", "https://replicate.npmjs.com/_all_docs?include_docs=true", "-O", outfile])
    else:
        # get all packages
        subprocess.call(["wget", "https://replicate.npmjs.com/_all_docs", "-O", outfile])


def get_pkgs_tarball(infile, outfile):
    # parse the document for tarball and download them in parallel
    logging.warning("loading %s", infile)
    npm_doc_f = open(infile, "r")
    pkg_objects = ijson.items(npm_doc_f, "rows.item")
    tarball_links = {}
    for pkg in pkg_objects:
        pkg_id = pkg["id"]
        if 'doc' in pkg and 'versions' in pkg['doc']:
            logging.warning("processing pkg %s with %d versions", pkg_id, len(pkg["doc"]["versions"]))
            tarball_links.setdefault(pkg_id, {})
            for pkg_version, version_info in pkg["doc"]["versions"].items():
                tarball_links[pkg_id][pkg_version] = version_info["dist"]["tarball"]
        else:
            logging.error("processing pkg %s with detail %s", pkg_id, pkg)

    json.dump(tarball_links, open(outfile, "w"))


def get_updates(latest_file, incr_file, outfile):
    # NOTE: potentially, we can listen to the streaming updates http://registry.npmjs.org/-/rss?descending=true&limit=50
    latest_tarball_links = json.load(open(latest_file, 'r'))
    incr_tarball_links = json.load(open(incr_file, 'r'))
    diff_tarball_links = {}
    pkg_diff_count = 0
    pkg_version_diff_count = 0
    for pkg in incr_tarball_links:
        if not pkg in latest_tarball_links:
            diff_tarball_links.setdefault(pkg, dict(incr_tarball_links[pkg]))
            pkg_diff_count += 1
            pkg_version_diff_count += len(incr_tarball_links[pkg])
        else:
            pkg_diff_versions = set(incr_tarball_links[pkg].keys()) - set(latest_tarball_links[pkg].keys())
            if len(pkg_diff_versions):
                pkg_diff_count += 1
                pkg_version_diff_count += len(pkg_diff_versions)
                diff_tarball_links.setdefault(pkg, {pkg_version: incr_tarball_links[pkg][pkg_version] for pkg_version in pkg_diff_versions})
    logging.warning("there are %d pkgs and %d pkg versions that are different in %s compared to latest file %s",
                    pkg_diff_count, pkg_version_diff_count, incr_file, latest_file)
    json.dump(diff_tarball_links, open(outfile, "w"))


def download_worker(pkg_info, outdir="npm/"):
    # NOTE: NPM has rate limits, we need to somehow handle them
    pkg_id, pkg_version, pkg_tarball = pkg_info
    writedir = join(outdir, pkg_id, pkg_version)
    if not exists(writedir):
        os.makedirs(writedir)
        try:
            logging.warning("downloading %s", pkg_tarball)
            subprocess.call(['wget', pkg_tarball], cwd=writedir)
        except Exception as e:
            logging.error("failed to download pkg: %s", pkg_info)
    else:
        logging.warning("processing already downloaded pkg: %s", pkg_info)
        if len(glob.glob(join(writedir, "*.tgz"))) == 0:
            logging.error("pkg %s was not downloaded successfully!", pkg_info)


def download(infile, outdir="npm/", skipfile=None, processes=32):
    # TODO: add support for progress tracking.
    tarball_links = json.load(open(infile, 'r'))
    logging.warning("there are %d packages to be downloaded", len(tarball_links))
    skip_pkg_versions = set()
    if skipfile and exists(skipfile):
        skip_tarballs = []
        for line in open(skipfile, 'r'):
            line = line.strip()
            if line.endswith('.tgz'):
                skip_tarballs.append(line)
        logging.warning("there are %d downloaded tarballs to be skipped", len(skip_tarballs))
        # https://registry.npmjs.org/vue-mobile-hotel-calendar-tmd/-/vue-mobile-hotel-calendar-tmd-1.8.3.tgz
        # https://registry.npmjs.org/@dmarksteinertickets/common/-/common-1.0.8.tgz
        # npm/@marklb/mb-hotkeys/1.0.5/mb-hotkeys-1.0.5.tgz
        # npm/ngx-material-timepicker-uwfm/2.6.0/ngx-material-timepicker-uwfm-2.6.0.tgz
        for tarball in skip_tarballs:
            pkg_id, pkg_version, fname = tarball.split('npm/', 1)[-1].rsplit('/', 2)
            skip_pkg_versions.add('%s:%s' % (pkg_id, pkg_version))
        logging.warning("there are %d downloaed package versions to be skipped", len(skip_pkg_versions))
    pkg_info_list = []
    pkg_version_total = 0
    for pkg_id, pkg_versions in tarball_links.items():
        pkg_version_total += len(pkg_versions)
        for pkg_version, pkg_tarball in pkg_versions.items():
            if '%s:%s' % (pkg_id, pkg_version) in skip_pkg_versions:
                continue
            pkg_info_list.append((pkg_id, pkg_version, pkg_tarball))
    logging.warning("there are %d tarballs to be downloaded before filtering and %d tarballs after filtering",
                    pkg_version_total, len(pkg_info_list))

    download_worker_partial = partial(download_worker, outdir=outdir)
    pool = Pool(processes=processes)
    pool.map(download_worker_partial, pkg_info_list)
    pool.close()
    pool.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('job', choices=['metadata', 'metadata_all', 'extract', 'download', 'sync_all', 'sync_incr'],
                        help='The name of the job to run.')
    parser.add_argument('--outdir', dest='outdir', default='/data/npm', help='Path to the output directory')
    parser.add_argument('--skipfile', dest='skipfile', default='/data/npm.files.tgz', help='Path to the file containing already downloaded tarballs to skip')
    parser.add_argument('--processes', dest='processes', type=int, default=32, help='Number of worker processes for downloading')
    args = parser.parse_args()

    if args.job == 'metadata':
        # get metadata
        get_pkgs(outfile=join(args.outdir, "all_npm_pkgs.json"))
    elif args.job == 'metadata_all':
        # get metadata with docs, 40G
        get_pkgs(outfile=join(args.outdir, "all_npm_pkgs_with_docs.json"), with_data=True)
    elif args.job == 'extract':
        # extract tarball, 1.4G
        get_pkgs_tarball(infile=join(args.outdir, "all_npm_pkgs_with_docs.json"),
                         outfile=join(args.outdir, "all_npm_pkgs_tarball.json"))
    elif args.job == 'download':
        # download tarball
        download(infile=join(args.outdir, "all_npm_pkgs_tarball.json"),
                 outdir=args.outdir, skipfile=args.skipfile, processes=args.processes)
    elif args.job == 'sync_all':
        logging.warning("performing full sync")
        # download metadata with docs, get all tarball links, download all tarballs
        get_pkgs(outfile=join(args.outdir, "all_npm_pkgs_with_docs.sync_all.json"), with_data=True)
        get_pkgs_tarball(infile=join(args.outdir, "all_npm_pkgs_with_docs.sync_all.json"),
                         outfile=join(args.outdir, "all_npm_pkgs_tarball.sync_all.json"))
        os.remove(join(args.outdir, "all_npm_pkgs_with_docs.sync_all.json"))
        download(infile=join(args.outdir, "all_npm_pkgs_tarball.sync_all.json"),
                 outdir=args.outdir, skipfile=args.skipfile, processes=args.processes)
    elif args.job == 'sync_incr':
        logging.warning("performing incremental sync")
        # check if the latest file exist
        latest_file = join(args.outdir, "all_npm_pkgs_tarball.latest.json")
        if not exists(latest_file):
            latest_file = join(args.outdir, "all_npm_pkgs_tarball.sync_all.json")
            if not exists(latest_file):
                raise Exception("No latest package list exist! Cannot perform incremental update!")
        incr_file = join(args.outdir, "all_npm_pkgs_tarball.sync_incr.json")
        # download metadata with docs, get all tarball links, diff with last tarball links, download the new tarballs
        get_pkgs(outfile=join(args.outdir, "all_npm_pkgs_with_docs.sync_incr.json"), with_data=True)
        get_pkgs_tarball(infile=join(args.outdir, "all_npm_pkgs_with_docs.sync_incr.json"), outfile=incr_file)
        os.remove(join(args.outdir, "all_npm_pkgs_with_docs.sync_incr.json"))
        diff_file = join(args.outdir, "all_npm_pkgs_tarball.diff.%s.json" % datetime.datetime.now().date())
        get_updates(latest_file=latest_file, incr_file=incr_file, outfile=diff_file)
        download(infile=diff_file, outdir=args.outdir, skipfile=args.skipfile, processes=args.processes)
        # update the latest file
        os.rename(incr_file, join(args.outdir, "all_npm_pkgs_tarball.latest.json"))
    else:
        raise Exception("Unhandled job: %s" % args.job)


if __name__=="__main__":
    main()
