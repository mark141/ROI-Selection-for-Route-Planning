# from core.roi.static_roi import ROISelectorFactory


# def test_static_roi_returns_nodes(mock_graph):
#
#     roi_selector = StaticROISelector()
#
#     region = roi_selector.select_region(
#         graph=mock_graph,
#         start="A",
#         goal="C",
#         constraints=[]
#     )
#
#     assert region is not None
#     assert len(region) > 0