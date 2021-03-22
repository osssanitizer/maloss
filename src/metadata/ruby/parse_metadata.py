import os, fnmatch
import json
from graph_tool.all import *
import csv


pattern = "*:latest.metadata.json"
with open('stats_of__rubypkg.csv','w') as out:
        writer = csv.writer(out)
        writer.writerow(["Package Name","Centrality","Similarity Value","Component_Labels","Histogram","Attractors"])

for root, dirs, files in os.walk("/info/ruby/."):
    print("Root : ",root)
    for file in files:
        if fnmatch.fnmatch(file, pattern):
            print("File : ",file)
            filepath = os.path.join(root, file)
            g = Graph()
            v_prop = g.new_vertex_property("string")
            e_prop = g.new_edge_property("string")
            root = g.add_vertex()
            content_string = open(filepath, 'r').read()
            if content_string:
                            f = open(filepath)
                            data = json.load(f)
                            package_name = data["name"]
                            print(package_name)
                            v_prop[root] = package_name
                            version = data["version"]
                            if 'dependencies' in data and 'runtime' in data['dependencies']:
                                    row = data["dependencies"]["runtime"]
                                    for key in row:
                                            child = g.add_vertex()
                                            v_prop[child] = key["name"]
                                            edge = g.add_edge(root, child)
                                            e_prop[edge] = key["requirements"]
                    #print key
                    # print str(row[key]).replace("^","")
                                    with open('stats_of_rubypkg.csv','a') as out:
                                            writer = csv.writer(out)
                                            centrality_val = graph_tool.centrality.pagerank(g, damping=0.85,pers=None, weight=None,prop=None,epsilon=1e-06,max_iter=None,ret_iter=False)
                                            similarity = graph_tool.topology.vertex_similarity(g, sim_type='jaccard',vertex_pairs=None,self_loops=True,sim_map=None)
                                            comp, hist, is_attractor=graph_tool.topology.label_components(g, vprop=None,directed=None,attractors=True)
                                            centrality_list=[]
                                            similarity_list=[]
                                            for val in centrality_val:
                                                    centrality_list.append(val)
                                            centrality_list=",".join(str(i) for i in centrality_list)
                                            for val in similarity:
                                                    similarity_list.append(val)
                                            similarity_list=",".join(str(i) for i in similarity_list)
                                            writer.writerow([package_name,centrality_list,similarity_list,comp.a,hist,is_attractor])
            #graph_draw(g, vertex_text=v_prop, edge_text=e_prop, vertex_font_size=10, output_size = (500, 500), output = "/metadata/test/graphs/"+package_name+".png")

