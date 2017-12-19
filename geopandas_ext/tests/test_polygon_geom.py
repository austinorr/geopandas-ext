import pytest

import geopandas
from geopandas import GeoDataFrame, read_file

from shapely.geometry import Point

from geopandas_ext.polygon_geom import  explode_multipart_polygons, gdf_bbox


def test_gdf_bbox():
    polydf = geopandas.read_file(geopandas.datasets.get_path('nybb'))
    bboxdf = gdf_bbox(polydf)
    tst = bboxdf.total_bounds == polydf.total_bounds
    assert polydf.crs == bboxdf.crs
    assert tst.all()

class TestExplodeMultipartPolygons:


    def setup_method(self):

        N = 10
        self.tol = 1e12
        self.kwargs = { # Use Defaults
        }
        self.crs = {'init': 'epsg:4326'}

        nybb_filename = geopandas.datasets.get_path('nybb')
        self.polydf = read_file(nybb_filename)

        b = [int(x) for x in self.polydf.total_bounds]
        self.polydf2 = GeoDataFrame(
            [{'geometry': Point(x, y).buffer(10000), 'value1': x + y,
              'value2': x - y}
             for x, y in zip(range(b[0], b[2], int((b[2]-b[0])/N)),
                             range(b[1], b[3], int((b[3]-b[1])/N)))],
            crs=self.polydf.crs,
            )

        # reproject to different crs
        self.polydf2.to_crs(self.crs, inplace=True)

    def test_explode_multipart_polygons(self):
        polydf_ex = explode_multipart_polygons(self.polydf)
        assert self.polydf.crs == polydf_ex.crs
        assert polydf_ex.shape == (106, 5)

    def test_explode_multipart_polygons_singlepart(self):
        polydf2_ex = explode_multipart_polygons(self.polydf2)
        assert self.polydf2.crs == polydf2_ex.crs
        assert polydf2_ex.shape == (11, 3)
