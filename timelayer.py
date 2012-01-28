#!/usr/bin/python
# -*- coding: UTF-8 -*-

debug = False

if debug:
    from PyQt4 import uic

import os
from datetime import datetime, timedelta
from qgis.core import *

class TimeLayer:
    """Manages the properties of a managed (managable) layer."""
    def __init__(self,layer,fromTimeAttribute,toTimeAttribute,rColumnAttribute="",rPathAttribute="",enabled=True,offset=0):
        self.layer = layer
        self.fromTimeAttribute = fromTimeAttribute
        self.toTimeAttribute = toTimeAttribute
        self.timeEnabled = enabled
        self.originalSubsetString = self.layer.subsetString()
        self.supportedFormats = [
             "%Y-%m-%d %H:%M:%S",
             "%Y-%m-%d %H:%M:%S.%f",
             "%Y-%m-%d %H:%M",
             "%Y-%m-%d"]
        self.timeFormat = self.supportedFormats[0]
        self.offset = int(offset)
        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e.value)

        # Raster support initialization
        self.rLayers = []
        self.rPath = rPathAttribute
        self.rColumn = rColumnAttribute
        self.rRefreshInhibit = False

        if debug:
            # load the form
            path = os.path.dirname(os.path.abspath(__file__))
            self.debugDialog = uic.loadUi(os.path.join(path, "debug.ui"))

    def getLayer(self):
        """Get the layer associated with the current timeLayer"""
        return self.layer
    
    def getName( self ):
        """Get the layer name as it is shown in the layers dock"""
        return self.layer.name()

    def getLayerId(self):
        """returns the layerID as registered in QgisMapLayerRegistry"""
        try:
            return self.layer.id() # function call for QGIS >= 1.7
        except AttributeError:
            return self.layer.getLayerID()

    def isEnabled(self):
        """whether timeManagement is enabled for this layer"""
        return self.timeEnabled

    def getTimeAttributes(self):
        """return the tuple of timeAttributes (fromTimeAttribute,toTimeAttribute)"""
        return(self.fromTimeAttribute,self.toTimeAttribute)

    def getTimeFormat(self):
        """returns the layer's time format"""
        return self.timeFormat
        
    def getOffset(self):
        """returns the layer's offset, integer in seconds"""
        return self.offset

    def strToDatetime(self, dtStr):
       """convert a date/time string into a Python datetime object"""
       try:
           # Try the last known format, if not, try all known formats.
           return datetime.strptime(dtStr, self.timeFormat)
       except:
           for fmt in self.supportedFormats:
               try:
                   self.timeFormat = fmt
                   return datetime.strptime(dtStr, self.timeFormat)
               except:
                   pass
       # If all fail, re-raise the exception
       raise

    def getTimeExtents( self ):
        """Get layer's temporal extent using the fields and the format defined somewhere else!"""
        #In irgendeiner Weise sollte der Benutzer auch erahnen können, wenn er Datensätze hat, die kein gültiges Datum haben, und daher nie angezeigt würden.
        provider=self.layer.dataProvider()
        fromTimeAttributeIndex = provider.fieldNameIndex(self.fromTimeAttribute)
        toTimeAttributeIndex = provider.fieldNameIndex(self.toTimeAttribute)
        startStr = str(provider.minimumValue(fromTimeAttributeIndex).toString())
        endStr = str(provider.maximumValue(toTimeAttributeIndex).toString())
        try:
            startTime = self.strToDatetime(startStr)
        except ValueError:
            raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as start time contains invalid data.')
        try:
            endTime = self.strToDatetime(endStr)
        except ValueError:
            raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as end time contains invalid data.')
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return (startTime,endTime)

    def setTimeRestriction(self,timePosition,timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return

        if debug:
            self.debugDialog.msg.append("setTimeRestriction " + datetime.strftime(timePosition, self.timeFormat))
            self.debugDialog.show()

        if self.rRefreshInhibit:
            return
        self.rRefreshInhibit = True

        startTime = datetime.strftime(timePosition + timedelta(seconds=self.offset),self.timeFormat)
        endTime = datetime.strftime((timePosition + timeFrame + timedelta(seconds=self.offset)),self.timeFormat)
        #subsetString = "\"%s\" < '%s' AND \"%s\" >= '%s' " % ( self.fromTimeAttribute,endTime,self.toTimeAttribute,startTime)
        if self.originalSubsetString == "":
            subsetString = "\"%s\" < '%s' AND \"%s\" >= '%s' " % ( self.fromTimeAttribute,endTime,self.toTimeAttribute,startTime)
        else:
            subsetString = "%s AND \"%s\" < '%s' AND \"%s\" >= '%s' " % ( self.originalSubsetString,self.fromTimeAttribute,endTime,self.toTimeAttribute,startTime)
        self.layer.setSubsetString( subsetString )
        #QMessageBox.information(self.iface.mainWindow(),"Test Output",subsetString)

        if self.rColumn != "":
            # Update the raster layers
            while len(self.rLayers) > 0:
                rLayer = self.rLayers.pop()
                if debug:
                    self.debugDialog.msg.append("Remove " + rLayer.name())
                    self.debugDialog.show()
                QgsMapLayerRegistry.instance().removeMapLayer(rLayer.id())

            # start data retreival: fetch geometry and all attributes for
            # each feature
            provider = self.layer.dataProvider()
            rFieldID = provider.fieldNameIndex(self.rColumn)
            provider.select(provider.attributeIndexes())
            feature = QgsFeature()
            while self.layer.dataProvider().nextFeature(feature):
                fname = feature.attributeMap()[rFieldID].toString()
                if debug:
                    self.debugDialog.msg.append("Found " + fname)
                    self.debugDialog.show()

                rlayer = QgsRasterLayer(os.path.join(str(self.rPath), str(fname)), fname)
                if rlayer.isValid():
                    rlayer.setNoDataValue(0.0)
                    # HACK - gvb
                    rlayer.setContrastEnhancementAlgorithm("StretchToMinimumMaximum")
                    self.rLayers.append(rlayer)
            for rlayer in self.rLayers:
                QgsMapLayerRegistry.instance().addMapLayer(rlayer)
                if debug:
                    self.debugDialog.msg.append("Add " + rlayer.name())
                    self.debugDialog.show()

        self.rRefreshInhibit = False

    def deleteTimeRestriction(self):
        """Restore original subset"""
        self.layer.setSubsetString( self.originalSubsetString )

    def hasTimeRestriction(self):
        """returns true if current layer.subsetString is not equal to originalSubsetString"""
        return self.layer.subsetString != self.originalSubsetString
        
    def getSaveString(self):
        """get string to save in project file"""
        delimiter = ';'
        saveString = self.getLayerId() + delimiter
        saveString += self.originalSubsetString + delimiter
        saveString += self.fromTimeAttribute + delimiter
        saveString += self.toTimeAttribute + delimiter
        saveString += str(self.timeEnabled) + delimiter
        saveString += self.timeFormat + delimiter
        saveString += str(self.offset) + delimiter
        saveString += self.rColumn + delimiter
        saveString += self.rPath
        return saveString

class NotATimeAttributeError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
         return repr(self.value)

class InvalidTimeLayerError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
         return repr(self.value)
