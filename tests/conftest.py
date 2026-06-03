import pytest
import networkx as nx


# @pytest.fixture
# def mock_graph():
#     """
#     Small graph for routing tests.
#     """
#
#     graph = nx.Graph()
#
#     graph.add_edge("A", "B", weight=1)
#     graph.add_edge("B", "C", weight=2)
#     graph.add_edge("A", "C", weight=4)
#
#     return graph
#
#
# @pytest.fixture
# def mock_weather():
#     """
#     Example environmental data.
#     """
#
#     return {
#         ("A", "B"): {
#             "visibility": 0.9,
#             "wind_speed": 10
#         },
#         ("B", "C"): {
#             "visibility": 0.2,
#             "wind_speed": 80
#         }
#     }
#
#
# @pytest.fixture
# def mock_edge():
#     """
#     Example edge object.
#     """
#
#     class Edge:
#         def __init__(self, edge_id):
#             self.id = edge_id
#
#     return Edge(("A", "B"))