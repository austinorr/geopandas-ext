# -*- coding: utf-8 -*-

import fiona
import pyepsg


def epsg_to_dict(epsg):
    """Converts an EPSG code to a full proj4 dictionary.

    Parameters
    ----------
    epsg : int
        e EPSG code to lookup

    Returns
    -------
    dict

    """
    p = pyepsg.get(epsg).as_proj4()
    return fiona.crs.from_string(p)


def crs_units(crs):
    """Fetches the units from a crs dictionary. If an epsg code is passed in,
    it is converted to a dict. Supports fiona crs dictionary formats.

    Parameters
    ----------
    crs : dict or int
        is the dict or epsg code to fetch the spatial units.

    Returns
    -------
    string
        units of the crs e.g., 'us-ft', 'm', 'degrees'

    """

    if isinstance(crs, int):
        epsg = crs
        crs_dict = epsg_to_dict(epsg)
        return crs_units(crs_dict)

    if isinstance(crs, dict):
        if 'units' in crs:
            return crs['units']

        else:
            if "init" in crs:
                if 'epsg' in crs.get('init').lower():
                    _, epsg = crs['init'].split(":")
                    crs_dict = epsg_to_dict(epsg)
                    return crs_units(crs_dict)

            elif 'datum' in crs:
                if 'wgs' in crs.get('datum').lower():
                    return 'degrees'

            else:
                raise ValueError('Unable to retrieve units. Reproject data into a valid '
                                 'coordinate system (State Plane Recommended)')
    else:
        raise Exception('crs must be epsg or `dict` format')





