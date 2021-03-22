#!/usr/bin/python
# add path to the proto messages
import argparse
import sys
sys.path.append('../../')

import proto.python.ast_pb2 as ast_pb2
import proto.python.module_pb2 as module_pb2
import proto.python.behavior_pb2 as behavior_pb2
import proto.python.info_pb2 as info_pb2
import proto.python.class_sig_pb2 as class_sig_pb2
from google.protobuf.text_format import MessageToString, Merge


def write_proto_to_file(proto, filename, binary=True):
    if binary:
        f = open(filename, "wb")
        f.write(proto.SerializeToString())
        f.close()
    else:
        f = open(filename, "w")
        f.write(MessageToString(proto))
        f.close()


def read_proto_from_file(proto, filename, binary=True):
    if binary:
        f = open(filename, "rb")
        proto.ParseFromString(f.read())
        f.close()
    else:
        f = open(filename, "r")
        Merge(f.read(), proto)
        f.close()


def convert(infile, outfile, proto_type, reverse=False):
    if hasattr(ast_pb2, proto_type):
        proto = getattr(ast_pb2, proto_type)()
    elif hasattr(module_pb2, proto_type):
        proto = getattr(module_pb2, proto_type)()
    else:
        raise Exception("proto_type %s is not available in ast_pb2 or module_pb2" % proto_type)
    if reverse:
        read_proto_from_file(proto=proto, filename=infile, binary=True)
        write_proto_to_file(proto=proto, filename=outfile, binary=False)
    else:
        read_proto_from_file(proto=proto, filename=infile, binary=False)
        write_proto_to_file(proto=proto, filename=outfile, binary=True)


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="convert", description="Convert protobuf message from text to binary format and vice versa.")
    parser.add_argument("-i", "--infile", required=True, help="Path to the input file.")
    parser.add_argument("-o", "--outfile", required=True, help="Path to the output file.")
    choices = [c for c in dir(ast_pb2) + dir(module_pb2) + dir(behavior_pb2) + dir(info_pb2) + dir(class_sig_pb2)
            if '_' not in c and not c.isupper() and c != 'sys']
    parser.add_argument("-t", "--type", choices=choices, required=True, help="Type of the protobuf message to convert.")
    parser.add_argument("-r", "--reverse", action="store_true", help="Convert binary to text format.")

    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    convert(args.infile, args.outfile, args.type, args.reverse)


