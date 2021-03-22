import os
import logging
from os.path import join

from util.job_util import read_proto_from_file, write_proto_to_file, exec_command
from util.enum_util import LanguageEnum
from static_base import StaticAnalyzer
from brakeman_run import brakeman_run
from proto.python.ast_pb2 import PkgAstResults, AstLookupConfig
from proto.python.module_pb2 import ModuleStatic


class RubyAnalyzer(StaticAnalyzer):
    def __init__(self):
        super(RubyAnalyzer, self).__init__()
        self.language = LanguageEnum.ruby

    def astgen(self, inpath, outfile, root=None, configpath=None, pkg_name=None, pkg_version=None, evaluate_smt=False):
        analyze_path, is_decompress_path, outfile, root, configpath = self._sanitize_astgen_args(
            inpath=inpath, outfile=outfile, root=root, configpath=configpath, language=self.language)

        configpb = AstLookupConfig()
        configpath_bin = configpath + '.bin'

        # create binary config from text format
        self._pb_text_to_bin(proto=configpb, infile=configpath, outfile=configpath_bin)
        astgen_cmd = ['ruby', 'astgen.rb', '-c', configpath_bin, '-i', analyze_path, '-o', outfile]
        if root is not None:
            astgen_cmd.extend(['-b', root])
        if pkg_name is not None:
            astgen_cmd.extend(['-n', pkg_name])
        if pkg_version is not None:
            astgen_cmd.extend(['-v', pkg_version])
        exec_command("ruby astgen", astgen_cmd, cwd="static_proxy")

        # convert binary output to text format
        resultpb = PkgAstResults()
        read_proto_from_file(resultpb, filename=outfile, binary=True)

        # optionally evaluate smt formula
        if evaluate_smt:
            satisfied = self._check_smt(astgen_results=[resultpb], configpath=configpath)
            resultpb.pkgs[0].config.smt_satisfied = satisfied

        # save resultpb
        write_proto_to_file(resultpb, filename=outfile, binary=False)

        # clean up residues
        self._cleanup_astgen(analyze_path=analyze_path, is_decompress_path=is_decompress_path)

    def taint(self, inpath, outfile, configpath=None, pkg_name=None, pkg_version=None):
        analyze_path, is_decompress_path, outfile, _, configpath = self._sanitize_astgen_args(
            inpath=inpath, outfile=outfile, root=None, configpath=configpath, language=self.language)

        # perform static taint (brakeman) analysis
        brakeman_run(pkg_path=analyze_path, config_path=configpath, out_path=outfile)

        """
        # FIXME: this is a temporary fix for the input path problem in brakeman, i.e. brakeman will create a rails2
        # folder in dirname(analyze_path) and expects the caller to cleanup.
        analyze_path = join(analyze_path, os.listdir(analyze_path)[0])

        # convert the config to binary
        configpb = AstLookupConfig()
        configpath_bin = configpath + '.bin'

        # create binary config from text format
        self._pb_text_to_bin(proto=configpb, infile=configpath, outfile=configpath_bin)

        # perform static taint analysis
        taint_cmd = ['brakeman', analyze_path, '-o', outfile, '-c', configpath_bin]
        exec_command('ruby taint', taint_cmd, cwd="static_proxy/brakeman")
        pkg_static = ModuleStatic()
        read_proto_from_file(pkg_static, outfile, binary=True)
        logging.warning("taint analysis results: %s", pkg_static)

        # save resultpb
        write_proto_to_file(pkg_static, filename=outfile, binary=False)

        os.remove(configpath_bin)
        """
        # clean up residues
        self._cleanup_astgen(analyze_path=analyze_path, is_decompress_path=is_decompress_path)

    def danger(self, pkg_name, outdir, cache_dir=None, configpath=None, pkg_version=None):
        pass
