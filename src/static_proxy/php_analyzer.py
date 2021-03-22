import os
import logging

from util.job_util import read_proto_from_file, write_proto_to_file, exec_command
from util.enum_util import LanguageEnum
from static_base import StaticAnalyzer
from progpilot_run import progpilot_run
from proto.python.ast_pb2 import PkgAstResults, AstLookupConfig
from proto.python.module_pb2 import ModuleStatic


class PhpAnalyzer(StaticAnalyzer):
    def __init__(self):
        super(PhpAnalyzer, self).__init__()
        self.language = LanguageEnum.php

    def astgen(self, inpath, outfile, root=None, configpath=None, pkg_name=None, pkg_version=None, evaluate_smt=False):
        analyze_path, is_decompress_path, outfile, root, configpath = self._sanitize_astgen_args(
            inpath=inpath, outfile=outfile, root=root, configpath=configpath, language=self.language)

        # ./vendor/nikic/php-parser/bin/php-parse  -d ../testdata/test-eval-exec.php
        configpb = AstLookupConfig()
        configpath_bin = configpath + '.bin'

        # create binary config from text format
        self._pb_text_to_bin(proto=configpb, infile=configpath, outfile=configpath_bin)
        astgen_cmd = ['php', 'astgen.php', '-c', configpath_bin, '-i', analyze_path, '-o', outfile]
        if root is not None:
            astgen_cmd.extend(['-b', root])
        if pkg_name is not None:
            astgen_cmd.extend(['-n', pkg_name])
        if pkg_version is not None:
            astgen_cmd.extend(['-v', pkg_version])
        exec_command("php astgen", astgen_cmd, cwd="static_proxy")

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

        # perform static taint analysis
        progpilot_run(pkg_path=analyze_path, config_path=configpath, out_path=outfile)

        # clean up residues
        self._cleanup_astgen(analyze_path=analyze_path, is_decompress_path=is_decompress_path)

    def danger(self, pkg_name, outdir, cache_dir=None, configpath=None, pkg_version=None):
        """
        Analyze the package for usage of danger API.

        The danger API are mostly also sinks, but not all of them.
        """
        pass
