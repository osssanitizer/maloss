import networkx as nx
import json
import pickle


def save_object(obj, filename):
    with open(filename, 'wb') as output:  # Overwrites any existing file.
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)


G = nx.DiGraph()

G.add_node('RUBY')
pkg_without_dependency = []
with open('rubygems_metadata.txt') as json_file:
    data = json.load(json_file)
    for p1 in data['ruby_package']:
        pkg_name = p1['name']
        if p1['name'] not in G:
            G.add_node(pkg_name)
            G.add_edges_from([('RUBY',pkg_name)])
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
    with open('ruby_pkg_without_dependency.txt', 'w') as f:
        #json.dump(pkg_without_dependency,f)
        for item in pkg_without_dependency:
            #print item

            f.write("%s\n" % item)

    save_object(G, 'ruby_dependency_graph_object.p')









