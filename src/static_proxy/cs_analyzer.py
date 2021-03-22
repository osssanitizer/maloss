import logging
from os.path import basename

from util.enum_util import LanguageEnum
from util.job_util import read_proto_from_file, write_proto_to_file, exec_command
from static_base import StaticAnalyzer
from proto.python.ast_pb2 import PkgAstResults, AstLookupConfig
from proto.python.module_pb2 import ModuleStatic


class CsAnalyzer(StaticAnalyzer):
    def __init__(self):
        super(CsAnalyzer, self).__init__()
        self.language = LanguageEnum.csharp

    def astgen(self, inpath, outfile, root=None, configpath=None, pkg_name=None, pkg_version=None, evaluate_smt=False):
        pass

    def taint(self, inpath, outfile, configpath=None, pkg_name=None, pkg_version=None):
        pass

    def danger(self, pkg_name, outdir, cache_dir=None, configpath=None, pkg_version=None):
        pass
