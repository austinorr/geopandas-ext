from pkg_resources import resource_filename

try:
    import pytest
    def test(*args):
        options = [resource_filename('geopandas_ext', 'tests')]
        options.extend(list(args))
        return pytest.main(options)

except ImportError:
    def test():
        print("Tests require `pytest`")

