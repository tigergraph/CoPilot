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
import pytest

pytest.mark.skip_on_collection_failure = pytest.mark.skip(reason="Skipped due to collection failure")
def pytest_collection_modifyitems(config, items):
    if config.pluginmanager.hasplugin('collect') and config.pluginmanager.getplugin('collect')._config.failed:
        for item in items:
            if 'skip_on_collection_failure' in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Skipped due to collection failure"))