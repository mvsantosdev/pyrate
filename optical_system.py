#!/usr/bin/env/python
"""
Pyrate - Optical raytracing based on Python

Copyright (C) 2014 Moritz Esslinger moritz.esslinger@web.de
               and    Uwe Lippmann  uwe.lippmann@web.de

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import inspect
import shape as surfShape # the name 'shape' already denotes the dimensions of a numpy array
import material
import pupil

from numpy import *
from ray import RayBundle


class Surface():
    """
    Represents a surface of an optical system.
    
    :param shap: Shape of the surface. Claculates the intersection with rays. ( Shape object or child )
    :param mater: Material of the volume behind the surface. Claculates the refraction. ( Material object or child )
    :param thickness: distance to next surface on the optical axis
    """
    def __init__(self, thickness = 0.0):
        self.shap  = surfShape.Conic()
        self.mater = material.ConstantIndexGlass()
        self.thickness = thickness
        
        self.availableShapeNames, self.availableShapeClasses = self.getAvailableShapes()
        self.availableMaterialTypeNames, self.availableMaterialTypeClasses = self.getAvailableMaterialTypes()


    def getAvailableShapes(self):
        """
        Parses shape.py for class definitions. Returns all but shape.Shape
        
        :return listOfShapeNames: List of strings
        :return listOfShapeClasses: List of Class references
        """
        listOfShapeNames = []
        listOfShapeClasses = []
        for name, cla in inspect.getmembers(surfShape):
            fullname = str(cla).strip()
            if fullname.startswith('<class \'shape.') and fullname != '<class \'shape.Shape\'>':
                listOfShapeNames.append( name )
                listOfShapeClasses.append( cla )
        return listOfShapeNames, listOfShapeClasses

    def getAvailableMaterialTypes(self):
        """
        Parses material.py for class defintions. Returns all but material.Material
        
        :return listOfMaterialTypeNames: List of strings
        :return listOfMaterialTypeClasses: List of Class references
        """
        listOfMaterialTypeNames = []
        listOfMaterialTypeClasses = []
        for name, cla in inspect.getmembers(material):
            fullname = str(cla).strip()
            if fullname.startswith('<class \'material.') and fullname != '<class \'material.Material\'>':
                listOfMaterialTypeNames.append( name )
                listOfMaterialTypeClasses.append( cla )
        return listOfMaterialTypeNames, listOfMaterialTypeClasses

    def setMaterial(self, materialType):
        """
        Sets the material object self.mater
        
        :param materialType: name of the material dispersion formula (str)
        """
        
        if materialType in self.availableMaterialTypeNames:
            i = self.availableMaterialTypeNames.index(materialType)
            self.mater = self.availableMaterialTypeClasses[i]()
        else:
            print 'Warning: material type \'', materialType, '\' not found. setMaterial() aborted.'

    def setMaterialCoefficients(self, coeff):
        """
        Sets the coefficients that determine the material behavior. 

        :param coeff: coefficients. Type and format depend on Material child class.
        """
        self.mater.setCoefficients(coeff)

    def setShape(self, shapeName):
        """
        Sets the shape object self.shap
        
        :param shapeName: name of the shape type (str)
        """
        if shapeName in self.availableShapeNames:
            i = self.availableShapeNames.index(shapeName)

            # conserve the most basic parameters of the shape
            curv = self.shap.curvature 
            semidiam = self.shap.sdia
         
            self.shap = self.availableShapeClasses[i](curv=curv, semidiam=semidiam)
        else:
            print 'Warning: shape \'', materialType, '\' not found. setShape() aborted.'

    def draw2d(self, ax, offset = [0,0], vertices=100, color="grey"):
        self.shap.draw2d(ax, offset, vertices, color)      

    def getABCDMatrix(self, nextSurface, ray):
        """
        Returns an ABCD matrix of the current surface.
        The matrix is set up in geometric convention for (y, dy/dz) vectors.

        The matrix contains:
        - paraxial refraction from vacuum through the front surface
        - paraxial translation through the material
        - paraxial refraction at the rear surface into vacuum

        :param nextSurface: next surface for rear surface curvature (Surface object)
        :param ray: ray bundle to obtain wavelength (RayBundle object)
        :return abcd: ABCD matrix (2d numpy 2x2 matrix of float)
        """
        curvature = self.shap.getCentralCurvature()
        nextCurvature = nextSurface.shap.getCentralCurvature()
        return self.mater.getABCDMatrix(curvature, self.thickness, nextCurvature, ray)


class OpticalSystem():
    """
    Represents an optical system, consisting of several surfaces and materials inbetween.
    """
    def __init__(self):
        self.surfaces = []
        self.insertSurface(0) # object
        self.insertSurface(1) # image
        self.stopPosition = None        
        self.stopDiameter = 0

        self.listOfPupilTypeNames, self.listOfPupilTypeClasses = self.getAvailablePupilDefinitions()

    def insertSurface(self,position):
        """
        Inserts a new surface into the optical system.

        :param position: number of the new surface (int). 
           Surface that is currently at this position 
           and all following surface indices are incremented.
        """
        self.surfaces.insert(position, Surface() )
        
    def removeSurface(self,position):
        """
        Removes a surface from the optical system.

        :param position: number of the surface to remove (int) 
        """
        self.surfaces.pop(position)
        
    def getNumberOfSurfaces(self):
        """
        Returns the number of surfaces, including object and image (int)
        """
        return len(self.surfaces)
        
    def setThickness(self, position, thickness):
        """
        Sets the on-axis thickness of a surface.

        :param position: number of the surface (int) 
        """
        self.surfaces[position].thickness = thickness

    def getAvailableShapeNames(self):
        """
        Returns a list of valid Shape child class names (list of str)
        """
        return self.surfaces[0].availableShapeNames

    def getAvailableMaterialTypeNames(self):
        """
        Returns a list of valid Material child class names (list of str)
        """
        return self.surfaces[0].availableMaterialTypeNames

    def getAvailablePupilDefinitions(self):
        """
        Parses pupil.py for class defintions.
        
        :return listOfPupilTypeNames: List of strings
        :return listOfPupilTypeClasses: List of Class references
        """
        listOfPupilTypeNames = []
        listOfPupilTypeClasses = []
        for name, cla in inspect.getmembers(pupil):
            fullname = str(cla).strip()
            if fullname.startswith('<class \'pupil.'):
                listOfPupilTypeNames.append( name )
                listOfPupilTypeClasses.append( cla )
        return listOfPupilTypeNames, listOfPupilTypeClasses

    def setMaterial(self, position, materialType):
        """
        Sets the material of a surface.

        :param position: number of the surface (int)
        :param materialType: name of the Material child class (str)
          See OpticalSystem.getAvailableMaterialTypeNames() for details.
        """
        self.surfaces[position].setMaterial(materialType)

    def setMaterialCoefficients(self, position, coeff):
        """
        Sets the coefficients that determine the material behavior. 

        :param position: number of the surface (int)
        :param coeff: coefficients. Type and format depend on Material child class.
        """
        self.surfaces[position].setMaterialCoefficients(coeff)

    def setShape(self, position, shapeName):
        """
        Sets the shape of a surface.

        :param position: number of the surface (int)
        :param shapeName: name of the Shape child class (str)
          See OpticalSystem.getAvailableShapeNames() for details.
        """
        self.surfaces[position].setShape(shapeName)

    def setStopPosition(self, position):
        """
        Sets one surface as the stop. Don't forget to set its semi-diameter.

        :param position: number of the surface (int) 
        """
        self.stopPosition = position

    def getABCDMatrix(self, ray, firstSurfacePosition = 0, lastSurfacePosition = -1):
        """
        Returns an ABCD matrix of the optical system.
        The matrix is set up in geometric convention for (y, dy/dz) vectors.

        The matrix contains:
        - paraxial refraction from vacuum through the first surface
        - paraxial propagation through the system
        - paraxial refraction after the last surface into vacuum

        :param firstSurfacePosition: Position of the first surface to consider (int).
          Preset is 0 (object position).
        :param lastSurfacePosition: Position of the last surface to consider (int).
          Preset is -1 (image position)
        :param ray: Ray bundle object.
        :return abcd: ABCD matrix (2d numpy 2x2 matrix of float)
        """

        if lastSurfacePosition < 0:
            lastSurfacePosition = self.getNumberOfSurfaces() - lastSurfacePosition - 3

        abcd = [[1,0],[0,1]]

        for i in arange( lastSurfacePosition - firstSurfacePosition + 1) + firstSurfacePosition:
            abcd = dot( self.surfaces[i].getABCDMatrix(self.surfaces[i+1], ray)  ,  abcd )

        return abcd

    def getParaxialPupil(self, ray):
        """
        Returns the paraxially calculated pupil positions.

        :param ray: Raybundle object
        :return zen: entrance pupil position from object (float)
        :return magen: entrance pupil magnificaction; entrance pupil diameter per stop diameter (float)
        :return zex: exit pupil position from image (float)
        :return magex: exit pupil magnificaction; exit pupil diameter per stop diameter (float)
        """ 
        abcdObjStop = self.getABCDMatrix(ray, 0 , self.stopPosition - 1) # object to stop

        zen  = abcdObjStop[0,1] / abcdObjStop[0,0] # entrance pupil position from object
        magen = 1.0 / abcdObjStop[0,0]     

        abcdStopIm = self.getABCDMatrix(ray, self.stopPosition, -1) # stop to image

        zex = - abcdStopIm[0,1] / abcdStopIm[1,1] # exit pupil position from image
        magex = abcdStopIm[0,0] - abcdStopIm[0,1] * abcdStopIm[1,0] / abcdStopIm[1,1]

        return zen, magen, zex, magex, abcdObjStop, abcdStopIm

    def getEffectiveFocalLength(self, ray):
        """
        Returns the effective (paraxial) focal length of the system.

        :param ray: Raybundle object
        :return f: focal length (float)
        """
        abcd = self.getABCDMatrix(ray)
        return -1.0 / abcd[1,0]

    def getParaxialMagnification(self, ray):
        """
        Returns the paraxial real space magnification of the system.
        Before calculation, the image is shifted into paraxial   finite conjugate plane.
 
        :param ray: Raybundle object
        :return pmag: real space paraxial magnification (float)
        """
        abcd = self.getABCDMatrix(ray)
        print abcd
        return abcd[0,0] - abcd[0,1] * abcd[1,0] / abcd[1,1]

    def setPupilData(self, stopPosition, pupilType, pupilSize, wavelength):
        """
        Sets up the private data of this class required to aim rays through the pupil.

        :param stopPosition: surface number of the stop (int)
        :param pupilType: name of the class in pupil.py that defines the type of pupil (F#, NA, stop dia, ...) (str)
        :param pupilSize: size parameter of the pupil. Unit depends on pupilType. (float)
        :param wavelength: wavelength for pupil size calculation in um (float)
        """
        self.stopPosition = stopPosition

        pupilType = pupilType.upper().strip()
        if pupilType in self.listOfPupilTypeNames:
            i = self.listOfPupilTypeNames.index(pupilType)
        
            temp_ray = RayBundle(zeros((3,3)), zeros((3,3)), wavelength) # dummy ray 
            temp_obj = self.listOfPupilTypeClasses[i]()
            tenp_ms, self.stopDiameter = temp_obj.get_marginalSlope(self, temp_ray, pupilSize)
        else:
            print 'Warning: pupil type \'', pupilType, '\' not found. setPupilData() aborted.'      
            self.stopDiameter = 0

    def aimInitialRayBundle(self, fieldType, fieldSize):
        """
        Creates and returns a RayBundle object that aims at the optical system pupil.
        Pupil position is estimated paraxially.
        Aiming into the pupil is non-iterative, which means there is no check 
        whether the real ray actually hits the stop at the paraxially calculated position.
        
        TO DO: At the moment, this function fails to produce correct values for immersion
        """

        raise NotImplementedError()
        
        return raybundle


    def draw2d(self, ax, offset = [0,0], vertices=100, color="grey"):
        N = self.getNumberOfSurfaces()
        offy = offset[0]
        offz = offset[1]
        for i in arange(N):
            self.surfaces[i].draw2d(ax, offset = [offy, offz])
            offz += self.surfaces[i].thickness
 

