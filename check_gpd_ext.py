import sys

import geopandas_ext
status = geopandas_ext.test(*sys.argv[1:])
sys.exit(status)