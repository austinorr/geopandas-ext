# -*- coding: utf-8 -*-

import geopandas
from shapely.geometry import Polygon, MultiPolygon


def explode_multipart_polygons(gdf):
    """separates multipart polygon geometries into a GeoDataFrame with single
    part geometries

    adapted from @jwass https://github.com/geopandas/geopandas/issues/174#issuecomment-63126908

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        The gdf with multipart and singlepart geometries that will be exploded.

    Returns
    -------
    outdf : geopandas.GeoDataFrame
        Exploded GeoDataFrame

    """
    if (gdf.geom_type.apply(lambda x: x in ['Polygon', 'MultiPolygon']).sum() != len(gdf.index)):
        raise TypeError(
            "explode_multipart_polygons only takes GeoDataFrames with (multi)polygon geometries")

    exploded = (
        gdf
        .explode()
        .reset_index()
        .rename(columns={0: 'geometry'})
        .merge(gdf.drop('geometry', axis=1), left_on='level_0', right_index=True)
        .set_geometry('geometry')
        .drop(['level_0', 'level_1'], axis=1)
    )

    exploded.crs = gdf.crs

    return exploded


def gdf_bbox(gdf):
    """Creates a projected bounding box dataframe from the geometries of the
    input geodataframe. This gdf can be reprojected with the GeoDataFrame.to_crs
    method.

    Parameters
    ----------
    gdf : GeoDataFrame

    """

    minx, miny, maxx, maxy = gdf.total_bounds

    p = geopandas.GeoDataFrame(
        [{'geometry': Polygon([[minx, miny], [minx, maxy], [
                              maxx, maxy], [maxx, miny]])}],
        crs=gdf.crs
    )

    return p
