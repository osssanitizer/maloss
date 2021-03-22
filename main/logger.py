#!/usr/bin/python3

import time
import logging
import os


###########################################################
# Logging
###########################################################
class Logger:
    __l = None

    def get(self):
        return self.__l

    def __init__(self, name, path=None, level=logging.INFO, mode='w',
                 formatter='%(asctime)s, %(msecs)d, %(name)s, %(process)d, %(levelname)s, %(message)s'):
        try:
            l = logging.getLogger(name)
            if not l.handlers:
                l.setLevel(level)

                ts = time.strftime('%Y_%m_%d_%H_%M_%S')
                if path:
                    if not name.startswith("Dump"):
                        path += '_' + str(os.getpid()) + '_' + ts + ".log"
                    handler = logging.FileHandler(path, mode=mode)
                    # also emit any warning/error/critical msgs to console
                    console = logging.StreamHandler()
                    console.setLevel(logging.WARNING)
                    console.setFormatter(logging.Formatter('%(message)s'))
                    l.addHandler(console)
                else:
                    handler = logging.StreamHandler()

                handler.setFormatter(logging.Formatter(formatter))
                l.addHandler(handler)
            self.__l = l

        except Exception as e:
            raise Exception("Error setting up '" + name + "' logger: " + str(e))
