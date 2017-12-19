import pytest

import geopandas

from geopandas_ext.epsg_utils import  epsg_to_dict, crs_units


proj_ft = geopandas.read_file(geopandas.datasets.get_path('nybb')).crs
wgs84 = {'init': 'epsg:4326'}
swiss = 21781

wgs84_dct = {'datum': 'WGS84', 'no_defs': True, 'proj': 'longlat'}



def test_epsg_to_dict():
    epsg = 4326
    assert wgs84_dct == epsg_to_dict(epsg)



@pytest.mark.parametrize(('crs', 'expected'), [
    (proj_ft, 'us-ft'),
    (swiss, 'm'),
    (wgs84, 'degrees'),
    ])
def test_crs_units(crs, expected):

    assert crs_units(crs) == expected
