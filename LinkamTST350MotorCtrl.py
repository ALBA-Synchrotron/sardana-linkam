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
from sardana.pool.controller import MotorController

from sardana import State



class LinkamTST350MotorCtrl(MotorController):
    """This class is the Sardana motor controller for the Linkam TST350
    motor controller device. It is designed to work linked to the TangoDS
    XXXX.
    The axes order is:
    1: X
    2: Y
    3: Z
    """

    MaxDevice = 3

    AXIS_ATTR = ['PositionX', 'PositionY', 'PositionZ']
    class_prop = {'DeviceName':
                      {'Type': 'PyTango.DevString',
                       'Description': 'Device name of the Smaract MCS DS'}}

    ctrl_extra_attributes = {}

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
        self.attributes[axis] = {'step_per_unit': 1.0,
                                 'base_rate': 0,
                                 'acceleration': 0,
                                 'velocity': 1}

    def DeleteDevice(self, axis):
        self.attributes[axis] = None

    def StateAll(self):
        """
        Get State of all axes
        """
        self.idle = None
        try:
            self.idle = self.device.read_attribute('Idle').value
        except Exception as e:
            self._log.error('StateAll error: %s' % e)
            self.state = State.Fault
            self.status = 'DS communication problem'
            return

    def StateOne(self, axis):
        if self.idle != None:
            axis_idle = self.idle[axis-1]
            if axis_idle:
                self.state = State.On
                self.status = 'ON'
            else:
                self.state = State.Moving
                self.status = 'Moving'

        return self.state, self.status

    def ReadAll(self):
        self.positionMultiple = {}
        for axis in self.attributes.keys():
            attr = self.AXIS_ATTR[axis-1]
            value = self.device.read_attribute(attr).value
            pos = value / self.attributes[axis]['step_per_unit']
            self.positionMultiple[axis] = pos

    def ReadOne(self, axis):
        return self.positionMultiple[axis]

    def PreStartAll(self):
        self.startMultiple = {}

    def StartOne(self, axis, position):

        position = position * self.attributes[axis]['step_per_unit']
        self.startMultiple[axis] = position

    def StartAll(self):
        positions_list = []

        for i in range(3):
            if self.startMultiple.has_key(i+1):
                pos = self.startMultiple[i+1]
            else:
                attr = self.AXIS_ATTR[i]
                pos = self.device.read_attribute(attr).value
            positions_list.append(int(pos))
        print 'RH###: ', positions_list
        self.device.command_inout('MoveAbsolute', positions_list)

    def SetAxisPar(self, axis, name, value):
        """ Set the standard pool motor parameters.
        @param axis to set the parameter
        @param name of the parameter
        @param value to be set
        """
        name = name.lower()
        if name == 'velocity':
            velocity = int(value * self.attributes[axis]['step_per_unit'])
            if axis in [0, 1]:
                cmd = 'SetSpeedXY'
            else:
                cmd = 'SetSpeedZ'
            self.attributes[axis]['velocity'] = velocity
            self.device.command_inout(cmd, velocity)

        elif name in ['acceleration', 'deceleration']:
            self.attributes[axis]['acceleration'] = value

        elif name == "step_per_unit":
            self.attributes[axis]["step_per_unit"] = float(value)

        elif name == "base_rate":
            self.attributes[axis]["base_rate"] = float(value)

    def GetAxisPar(self, axis, name):
        """ Get the standard pool motor parameters.
        @param axis to get the parameter
        @param name of the parameter to get the value
        @return the value of the parameter
        """

        name = name.lower()
        if name == 'velocity':
            value = self.attributes[axis]['velocity'] / self.attributes[
                axis]['step_per_unit']

        elif name in ['acceleration', 'deceleration']:
            value = self.attributes[axis]['acceleration']

        elif name == "step_per_unit":
            value = self.attributes[axis]["step_per_unit"]

        elif name == "base_rate":
            value = self.attributes[axis]["base_rate"]

        return value

    def AbortOne(self, axis):
        if axis in [0, 1]:
            cmd = 'StopXY'
        else:
            cmd = 'StopZ'

        self.device.command_inout(cmd)

