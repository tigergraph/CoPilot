# import pytest
#
# def pytest_collection_modifyitems(config, items):
#     """
#     Hook to dynamically exclude tests based on error messages encountered during collection.
#     """
#     deselected_items = []
#     for item in items:
#         try:
#             # Attempt to collect the test
#             config.hook.pytest_runtest_protocol(item=item, nextitem=None)
#         except Exception as e:
#             # Check if the error message indicates skipping
#             if "skip_this_test" in str(e):
#                 deselected_items.append(item)
#     for item in deselected_items:
#         items.remove(item)