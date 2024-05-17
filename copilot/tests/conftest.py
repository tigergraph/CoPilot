import pytest

def pytest_collection_modifyitems(config, items):
    """
    Hook to modify collected test items.
    """
    deselected_modules = set()
    for item in items:
        try:
            # Attempt to collect the test
            config.hook.pytest_runtest_protocol(item=item, nextitem=None)
        except Exception as e:
            # Check if the error message contains the specified substring
            error_message = str(e)
            if "pymilvus.exceptions.MilvusException" in error_message:
                # Mark the test module as skipped if the error message contains the specified substring
                deselected_modules.add(item.module.__name__)
    # Remove the deselected modules from the test items list
    items[:] = [item for item in items if item.module.__name__ not in deselected_modules]