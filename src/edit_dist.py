from __future__ import division
import sys
import csv
import shutil
import logging
import tempfile
from os.path import basename, join, dirname
from functools import partial
from itertools import product
from multiprocessing import Pool
import pandas as pd
from progressbar import ProgressBar

from util.enum_util import DistanceAlgorithmEnum
from metric.levenshtein_wrapper import levenshtein, levenshtein_batch


def edit_distance(s1, s2):
    # ref: https://stackoverflow.com/questions/2460177/edit-distance-in-python
    m=len(s1)+1
    n=len(s2)+1

    tbl = {}
    i, j = 0, 0
    for i in range(m):
        tbl[i, 0]= i
    for j in range(n):
        tbl[0, j]= j
    for i in range(1, m):
        for j in range(1, n):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            tbl[i, j] = min(tbl[i, j-1]+1, tbl[i-1, j]+1, tbl[i-1, j-1] + cost)
    return tbl[i, j]


def parser(source, target, outfile="output.csv", processes=1):
    src_df = pd.read_csv(source)
    src_package_column = src_df.get('package name')
    if target:
        tgt_df = pd.read_csv(target)
        tgt_package_column = tgt_df.get('package name')
    else:
        # default to source
        tgt_package_column = src_package_column
    ANS = []

    progress = ProgressBar()
    for a in progress(range(len(src_package_column))):
        first=str(src_package_column[a])
        newrow = []
        if processes == 1:
            for b in range(0, len(tgt_package_column)):
                second = str(tgt_package_column[b])
                try:
                    ans = edit_distance(first, second)
                    newrow.append(ans)
                except Exception as e:
                    logging.error(e, exc_info=True)

        else:
            partial_edit_distance = partial(edit_distance, s2=first)
            pool = Pool(processes=processes)
            results = pool.map(partial_edit_distance, [str(tgt_package_column[b]) for b in range(0, len(tgt_package_column))])
            pool.close()
            pool.join()
            for result in results:
                newrow.append(result)

        ANS.append(newrow)

    with open(outfile, "w") as f:
        writer = csv.writer(f)
        writer.writerow("pname".split() + list(tgt_package_column))
        writer.writerows(ANS)


def c_edit_distance(source, target, outfile, processes=1):
    src_df = pd.read_csv(source)
    src_package_column = src_df.get('package name')
    if target:
        tgt_df = pd.read_csv(target)
        tgt_package_column = tgt_df.get('package name')
    else:
        # default to source
        tgt_package_column = src_package_column
    ANS = []
    for a in range(len(src_package_column)):
        first = str(src_package_column[a])
        newrow = []
        if processes == 1:
            for b in range(0, len(tgt_package_column)):
                newrow.append(levenshtein(first, str(tgt_package_column[b])))
        else:
            partial_levenshtein = partial(levenshtein, strB=first)
            pool = Pool(processes=processes)
            results = pool.map(partial_levenshtein, [str(tgt_package_column[b]) for b in range(0, len(tgt_package_column))])
            pool.close()
            pool.join()
            for result in results:
                newrow.append(result)
        ANS.append(newrow)

    with open(outfile, "w") as f:
        writer = csv.writer(f)
        writer.writerow("pname".split() + list(tgt_package_column))
        writer.writerows(ANS)


def c_edit_distance_batch(source, target, outfile, processes=1):
    src_df = pd.read_csv(source)
    src_package_column = src_df.get('package name')
    if target:
        tgt_df = pd.read_csv(target)
        tgt_package_column = tgt_df.get('package name')
    else:
        # default to source
        tgt_package_column = src_package_column
    ANS = []
    partial_levenshtein_batch = partial(levenshtein_batch, sArr=[str(tgt_package_column[b]) for b in range(0, len(tgt_package_column))])
    pool = Pool(processes=processes)
    results = pool.map(partial_levenshtein_batch, [str(src_package_column[b]) for b in range(0, len(src_package_column))])
    pool.close()
    pool.join()
    for i, result in enumerate(results):
        ANS.append(str(src_package_column[i]).split() + list(result))

    with open(outfile, "w") as f:
        writer = csv.writer(f)
        writer.writerow("pname".split() + list(tgt_package_column))
        writer.writerows(ANS)


def edit_dist_worker(source, target, algorithm, outfile, threshold=2, processes=1):
    logging.warning("comparing %s to %s using algorithm %s, writing results to %s", source, target, algorithm, outfile)
    if algorithm == DistanceAlgorithmEnum.py_edit_distance:
        parser(source, target, outfile)
    elif algorithm == DistanceAlgorithmEnum.c_edit_distance:
        c_edit_distance(source, target, outfile, processes)
    elif algorithm == DistanceAlgorithmEnum.c_edit_distance_batch:
        c_edit_distance_batch(source, target, outfile, processes)
    else:
        raise Exception("Unhandled distance algorithm: %s" % algorithm)
    # TODO: save the output as sparse matrix
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.save_npz.html
    if threshold > 0:
        logging.warning("filtering %s with threshold %s", outfile, threshold)
        out_reader = csv.DictReader(open(outfile, 'r'))
        out_fieldnames = out_reader.fieldnames
        out_rows = list(out_reader)
        out_writer = csv.DictWriter(open(outfile, 'w'), fieldnames=out_fieldnames)
        out_writer.writeheader()
        for out_row in out_rows:
            out_row = {k:v for k, v in out_row.items() if k == "pname" or int(v) <= threshold}
            out_writer.writerow(out_row)


def split_csv_file(filepath, batch_size=10000):
    # if there is only file file, no need to split
    split_files = []
    split_dir = tempfile.mkdtemp(prefix='edit_dist-')
    split_reader = csv.DictReader(open(filepath, 'r'))
    split_rows = list(split_reader)
    # if the file is not big, then just use it as it is, and don't remove any folder
    if len(split_rows) <= batch_size:
        return None, [filepath]
    # if the file is big, then split it, and remove the temp folder after done processing
    for file_count, source_index in enumerate(range(0, len(split_rows), batch_size)):
        block_filepath = join(split_dir, basename(filepath) + '.%s' % file_count)
        block_writer = csv.DictWriter(open(block_filepath, 'w'), fieldnames=split_reader.fieldnames)
        block_writer.writeheader()
        for block_row in split_rows[source_index: min(source_index + batch_size, len(split_rows))]:
            block_writer.writerow(block_row)
        split_files.append(block_filepath)
    return split_dir, split_files


def transform_to_pair(infile, writer):
    # fieldnames = ['source', 'target', 'distance']
    oblock_reader = csv.DictReader(open(infile, 'r'))
    for row in oblock_reader:
        for key, value in row.items():
            if key != 'pname' and value:
                writer.writerow({'source': row['pname'], 'target': key, 'distance': value})


def edit_dist(source, target, algorithm, outfile, pair_outfile=None, batch_size=10000, threshold=2, processes=1):
    # TODO: merge the output files into one
    out_writer = None
    if pair_outfile:
        fieldnames = ['source', 'target', 'distance']
        out_writer = csv.DictWriter(open(pair_outfile, 'w'), fieldnames=fieldnames)
        out_writer.writeheader()
    if batch_size > 0:
        source_dir, source_files = split_csv_file(filepath=source, batch_size=batch_size)
        if target:
            target_dir, target_files = split_csv_file(filepath=target, batch_size=batch_size)
            for sblock, tblock in product(source_files, target_files):
                oblock = outfile + '.%s-%s' % (basename(sblock), basename(tblock))
                edit_dist_worker(source=sblock, target=tblock, algorithm=algorithm, outfile=oblock, threshold=threshold,
                                 processes=processes)
                if pair_outfile:
                    transform_to_pair(infile=oblock, writer=out_writer)
            if target_dir:
                shutil.rmtree(target_dir)
        else:
            for sblock, tblock in product(source_files, source_files):
                oblock = outfile + '.%s-%s' % (basename(sblock), basename(tblock))
                edit_dist_worker(source=sblock, target=tblock, algorithm=algorithm, outfile=oblock, threshold=threshold,
                                 processes=processes)
                if pair_outfile:
                    transform_to_pair(infile=oblock, writer=out_writer)
        if source_dir:
            shutil.rmtree(source_dir)
    else:
        edit_dist_worker(source=source, target=target, algorithm=algorithm, outfile=outfile, threshold=threshold,
                         processes=processes)
        if pair_outfile:
            transform_to_pair(infile=outfile, writer=out_writer)


if __name__ == "__main__":
    parser(sys.argv[1], sys.argv[2])
