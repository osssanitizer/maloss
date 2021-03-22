# Names for built-in types
# https://docs.python.org/2/library/types.html
import importlib
import pkgutil
import types
import sys
import logging
import atexit
import pkg_resources
import timeout_decorator

data_types = {types.NoneType, types.TypeType, types.BooleanType, types.IntType, types.LongType, types.FloatType,
              types.ComplexType, types.StringType, types.UnicodeType, types.TupleType, types.ListType, types.DictType,
              types.DictionaryType, types.FileType, types.StringTypes, types.XRangeType, types.SliceType,
              types.EllipsisType, types.CodeType, types.BufferType, types.DictProxyType, types.NotImplementedType,}
debug_types = {types.TracebackType, types.FrameType,}
descriptor_types = {types.GetSetDescriptorType, types.MemberDescriptorType,}
function_types = {types.FunctionType, types.LambdaType, types.MethodType, types.UnboundMethodType,
                  types.BuiltinFunctionType, types.BuiltinMethodType,}
class_types = {types.ClassType,}
generator_types = {types.GeneratorType,}
instance_types = {types.InstanceType,}
module_types = {types.ModuleType,}


def get_all_modules(root_module):
    """
    A module is a single file (or files) that are imported under one import and used. e.g.
    A package is a collection of modules in directories that give a package hierarchy.

    It's important to keep in mind that all packages are modules, but not all modules are packages.
    Or put another way, packages are just a special kind of module. Specifically, any module that contains a __path__
    attribute is considered a package.

    Ref: https://stackoverflow.com/questions/7948494/whats-the-difference-between-a-python-module-and-a-python-package
    Ref: https://stackoverflow.com/questions/1707709/list-all-the-modules-that-are-part-of-a-python-package
    """
    #
    #
    root_path = root_module.__path__
    logging.warning("checking submodules of root module %s path %s", root_module, root_path)
    # breath search for all submodules
    visited, queue = set(), [root_module]
    while queue:
        vertex = queue.pop(0)
        if vertex not in visited:
            visited.add(vertex)
            if hasattr(vertex, '__path__') and vertex.__path__[0].startswith(root_path[0]):
                submodules = set()
                for importer, sub_mod_name, sub_mod_ispkg in pkgutil.iter_modules(vertex.__path__):
                    try:
                        logging.warning("loading submodule %s of module %s", sub_mod_name, vertex)
                        sub_mod = importer.find_module(sub_mod_name).load_module(sub_mod_name)
                        submodules.add(sub_mod)
                    except Exception as e:
                        # FIXME: error message to be addressed - Attempted relative import in non-package
                        logging.error("could not submodule %s of module %s: %s", sub_mod_name, vertex, str(e))
                queue.extend(submodules)
            else:
                logging.debug("ignoring module %s", vertex)
    logging.warning("loaded %d modules in total", len(visited))
    return visited


@timeout_decorator.timeout(20)
def try_init_module_attr(mod, attr):
    try:
        mod_attr = getattr(mod, attr)
        logging.warning("checking attr %s, type %s", attr, type(mod_attr))
        if type(mod_attr) in data_types | debug_types | descriptor_types:
            logging.debug("do nothing for data/debug/descriptor types")
        elif type(mod_attr) in function_types | class_types:
            logging.debug("invoke the function (__init__ for class types) with no arguments")
            mod_attr()
        elif type(mod_attr) in generator_types:
            logging.debug("iterate through generator types")
            list(mod_attr)
        elif type(mod_attr) in instance_types | module_types:
            logging.debug("do nothing for instance/module types")
        else:
            raise Exception("Unknown type %s" % type(mod_attr))

    except Exception as e:
        logging.error("Error init mod %s attr %s: %s", mod, attr, str(e))


def try_init_module_attrs(mod):
    # check module
    if type(mod) not in instance_types | module_types:
        logging.warning("ignoring mod %s due to type", mod)
        return
    else:
        logging.warning("checking mod %s, type %s", mod, type(mod))

    # iterate through attributes
    logging.warning("get mod %s attributes and try to initialize them", mod)
    # FIXME: the init may report errors due to missing imports
    for attr in dir(mod):
        try:
            try_init_module_attr(mod, attr)
        except Exception as e:
            logging.error("Error init mod %s: %s", mod, str(e))


@atexit.register
def handle_remaining_modules():
    if all_modules is None:
        return

    logging.critical("the program is trying to exit! run the remaining jobs before it exits!")
    remaining_modules = all_modules - completed_modules
    for module in remaining_modules:
        completed_modules.add(module)
        try:
            try_init_module_attrs(mod=module)
        except Exception as e:
            logging.error("Error checking module %s: %s", module, str(e))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: %s PKG_NAME" % sys.argv[0])
        exit(1)

    global all_modules
    global completed_modules
    all_modules = None
    completed_modules = set()

    # import a module by its name
    # https://stackoverflow.com/questions/14071135/import-file-using-string-as-name
    pkg_name = sys.argv[1]
    root_module_name = list(pkg_resources.get_distribution(pkg_name)._get_metadata('top_level.txt'))[0]
    root_module = importlib.import_module(root_module_name)
    all_modules = get_all_modules(root_module)

    # for each module, try to initialize its attributes
    for module in all_modules:
        completed_modules.add(module)
        try:
            try_init_module_attrs(mod=module)
        except Exception as e:
            logging.error("Error checking module %s: %s", module, str(e))

