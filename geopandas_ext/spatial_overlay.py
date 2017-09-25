from functools import reduce
import warnings

import numpy
import pandas

# import fiona
# from shapely.geometry import Point, Polygon, MultiPolygon
from .polygon_geom import explode_multipart_polygons

import geopandas
from geopandas import GeoDataFrame, GeoSeries

# import pyepsg


# def epsg_to_dict(epsg):
#     """Converts an EPSG code to a full proj4 dictionary.

#     Parameters
#     ----------
#     epsg : int
#         e EPSG code to lookup

#     Returns
#     -------
#     dict

#     """
#     p = pyepsg.get(epsg).as_proj4()
#     return fiona.crs.from_string(p)


# def crs_units(crs):
#     """Fetches the units from a crs dictionary. If an epsg code is passed in, 
#     it is converted to a dict. Supports fiona crs dictionary formats.

#     Parameters
#     ----------
#     crs : dict or int
#         is the dict or epsg code to fetch the spatial units.

#     Returns
#     -------
#     string
#         units of the crs e.g., 'us-ft', 'm', 'degrees'

#     """
    
#     if isinstance(crs, int):
#         epsg = crs
#         crs_dict = epsg_to_dict(epsg)
#         return crs_units(crs_dict)
    
#     if isinstance(crs, dict):
#         if 'units' in crs:
#             return crs['units']
        
#         else:
#             if "init" in crs:
#                 if 'epsg' in crs.get('init').lower():
#                     _, epsg = crs['init'].split(":")
#                     crs_dict = epsg_to_dict(epsg)
#                     return crs_units(crs_dict)
            
#             elif 'datum' in crs:
#                 if 'wgs' in crs.get('datum').lower():
#                     return 'degrees'
            
#             else:
#                 raise ValueError('Unable to retrieve units. Reproject data into a valid '
#                                  'coordinate system (State Plane Recommended)')
#     else:
#         raise Exception('crs must be epsg or `dict` format')


# def explode_multipart_polygons(gdf):
#     """separates multipart polygon geometries into a GeoDataFrame with single 
#     part geometries

#     Parameters
#     ----------
#     gdf : geopandas.GeoDataFrame
#         The gdf with multipart and singlepart geometries that will be exploded.

#     Returns
#     -------
#     outdf : geopandas.GeoDataFrame
#         Exploded GeoDataFrame 

#     """
#     if (gdf.geom_type.apply(lambda x: x in ['Polygon', 'MultiPolygon']).sum()!=len(gdf.index)):
#         raise TypeError("explode_multipart_polygons only takes GeoDataFrames with (multi)polygon geometries")

#     crs = gdf.crs
#     outdf = geopandas.GeoDataFrame(columns=gdf.columns)
#     for idx, row in gdf.iterrows():
#         if type(row.geometry) == Polygon:
#             outdf = outdf.append(row, ignore_index=True)
        
#         if type(row.geometry) == MultiPolygon:
#             multdf = geopandas.GeoDataFrame(columns=gdf.columns)
#             recs = len(row.geometry)
#             multdf = multdf.append([row] * recs, ignore_index=True)
            
#             for geom in range(recs):
#                 multdf.loc[geom, 'geometry'] = row.geometry[geom]
            
#             outdf = outdf.append(multdf, ignore_index=True)
#     outdf.crs = crs
    
#     return outdf


# def gdf_bbox(gdf):
#     """Creates a projected bounding box dataframe from the geometries of the 
#     input geodataframe. This gdf can be reprojected with the GeoDataFrame.to_crs
#     method.

#     Parameters
#     ----------
#     gdf : GeoDataFrame

#     """
    
#     minx, miny, maxx, maxy = gdf.total_bounds
    
#     p = geopandas.GeoDataFrame(
#         [{'geometry':Polygon([[minx, miny], [minx, maxy], [maxx, maxy], [maxx, miny]])}],
#         crs=gdf.crs
#     )
    
#     return p


def spatial_overlay(df1, df2, how='intersection', reproject=True, explode=False, keep_index=True, **kwargs):
    """Perform spatial overlay between two polygons.
    Currently only supports data GeoDataFrames with polygons.
    Implements several methods that are all effectively subsets of
    the union.

    Parameters
    ----------
    df1 : GeoDataFrame with MultiPolygon or Polygon geometry column
    df2 : GeoDataFrame with MultiPolygon or Polygon geometry column
    how : string
        Method of spatial overlay: 'intersection', 'union',
        'identity', 'symmetric_difference' or 'difference'.
    reproject : boolean, default True
        If GeoDataFrames do not have same projection, reproject
        df2 to same projection of df1 before performing overlay.
    explode : boolean, optional (default=False)
        explodes multipart geometries to single part.
    keep_index : boolean, optional (default=True)
        When combining geodataframes, this option assigns a range index to 
        each dataframe prior to the merge operation to indicate the parent 
        geometry in the source files.
    kwargs : kward arguments for api compatibility with `geopandas.overlay`

    Returns
    -------
    df : GeoDataFrame
        GeoDataFrame with new set of polygons and attributes
        resulting from the overlay
    """
    df1 = df1.copy()
    df2 = df2.copy()

    if keep_index:
        df1['idx1'] = range(len(df1))
        df2['idx2'] = range(len(df2))
    df_out = _calculate_overlay(df1, df2, how=how, reproject=reproject, **kwargs)

    if explode:
        return explode_multipart_polygons(df_out)

    return df_out


def _calculate_overlay(df1, df2, how, reproject, **kwargs):
    """
    Contributors: https://github.com/ozak
        Provided the algorithmic outline for performing the intersection and
        difference functions. His work for geopandas PR: Overlay performance #429
        was adapted and modified to enhance readibility, performance,
        and to improve the test framework.
    """

    # Allowed operations
    allowed_hows = [
        'intersection',
        'union',
        'identity',
        'symmetric_difference',
        'difference',  # aka erase
    ]

    # Error Messages
    if how not in allowed_hows:
        raise ValueError("`how` was \"%s\" but is expected to be in %s" % \
            (how, allowed_hows))

    if isinstance(df1, GeoSeries) or isinstance(df2, GeoSeries):
        raise NotImplementedError("`spatial_overlay` currently only implemented for GeoDataFrames")

    if (df1.geom_type.apply(lambda x: x in ['Polygon', 'MultiPolygon']).sum()!=len(df1.index) or
        df2.geom_type.apply(lambda x: x in ['Polygon', 'MultiPolygon']).sum()!=len(df2.index)):
        raise TypeError("`spatial_overlay` only takes GeoDataFrames with (multi)polygon geometries")

    if 'use_sindex' in kwargs:
        warnings.warn('`use_sindex` is deprecated and will be ignored.', DeprecationWarning)

    df1 = df1.copy()
    df2 = df2.copy()

    for df in [df1, df2]:
        if 'geometry' != df.geometry.name:
            if 'geometry' in df.columns:
                df.drop('geometry', axis=1, inplace=True)
            df.rename(columns={df.geometry.name:'geometry'}, inplace=True)
            df.set_geometry('geometry', inplace=True)

    df1.geometry = df1.geometry.buffer(0)
    df2.geometry = df2.geometry.buffer(0)

    if df1.crs != df2.crs and reproject:
        warnings.warn(
            'Data has different projections.\n'
            'Converted data to projection of first GeoPandas DataFrame.')
        df2.to_crs(crs=df1.crs, inplace=True)
    
    else:
        df2.crs = df1.crs

    if how == 'intersection':
        # Spatial Index to create intersections
        spatial_index = df2.sindex
        df1['bbox'] = df1.geometry.apply(lambda x: x.bounds)
        df1['sidx']=df1.bbox.apply(lambda x:list(spatial_index.intersection(x)))
        pairs = df1['sidx'].to_dict()
        nei = []
        for i,j in pairs.items():
            for k in j:
                nei.append([i,k])
        if nei!=[]:
            pairs = (GeoDataFrame(nei, columns=['pidx1','pidx2'], crs=df1.crs)
                     .merge(df1, left_on='pidx1', right_index=True)
                     .merge(df2, left_on='pidx2', right_index=True, suffixes=['_1','_2'])
                     .assign(Intersection=lambda _df:
                                 _df.apply(lambda x:
                                      (x['geometry_1'].intersection(x['geometry_2'])).buffer(0), axis=1)
                            )
                     .drop(['pidx1','pidx2','geometry_1','geometry_2','sidx','bbox'], axis=1)
                     .rename(columns={'Intersection':'geometry'})
                    )
            # method chain `merge` operations cause the gdf to drop into a df. need to re-init gdf.
            dfinter = GeoDataFrame(pairs, columns=pairs.columns, crs=df1.crs)
            dfinter = dfinter.loc[dfinter.geometry.is_empty==False]
            return dfinter.reset_index(drop=True)
        else:
            return GeoDataFrame([], columns=list(set(df1.columns).union(df2.columns)), crs=df1.crs)
    
    elif how == 'difference':
        spatial_index = df2.sindex

        df1['bbox'] = df1.geometry.apply(lambda x: x.bounds)
        df1['sidx'] = df1.bbox.apply(lambda x:list(spatial_index.intersection(x)))
        df1['new_g'] = df1.apply(lambda x: reduce(lambda x, y: x.difference(y).buffer(0),
                                 [x.geometry]+list(df2.iloc[x.sidx].geometry)) , axis=1)
        df1.geometry = df1.new_g
        df1 = df1.loc[df1.geometry.is_empty==False].copy()
        df1.drop(['bbox', 'sidx', 'new_g'], axis=1, inplace=True)
        df1.reset_index(inplace=True, drop=True)
        return df1
    
    elif how == 'symmetric_difference':
        s1 = _calculate_overlay(df1, df2, how='difference', reproject=reproject)
        s2 = _calculate_overlay(df2, df1, how='difference', reproject=reproject)
        if reproject:
            s2.to_crs(s1.crs, inplace=True)
        s3 = pandas.concat([s1, s2]).reset_index(drop=True)
        return s3
    
    elif how == 'union':
        s1 = _calculate_overlay(df1, df2, how='intersection', reproject=reproject)
        s2 = _calculate_overlay(df1, df2, how='difference', reproject=reproject)
        s3 = _calculate_overlay(df2, df1, how='difference', reproject=reproject)
        if reproject:
            s3.to_crs(s1.crs, inplace=True)
        s4 = pandas.concat([s1,s2,s3]).reset_index(drop=True)
        return s4
    
    elif how == 'identity':
        s1 = _calculate_overlay(df1, df2, how='difference', reproject=reproject)
        s2 = _calculate_overlay(df1, df2, how='intersection', reproject=reproject)
        s3 = pandas.concat([s1, s2]).reset_index(drop=True)
        return s3
    
    else:
        raise NotImplementedError(how)

