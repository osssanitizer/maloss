#!/usr/bin/python3


#################################################################
# Configuration parser
#################################################################
class Config(object):
    __configParser = None

    def __init__(self, file_path="config"):
        try:
            import configparser
            self.__configParser = configparser.RawConfigParser()
            self.__configParser.read(file_path)

        except ImportError as ie:
            raise Exception("ConfigParser module not available. Please install")

        except Exception as e:
            raise Exception("Error parsing " + file_path + ": " + str(e))

    def get(self, opt, sec="Main"):
        if not self.__configParser:
            return None
        try:
            return self.__configParser.get(sec, opt)
        except Exception as e:
            return None

