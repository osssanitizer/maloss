import pandas as pd
import sys
import csv
from multiprocessing import Pool
from functools import partial


def check_if_substring(first, second):
    if first == second: return False;
    if second.find(first) == -1:
        return False
    else:
        return True


def check_if_substring_array(first, second_arr):
    result = []
    for ele in second_arr:
        temp = []

        if check_if_substring(first, ele) == True:
            temp.append(first)
            temp.append(ele)
            # temp.append(check_if_substring(first,ele))
            result.append(temp)

    return result


def combo_squatting(source, target, outfile):
    src_df = pd.read_csv(source)
    src_package_column = src_df.package_name
    '''
    if target:
        tgt_df = pd.read_csv(target)
        tgt_package_column = tgt_df.package_name
    else:
        # default to source
        tgt_package_column = src_package_column
    '''''

    new_src_package_column = []

    # print len(src_package_column)
    for b in range(0, len(src_package_column)):
        # print b
        if len(str(src_package_column[b])) > 5:
            # print src_package_column[b]
            new_src_package_column.append(src_package_column[b])

    # Do partial on the function to make it take only one argument
    check_if_substring_array_partial = partial(check_if_substring_array,
                                               second_arr=[str(new_src_package_column[b]) for b in
                                                           range(0, len(new_src_package_column))])

    pool = Pool(processes=24)
    try:

        results = pool.map(check_if_substring_array_partial,
                           [str(new_src_package_column[a]) for a in range(0, len(new_src_package_column))])

    except Exception as e:
        print(e)
    pool.close()
    pool.join()
    # print results
    with open(outfile, "a") as f:
        writer = csv.writer(f)
        for result in results:
            if result != []:
                # print result

                writer.writerows(result)


combo_squatting(sys.argv[1], sys.argv[2], sys.argv[3])
