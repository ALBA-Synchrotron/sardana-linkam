#!/usr/bin/env python

#############################################################################
##
## file :    LinkamTST350MotorCtrl.py
##
## developers : ctbeamlines@cells.es
##
## copyleft :    Cells / Alba Synchrotron
##               Bellaterra
##               Spain
##
#############################################################################
##
## This file is part of Sardana.
##
## This is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This software is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
###########################################################################

import PyTango
import time
from sardana.pool.controller import (MotorController, Type, Description,
                                     DefaultValue)

from sardana import State



class LinkamT96MotorCtrl(MotorController):
    """This class is the Sardana motor controller for the device Linkam T96.
    The idea of this class is to be a generic motor controller for all the stages that
    are compatible with the idea of a motor controller.
    It is designed to work linked to the TangoDS <linkamt96>.
    The axes order is:
    1: TST350Motor
    2: TST350Temperature
    3: CSS450Motor...
    4: ...
    """

    MaxDevice = 3

    # tst_stretcher = "tst_stretcher"
    # tst_temperature = "tst_temperature"
    # css_shearing = "css_shearing"

    axis2motor = {
        1: 'axis_tst_stretcher',
        2: 'axis_tst_temperature',
        3: 'axis_css_shearing'
    }

    AXIS_ATTR = ['PositionX', 'PositionY', 'PositionZ']
    ctrl_properties = {'DeviceName':
                      {Type: 'str',
                       Description: 'Device name of the Linkam T-96 DS'}}

    axis_attributes = {}

    def __init__(self, inst, props, *args, **kwargs):

        try:
            MotorController.__init__(self, inst, props, *args, **kwargs)
            self.device = PyTango.DeviceProxy(self.DeviceName)
            self.startMultiple = {}
            self.positionMultiple = {}
            self.attributes = {}

        except Exception as e:
            self._log.error('Error when init: %s' % e)
            raise

    def AddDevice(self, axis):
        self._log.debug('AddDevice entering...')
        axis_name = self.axis2motor[axis]
        if axis_name == "axis_tst_stretcher":
            self.attributes[axis_name] = {'step_per_unit': 1.0,
                                     'velocity': 1}
            
        elif axis_name == "axis_tst_temperature":
            # We do not need to store any attribute for this axis
            pass

    def DeleteDevice(self, axis):
        self._log.debug('DeleteDevice entering...')
        axis_name = self.axis2motor[axis]
        if axis_name == "axis_tst_stretcher":
            self.attributes[axis_name] = None

    def StateAll(self):
        self._log.debug('Entering StateAll...')
        self.device.UpdateStateFlags()

    def StateOne(self, axis):
        axis_name = self.axis2motor[axis]
        self._log.debug('Entering StateOne for axis {} ({})'.format(axis, axis_name))

        if axis_name == 'axis_tst_stretcher':
            attribute = 'tst_stretching'
        elif axis_name == 'axis_tst_temperature':
            attribute = 'heater_ramping'
        
        if self.device.read_attribute(attribute).value:
            self.state = State.Moving
        else:
            self.state = State.On

        return self.state

    def ReadAll(self):
        pass

    def ReadOne(self, axis):
        axis_name = self.axis2motor[axis]
        self._log.debug('Entering ReadOne for axis {} ({})'.format(axis, axis_name))
        
        if axis_name == 'axis_tst_stretcher':
            attr = 'tst_gap'
            value = self.device.read_attribute(attr).value
            pos = value / self.attributes[axis_name]['step_per_unit']

        elif axis_name == 'axis_tst_temperature':
            attr = 'temperature'
            value = self.device.read_attribute(attr).value

        return value

    def StartOne(self, axis, position):
        axis_name = self.axis2motor[axis]
        self._log.debug('Entering StartOne for axis {} ({})'.format(axis, axis_name))

        if axis_name == 'axis_tst_stretcher':
            position = position * self.attributes[axis_name]['step_per_unit']
            cmd = 'MoveGapAbsolute'

        elif axis_name == 'axis_tst_temperature':
            cmd = 'StartTemperatureRamp'

        self.device.command_inout(cmd, position)

    def StartAll(self):
        pass

    def SetAxisPar(self, axis, name, value):
        """ Set the standard pool motor parameters.
        @param axis to set the parameter
        @param name of the parameter
        @param value to be set
        """
        name = name.lower()
        axis_name = self.axis2motor[axis]

        if name == 'velocity':
            if axis_name == 'axis_tst_stretcher':
                attr = 'tst_motor_velocity'
                velocity = int(value * self.attributes[axis_name]['step_per_unit'])
                self.device.write_attribute(attr, velocity)
                self.attributes[axis_name]['velocity'] = velocity

            elif axis_name == 'axis_tst_temperature':
                attr = 'ramp_rate'
                self.device.write_attribute(attr, value)

        elif name == "step_per_unit":
            if axis_name == 'axis_tst_stretcher':
                self.attributes[axis_name]["step_per_unit"] = float(value)

            elif axis_name == 'axis_tst_temperature':
                raise Exception("{} is not supported for axis {} ({})".format(name, axis, axis_name))

        elif name in ['acceleration', 'deceleration', 'base_rate']:
            if axis in ['tst_stretcher', 'tst_temperature']:
                raise Exception("{} does not support {}".format(self.__class__.__name__, name))

    def GetAxisPar(self, axis, name):
        """ Get the standard pool motor parameters.
        @param axis to get the parameter
        @param name of the parameter to get the value
        @return the value of the parameter
        """

        name = name.lower()
        axis_name = self.axis2motor[axis]
        
        if name == 'velocity':
            if axis_name == 'axis_tst_stretcher':
                # Return memorized attribute because reading of the Tango DS attribute
                # is sometimes incorrect when we set a new velocity. 
                # It only gets correctly updated in the DS once you move the motor.
                value = self.attributes[axis_name]['velocity'] / self.attributes[axis_name]['step_per_unit']
                
            elif axis_name == 'axis_tst_temperature':
                value = self.device.ramp_rate

        elif name == "step_per_unit":
            if axis_name == 'axis_tst_stretcher':
                value = self.attributes[axis_name]["step_per_unit"]

            elif axis_name == 'axis_tst_temperature':
                raise Exception("{} is not supported for axis {} ({})".format(name, axis, axis_name))

        elif name in ['acceleration', 'deceleration', 'base_rate']:
            if axis in ['tst_stretcher', 'tst_temperature']:
                raise Exception("{} does not support {}".format(self.__class__.__name__, name))

        return value

    def AbortOne(self, axis):
        axis_name = self.axis2motor[axis]
        self._log.debug('In method AbortOne of axis {} ({})'.format(axis, axis_name))
        if axis_name == 'axis_tst_stretcher':
            cmd = 'StopTSTMotor'
        elif axis_name == 'axis_tst_temperature':
            cmd = 'HoldTemperature'

        self.device.command_inout(cmd)

