import networkx as nx
import json
import pickle
import sys

def save_object(obj, filename):
    with open(filename, 'wb') as output:  # Overwrites any existing file.
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)


def build_graph(filename,root):
    G = nx.DiGraph()

    G.add_node(root)
    pkg_without_dependency = []
    with open(filename) as json_file:
        data = json.load(json_file)
        for p1 in data[root+'_package']:
            pkg_name = p1['name']
            if p1['name'] not in G:
                G.add_node(pkg_name)
                G.add_edges_from([(root,pkg_name)])
                dep = p1['dependencies']

                if dep:
                    for value in dep:
                        if value not in G:
                            G.add_node(value)
                            G.add_edges_from([(pkg_name,value)])
                        else:
                            G.add_edges_from([(pkg_name,value)])
                else:
                    if pkg_name not in pkg_without_dependency:
                        pkg_without_dependency.append(pkg_name)
            else:
                dep = p1['dependencies']
                if dep:
                    for value in dep:
                        if value not in G:
                            G.add_node(value)

                            G.add_edges_from([(pkg_name,value)])
                            print "edge added between",pkg_name,value
                        else:
                            G.add_edges_from([(pkg_name,value)])
                else:
                    if pkg_name not in pkg_without_dependency:
                        pkg_without_dependency.append(pkg_name)
        #print G.nodes()
        with open(root+'_pkg_without_dependency.txt', 'w') as f:
            #json.dump(pkg_without_dependency,f)
            for item in pkg_without_dependency:
                #print item

                f.write("%s\n" % item)

        save_object(G, root+'_dependency_graph_object.p')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Invalid number of arguments \n Usage : program_name file_name"
        exit(0)
    else:
        filename=sys.argv[1]
        root=filename.split('_')[0]

        build_graph(filename,root)









