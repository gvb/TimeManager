#===========================================================================
# TIME MANAGER 
# a plugin for QGIS
# --------------------------------------------------------------------------
# by Anita Graser (anitagraser@gmx.at) 
# --------------------------------------------------------------------------
# project home and bug tracker: https://github.com/anitagraser/TimeManager
# plugin repository: http://plugins.qgis.org/plugins/plugins.xml
#===========================================================================

DEPENDENCIES
   none, runs on a default QGIS installation

MINIMUM QGIS VERSION
   QGIS 1.6 

PYTHON VERSION
   tested using Python 2.5

KNOWN ISSUES
   The plug-in uses Python's datetime module for calculations. It is 
   therefore limited to the module's functionality. 
   This enfolds (not exhaustive): 
   - Dates must accord to the Gregorian calendar 
   - Years must be between 1902 and 2038 due to limitations in time.mktime 
     (datetime supports years 1 to 9999) 
   - Limits to the size/resolution of the time frame size 

   We currently don't support: 
   - Leap years 
   - Dates with time zone notion 

   Shapefiles can't be edited directly, while time-managed. This is an OGR 
   limitation. It also exists for any other query you set: You simply can't 
   edit a shapefile whilst a query is set.