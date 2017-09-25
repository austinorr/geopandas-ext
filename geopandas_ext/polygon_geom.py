

import geopandas
from shapely.geometry import Polygon, MultiPolygon


def explode_multipart_polygons(gdf):
    """separates multipart polygon geometries into a GeoDataFrame with single 
    part geometries

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        The gdf with multipart and singlepart geometries that will be exploded.

    Returns
    -------
    outdf : geopandas.GeoDataFrame
        Exploded GeoDataFrame 

    """
    if (gdf.geom_type.apply(lambda x: x in ['Polygon', 'MultiPolygon']).sum()!=len(gdf.index)):
        raise TypeError("explode_multipart_polygons only takes GeoDataFrames with (multi)polygon geometries")

    crs = gdf.crs
    outdf = geopandas.GeoDataFrame(columns=gdf.columns)
    for idx, row in gdf.iterrows():
        if type(row.geometry) == Polygon:
            outdf = outdf.append(row, ignore_index=True)
        
        if type(row.geometry) == MultiPolygon:
            multdf = geopandas.GeoDataFrame(columns=gdf.columns)
            recs = len(row.geometry)
            multdf = multdf.append([row] * recs, ignore_index=True)
            
            for geom in range(recs):
                multdf.loc[geom, 'geometry'] = row.geometry[geom]
            
            outdf = outdf.append(multdf, ignore_index=True)
    outdf.crs = crs
    
    return outdf


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
        [{'geometry':Polygon([[minx, miny], [minx, maxy], [maxx, maxy], [maxx, miny]])}],
        crs=gdf.crs
    )
    
    return p



