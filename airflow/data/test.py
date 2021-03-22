import networkx as nx
import matplotlib.pyplot as plt
import pickle

G = nx.DiGraph()
G.add_node("ROOT")
graph = {
    'A': ['B', 'C', 'D'],
    'B': ['E', 'F'],
    'C': [],
    'D': ['F'],
    'E': [],
    'F': ['G']
}

for p1 in graph:
    if p1 not in G:
        G.add_node(p1)
    G.add_edges_from([('ROOT', p1)])
    for dep in graph[p1]:
        if dep not in G:
            G.add_node(dep)
        G.add_edges_from([(p1, dep)])

pickle.dump(G, open('test_graph.pickle', 'wb'))

nx.draw(G, with_labels=True)
# plt.show()

