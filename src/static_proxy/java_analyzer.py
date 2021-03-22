import logging
from os.path import isdir, dirname, join, basename, splitext
from util.enum_util import LanguageEnum
from util.job_util import exec_command, read_proto_from_file, write_proto_to_file
from util.compress_files import get_file_with_meta
from static_base import StaticAnalyzer
from proto.python.ast_pb2 import PkgAstResults


class JavaAnalyzer(StaticAnalyzer):
    def __init__(self):
        super(JavaAnalyzer, self).__init__()
        self.language = LanguageEnum.java

    def astgen(self, inpath, outfile, root=None, configpath=None, pkg_name=None, pkg_version=None, evaluate_smt=False):
        analyze_path, is_decompress_path, outfile, root, configpath = self._sanitize_astgen_args(
            inpath=inpath, outfile=outfile, root=root, configpath=configpath, language=self.language)

        astgen_cmd = ['java', '-jar', 'target/astgen-java-1.0.0-jar-with-dependencies.jar', '-inpath', analyze_path,
                      '-outfile', outfile, '-config', configpath]
        if isdir(analyze_path):
            raise Exception("Soot doesn't take a directory as input: %s", analyze_path)

        if analyze_path.endswith((".apk", ".dex")):
            # processing android apps requires android.jar
            astgen_cmd.extend(['-android_jar_dir', 'platforms/'])
            if analyze_path.endswith(".apk"):
                astgen_cmd.extend(['-intype', 'APK' '-process_dir', analyze_path])
            elif analyze_path.endswith(".dex"):
                astgen_cmd.extend(['-intype', 'DEX', '-process_dir', analyze_path])
        elif analyze_path.endswith((".java",)):
            astgen_cmd.extend(['-intype', 'SOURCE', '-process_dir', dirname(analyze_path)])
        elif analyze_path.endswith((".class",)):
            astgen_cmd.extend(['-intype', 'CLASS', '-process_dir', dirname(analyze_path)])
        elif analyze_path.endswith((".jar",)):
            # this is the default input type
            astgen_cmd.extend(['-intype', 'JAR', '-process_dir', analyze_path])
        elif analyze_path.endswith((".aar",)):
            # aar contains /classes.jar
            # https://developer.android.com/studio/projects/android-library
            astgen_cmd.extend(['-android_jar_dir', 'platforms/'])
            aar_file = get_file_with_meta(analyze_path)
            class_jar_content = aar_file.accessor.read('classes.jar')
            analyze_path_jar = join(dirname(analyze_path), splitext(basename(analyze_path))[0] + '.jar')
            open(analyze_path_jar, 'wb').write(class_jar_content)
            astgen_cmd.extend(['-intype', 'JAR', '-process_dir', analyze_path_jar])
        elif analyze_path.endswith((".war",)):
            # war contains lots of jar files in /WEB-INF/lib/
            # http://one-jar.sourceforge.net/
            logging.error("Not handling .war file yet: %s", analyze_path)
        else:
            logging.error("Input path has unexpected suffix: %s", analyze_path)
        # root is not used here
        if pkg_name is not None:
            astgen_cmd.extend(['-package_name', pkg_name])
        if pkg_version is not None:
            astgen_cmd.extend(['-package_version', pkg_version])
        exec_command("java astgen", astgen_cmd, cwd="static_proxy/astgen-java")

        # optionally evaluate smt formula
        if evaluate_smt:
            resultpb = PkgAstResults()
            read_proto_from_file(resultpb, filename=outfile, binary=False)
            satisfied = self._check_smt(astgen_results=[resultpb], configpath=configpath)
            resultpb.pkgs[0].config.smt_satisfied = satisfied
            write_proto_to_file(resultpb, filename=outfile, binary=False)

        # clean up residues
        self._cleanup_astgen(analyze_path=analyze_path, is_decompress_path=is_decompress_path)

    def taint(self, inpath, outfile, configpath=None, pkg_name=None, pkg_version=None):
        analyze_path, is_decompress_path, outfile, root, configpath = self._sanitize_astgen_args(
            inpath=inpath, outfile=outfile, root=None, configpath=configpath, language=self.language)
        # FIXME: modify soot-infoflow to support jar input
        apk_path = None
        sources_sinks_file = None
        taint_cmd = ['java', '-jar', 'soot-infoflow-cmd/target/soot-infoflow-cmd-jar-with-dependencies.jar',
                     '-a', apk_path, '-p', 'platforms/', '-s', sources_sinks_file]
        # -o outfile -c configpath
        if isdir(analyze_path):
            raise Exception("FlowDroid doesn't take a directory as input: %s", analyze_path)

        if analyze_path.endswith((".apk",)):
            pass
        elif analyze_path.endswith((".dex", ".jar", ".aar")):
            pass
        elif analyze_path.endswith((".war",)):
            logging.error("Not handling .war file yet: %s", analyze_path)
        else:
            logging.error("Input path has unexpected suffix: %s", analyze_path)
        exec_command("java taint", taint_cmd, cwd="static_proxy/flowdroid")

        # clean up residues
        self._cleanup_astgen(analyze_path=analyze_path, is_decompress_path=is_decompress_path)

    def danger(self, pkg_name, outdir, cache_dir=None, configpath=None, pkg_version=None):
        pass

