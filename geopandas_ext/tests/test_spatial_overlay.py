import numpy
from pandas.util.testing import assert_series_equal

from shapely.geometry import Point, Polygon

import geopandas
from geopandas import GeoDataFrame, read_file

from geopandas_ext.spatial_overlay import spatial_overlay as overlay

import pytest

ignore_diff_proj =  'ignore:Data has different projections.'


class TestDataFrame_orig:
    """This test uses the original test setup from geopandas.tests.test_overlay.
    This version has been modified to correct errors in that test suite
    including the following:
        * The geopandas.overlay(how='symmetric_difference') test contains
        invalid polygons in the output. These polygons contain NaN attributes
        from _both_ gdf that are fed into the overlay method, which cannot be
        true of a symmetric difference. The shape of the output is used as
        to verify the original test, but it's invalid.
        * The geopandas.overlay(how='difference') test again checks the shape
        of the output, but again the shape includes invalid columns. A
        correct difference function subtracts the geometry from the second
        from the geometry of the first without appending attributes from the
        second (which are all empty or NaN, of course.). The original overlay
        function appends the columns of the second to the first before the
        subtraction, which results in those columns being entirely NaN.
        * All geopandas.overlay() operations naively handle the crs information
        from the gdfs that are passed into it. If projected gdfs
        are passed in, the result has no crs information even if the two crs
        dictionaries are identical.

    """

    def setup_method(self):
        N = 10

        self.kwargs = {
            'reproject': False,
            'keep_index': False,
            'explode': True,
        }

        nybb_filename = geopandas.datasets.get_path('nybb')

        self.polydf = read_file(nybb_filename)
        self.crs = {'init': 'epsg:4326'}

        # ALERT: The bounding coordinates of `polydf` are 913175.1, 120121.9,
        # 1067382.5, 272844.3, which make no sense in the epsg:4326 system,
        # which is in degrees. Tests passing under these conditions prove that
        # the overlay function must be capable of ignoring the crs information.

        b = [int(x) for x in self.polydf.total_bounds]
        self.polydf2 = GeoDataFrame(
            [{'geometry': Point(x, y).buffer(10000), 'value1': x + y,
              'value2': x - y}
             for x, y in zip(range(b[0], b[2], int((b[2]-b[0])/N)),
                             range(b[1], b[3], int((b[3]-b[1])/N)))],
            crs=self.crs,
            )
        self.pointdf = GeoDataFrame(
            [{'geometry': Point(x, y), 'value1': x + y, 'value2': x - y}
             for x, y in zip(range(b[0], b[2], int((b[2]-b[0])/N)),
                             range(b[1], b[3], int((b[3]-b[1])/N)))],
            crs=self.crs,
            )

        # TODO this appears to be necessary;
        # why is the sindex not generated automatically?
        # self.polydf2._generate_sindex() # this appears not to be necessary in geopandas 0.3.0

        self.union_shape = (180, 7)

    def test_union(self):
        df = overlay(self.polydf, self.polydf2, how="union", **self.kwargs)
        assert type(df) is GeoDataFrame
        assert df.shape == self.union_shape
        assert 'value1' in df.columns and 'Shape_Area' in df.columns

    def test_union_no_index(self):
        # explicitly ignore indicies
        dfB = overlay(self.polydf, self.polydf2, how="union", use_sindex=False, **self.kwargs)
        assert dfB.shape == self.union_shape

        # remove indicies from df
        self.polydf._sindex = None
        self.polydf2._sindex = None
        dfC = overlay(self.polydf, self.polydf2, how="union", **self.kwargs)
        assert dfC.shape == self.union_shape

    def test_intersection(self):
        df = overlay(self.polydf, self.polydf2, how="intersection", **self.kwargs)
        assert df['BoroName'][0] is not None
        assert df.shape == (68, 7)

    def test_identity(self):
        df = overlay(self.polydf, self.polydf2, how="identity", **self.kwargs)
        assert df.shape == (154, 7)

    def test_symmetric_difference(self):
        df = overlay(self.polydf, self.polydf2, how="symmetric_difference", **self.kwargs)
        # ALERT: the original algorithm creates invalid geometries.
        # Symmetric differece geometries should be in either polydf or polydf2.
        # Any resulting geometries without attributes from one or the other is
        # completely invalid.

        # assert df.shape == (122, 7) # this shape contains invalid geometries

        # Use 'Shape_Area' as the field to indicate polydf and 'value1' as the
        # field for polydf2
        # df = geopandas.overlay(polydf, polydf2, how="symmetric_difference")
        # len(df.loc[(out['Shape_Area'].isnull()) & (df['value1'].isnull())])
        # >>> 10
        invalid_sym_diff_geom_len = 10
        assert df.shape == (122-invalid_sym_diff_geom_len, 7)

    def test_difference(self):
        df = overlay(self.polydf, self.polydf2, how="difference", **self.kwargs)
        # ALERT: the original difference algorithm creates invalid columns.
        # If taking the difference of polydf and polydf2, there should be no
        # geometries containing any attributes from polydf2. Yet the original
        # algorithm creates the attribute fields for all fields in polydf2 and
        # fills them with `None` or `NaN`.

        # assert df.shape == (86, 7) #this shape contains 2 invalid columns

        # df = geopandas.overlay(polydf, polydf2, how='difference')
        # df.dropna().shape
        # >>> (86, 5)
        assert df.shape == (86, 5)

    def test_bad_how(self):
        with pytest.raises(ValueError):
            overlay(self.polydf, self.polydf, how="spandex", **self.kwargs)

    def test_nonpoly(self):
        with pytest.raises(TypeError):
            overlay(self.pointdf, self.polydf, how="union", **self.kwargs)

    def test_duplicate_column_name(self):
        polydf2r = self.polydf2.rename(columns={'value2': 'Shape_Area'})
        df = overlay(self.polydf, polydf2r, how="union", **self.kwargs)
        assert 'Shape_Area_2' in df.columns and 'Shape_Area' in df.columns

    def test_geometry_not_named_geometry(self):
        # Geopandas Issue #306
        # Add points and flip names
        polydf3 = self.polydf.copy()
        polydf3 = polydf3.rename(columns={'geometry': 'polygons'})
        polydf3 = polydf3.set_geometry('polygons')
        polydf3['geometry'] = self.pointdf.geometry.loc[0:4]
        assert polydf3.geometry.name == 'polygons'

        df = overlay(polydf3, self.polydf2, how="union", **self.kwargs)
        assert type(df) is GeoDataFrame
        df2 = overlay(self.polydf, self.polydf2, how="union", **self.kwargs)
        assert df.geom_almost_equals(df2).all()

    def test_geoseries_warning(self):
        # Geopandas Issue #305
        with pytest.raises(NotImplementedError):
            overlay(self.polydf, self.polydf2.geometry, how="union", **self.kwargs)


class TestDataFrame_nocrs:
    """These tests check that if neither gdf has crs information, that
    the results are identical to the `_orig` test.
    """

    def setup_method(self):
        N = 10

        self.kwargs = {
            'reproject': False,
            'keep_index': False,
            'explode': True,
        }

        nybb_filename = geopandas.datasets.get_path('nybb')

        self.polydf = read_file(nybb_filename)

        # this should be the only change compared to `_orig`
        self.polydf.crs = None
        self.crs = None
        # end change

        b = [int(x) for x in self.polydf.total_bounds]
        self.polydf2 = GeoDataFrame(
            [{'geometry': Point(x, y).buffer(10000), 'value1': x + y,
              'value2': x - y}
             for x, y in zip(range(b[0], b[2], int((b[2]-b[0])/N)),
                             range(b[1], b[3], int((b[3]-b[1])/N)))],
            crs=self.crs,
            )
        self.pointdf = GeoDataFrame(
            [{'geometry': Point(x, y), 'value1': x + y, 'value2': x - y}
             for x, y in zip(range(b[0], b[2], int((b[2]-b[0])/N)),
                             range(b[1], b[3], int((b[3]-b[1])/N)))],
            crs=self.crs,
            )

        self.union_shape = (180, 7)

    def test_union(self):
        df = overlay(self.polydf, self.polydf2, how="union", **self.kwargs)
        assert type(df) is GeoDataFrame
        assert df.shape == self.union_shape
        assert 'value1' in df.columns and 'Shape_Area' in df.columns

    def test_union_no_index(self):
        # explicitly ignore indicies
        dfB = overlay(self.polydf, self.polydf2, how="union", use_sindex=False, **self.kwargs)
        assert dfB.shape == self.union_shape

        # remove indicies from df
        self.polydf._sindex = None
        self.polydf2._sindex = None
        dfC = overlay(self.polydf, self.polydf2, how="union", **self.kwargs)
        assert dfC.shape == self.union_shape

    def test_intersection(self):
        df = overlay(self.polydf, self.polydf2, how="intersection", **self.kwargs)
        assert df['BoroName'][0] is not None
        assert df.shape == (68, 7)

    def test_identity(self):
        df = overlay(self.polydf, self.polydf2, how="identity", **self.kwargs)
        assert df.shape == (154, 7)

    def test_symmetric_difference(self):
        df = overlay(self.polydf, self.polydf2, how="symmetric_difference", **self.kwargs)
        # ALERT: the original algorithm creates invalid geometries.
        # Symmetric differece geometries should be in either polydf or polydf2.
        # Any resulting geometries without attributes from one or the other is
        # completely invalid.

        # assert df.shape == (122, 7) # this shape contains invalid geometries

        # Use 'Shape_Area' as the field to indicate polydf and 'value1' as the
        # field for polydf2
        # df = geopandas.overlay(polydf, polydf2, how="symmetric_difference")
        # len(df.loc[(out['Shape_Area'].isnull()) & (df['value1'].isnull())])
        # >>> 10
        invalid_sym_diff_geom_len = 10
        assert df.shape == (122-invalid_sym_diff_geom_len, 7)

    def test_difference(self):
        df = overlay(self.polydf, self.polydf2, how="difference", **self.kwargs)
        # ALERT: the original difference algorithm creates invalid columns.
        # If taking the difference of polydf and polydf2, there should be no
        # geometries containing any attributes from polydf2. Yet the original
        # algorithm creates the attribute fields for all fields in polydf2 and
        # fills them with `None` or `NaN`.

        # assert df.shape == (86, 7) #this shape contains 2 invalid columns

        # df = geopandas.overlay(polydf, polydf2, how='difference')
        # df.dropna().shape
        # >>> (86, 5)
        assert df.shape == (86, 5)

    def test_bad_how(self):
        with pytest.raises(ValueError):
            overlay(self.polydf, self.polydf, how="spandex", **self.kwargs)

    def test_nonpoly(self):
        with pytest.raises(TypeError):
            overlay(self.pointdf, self.polydf, how="union", **self.kwargs)

    def test_duplicate_column_name(self):
        polydf2r = self.polydf2.rename(columns={'value2': 'Shape_Area'})
        df = overlay(self.polydf, polydf2r, how="union", **self.kwargs)
        assert 'Shape_Area_2' in df.columns and 'Shape_Area' in df.columns

    def test_geometry_not_named_geometry(self):
        # Geopandas Issue #306
        # Add points and flip names
        polydf3 = self.polydf.copy()
        polydf3 = polydf3.rename(columns={'geometry': 'polygons'})
        polydf3 = polydf3.set_geometry('polygons')
        polydf3['geometry'] = self.pointdf.geometry.loc[0:4]
        assert polydf3.geometry.name == 'polygons'

        df = overlay(polydf3, self.polydf2, how="union", **self.kwargs)
        assert type(df) is GeoDataFrame
        df2 = overlay(self.polydf, self.polydf2, how="union", **self.kwargs)
        assert df.geom_almost_equals(df2).all()

    def test_geoseries_warning(self):
        # Geopandas Issue #305
        with pytest.raises(NotImplementedError):
            overlay(self.polydf, self.polydf2.geometry, how="union", **self.kwargs)


class TestDataFrame_crs:
    """In real use cases, overlay functionality should take into account
    the crs informatin of the GeoDataFrames involved with it is available.
    """

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

        self.pointdf = GeoDataFrame(
            [{'geometry': Point(x, y), 'value1': x + y, 'value2': x - y}
             for x, y in zip(range(b[0], b[2], int((b[2]-b[0])/N)),
                             range(b[1], b[3], int((b[3]-b[1])/N)))],
            crs=self.polydf.crs,
            )

        # reproject to different crs
        self.polydf2.to_crs(self.crs, inplace=True)
        self.pointdf.to_crs(self.crs, inplace=True)


    @pytest.mark.filterwarnings(ignore_diff_proj)
    def test_union(self):
        df = overlay(self.polydf, self.polydf2, how="union", **self.kwargs)
        df['area'] = df.geometry.area

        polydf = self.polydf.copy()
        polydf2 = self.polydf2.copy()

        polydf['area'] = polydf.geometry.area
        ck1 = polydf.groupby(polydf.index)['area'].sum()
        polydf2['area'] = polydf2.to_crs(polydf.crs).geometry.area
        ck2 = polydf2.groupby(polydf2.index)['area'].sum()

        assert type(df) is GeoDataFrame
        assert df.crs == self.polydf.crs
        assert 'value1' in df.columns and 'Shape_Area' in df.columns
        for ix, ck in zip(['idx1','idx2'], [ck1, ck2]):
            check = df.groupby([ix])['area'].sum()
            assert_series_equal(check, ck, check_names=False, check_index_type=False)

    @pytest.mark.filterwarnings(ignore_diff_proj)
    def test_union_no_index(self):
        # explicitly ignore indicies
        df = overlay(self.polydf, self.polydf2, how="union", keep_index=False, **self.kwargs)

        assert df.shape[1] == 7

    @pytest.mark.filterwarnings(ignore_diff_proj)
    def test_intersection(self):
        df = overlay(self.polydf, self.polydf2, how="intersection", **self.kwargs)

        assert df['BoroName'][0] is not None
        assert df.shape[1] == 9

    @pytest.mark.filterwarnings(ignore_diff_proj)
    def test_identity(self):
        df = overlay(self.polydf, self.polydf2, how="identity", **self.kwargs)
        df['area'] = df.geometry.area

        polydf = self.polydf.copy()

        polydf['area'] = polydf.geometry.area
        ck = polydf.groupby(polydf.index)['area'].sum()
        check = df.groupby(['idx1'])['area'].sum()
        df_area = df.geometry.area.sum()
        polydf_area = self.polydf.geometry.area.sum()
        error =  (polydf_area - df_area) / polydf_area

        assert -self.tol < error < self.tol
        assert_series_equal(check, ck, check_names=False, check_index_type=False)
        assert df.shape[1] == 9 + 1 # add one for the 'area' field

    @pytest.mark.filterwarnings(ignore_diff_proj)
    def test_symmetric_difference(self):
        df = overlay(self.polydf, self.polydf2, how="symmetric_difference", **self.kwargs)

        assert df.shape == (15, 9)

    @pytest.mark.filterwarnings(ignore_diff_proj)
    def test_difference(self):
        df = overlay(self.polydf, self.polydf2, how="difference", **self.kwargs)

        rows, cols = self.polydf.shape

        assert df.shape == (rows, cols+1) #add one for the index

    def test_bad_how(self):
        with pytest.raises(ValueError):
            overlay(self.polydf, self.polydf, how="spandex", **self.kwargs)

    def test_nonpoly(self):
        with pytest.raises(TypeError):
            overlay(self.pointdf, self.polydf, how="union", **self.kwargs)

    @pytest.mark.filterwarnings(ignore_diff_proj)
    def test_duplicate_column_name(self):
        polydf2r = self.polydf2.rename(columns={'value2': 'Shape_Area'})
        df = overlay(self.polydf, polydf2r, how="union", **self.kwargs)

        assert 'Shape_Area_2' in df.columns and 'Shape_Area' in df.columns

    @pytest.mark.filterwarnings(ignore_diff_proj)
    def test_geometry_not_named_geometry(self):
        # Geopandas Issue #306
        # Add points and flip names
        polydf3 = self.polydf.copy()
        polydf3 = polydf3.rename(columns={'geometry': 'polygons'})
        polydf3 = polydf3.set_geometry('polygons')
        polydf3['geometry'] = self.pointdf.geometry.loc[0:4]

        df = overlay(polydf3, self.polydf2, how="union", **self.kwargs)
        df2 = overlay(self.polydf, self.polydf2, how="union", **self.kwargs)

        assert polydf3.geometry.name == 'polygons'
        assert type(df) is GeoDataFrame
        assert df.geom_almost_equals(df2).all()

    def test_geoseries_warning(self):
        # Geopandas Issue #305
        with pytest.raises(NotImplementedError):
            overlay(self.polydf, self.polydf2.geometry, how="union", **self.kwargs)
