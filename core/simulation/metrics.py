

def compute_path_cost(graph, path):

    total = 0

    for i in range(len(path) - 1):

        edge_data = graph[path[i]][path[i + 1]]

        total += edge_data["weight"]

    return total