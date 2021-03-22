import pickle
import sys

results = []


def getdependentsofpackage(pkg_manager, pkg_name):
    for pkg in G.predecessors(pkg_name):
        print pkg
        if pkg == pkg_manager:
            continue
        else:
            if pkg not in results:
                results.append(pkg)
            getdependentsofpackage(pkg_manager, pkg)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Invalid number of arguments \n Usage : program_name package_manager pkg_name"
        exit(0)
    # load the graph object
    pkg_manager = sys.argv[1]
    G = pickle.load(open(pkg_manager + "_dependency_graph_object.txt", "rb"))
    getdependentsofpackage(pkg_manager, sys.argv[2])

    if len(results) == 0:
        print "package does not have any dependents"
    else:
        print results
