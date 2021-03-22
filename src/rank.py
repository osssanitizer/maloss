import csv
import sys
import logging
import pandas as pd
from pandas import *
import os


def traversing_csv(output_name_template='rank_%s.csv'):
    # print type(input)

    directory = '/home/salini/maloss/rubygems_edit'
    current_piece = 0
    output_path = '/home/salini/maloss/rubygems_rank/'

    for root, dirs, files in os.walk(directory):
        files = sorted(files)
        for it in range(len(files)):
            input = os.path.join(directory, files[it])
            rank = []
            print(it, files[it])

            with open(input, 'rb') as file:
                print("inside")

                reader = csv.reader(file, delimiter=',')
                # print reader
                x = reader.next()
                # rest = [rowA for rowA in reader]
                # print x
                # print rest[0][0]
                i, j = 0, 0
                rank = []
                s = 1

                for row in reader:
                    j = 0
                    # print row
                    for column in row:
                        rank_row = []
                        if j == 0:
                            name = column

                        try:
                            if int(column) <= 3 and (i != j):
                                rank_row.append(name)
                                rank_row.append(x[j])
                                rank_row.append(column)
                        except Exception as e:
                            s = 0

                        j = j + 1

                        if rank_row != []:
                            # print rank_row
                            rank.append(rank_row)
                    i = i + 1
                print(rank)
            outfile = os.path.join(output_path, output_name_template % current_piece)
            current_piece = current_piece + 1

            with open(outfile, "a") as f:
                writer = csv.writer(f)
                writer.writerows(rank)


traversing_csv()
