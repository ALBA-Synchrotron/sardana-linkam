#!/usr/bin/env python

#############################################################################
##
## file :    LinkamTST350TempMotorCtrl.py
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
from sardana.pool.controller import MotorController
from sardana import State


class LinkamTST350TempMotorCtrl(MotorController):
    """This class is the Sardana motor controller for the Linkam TST350
    temperature controller device.

    Requires the PyLinkam TangoDS.

    The controller contains a single axis corresponding to the temperature.
    Only the velocity and position concepts has sense for this controller and
    any other axis parameter (acceleration, deceleration and baserate) has no
    sense.

    Position units: degrees.
    Velocity units: degrees/second
    """

    MaxDevice = 1
    AXIS_ATTR = 'Temperature'
    class_prop = {'DeviceName':
                      {'Type': 'PyTango.DevString',
                       'Description': 'Device name of the Linkam TST350'}}

    ctrl_extra_attributes = {}

    def __init__(self, inst, props, *args, **kwargs):

        try:
            MotorController.__init__(self, inst, props, *args, **kwargs)
            self.device = PyTango.DeviceProxy(self.DeviceName)
            self.attributes = {}

        except Exception as e:
            self._log.error('Error when init: %s' % e)
            raise

    def AddDevice(self, axis):
        self._log.debug('Adding device...')
        self.attributes[axis] = {'step_per_unit': 1.0,
                                 'base_rate': 0,
                                 'acceleration': 0,
                                 'velocity': 1}

    def DeleteDevice(self, axis):
        self.attributes[axis] = None

    def StateOne(self, axis):
        try:
            state = self.device.read_attibute('Program').value
        except Exception as e:
            self._log.error('StateOne error: %s' % e)
            self.state = State.Fault
            self.status = 'DS communication problem'
            return

        if state.lower() == 'cooling' or state.lower() == 'heating':
            self.state = State.Moving
        elif state.lower() == 'Stopped':
            self.state = State.Alarm
        else:
            self.state = State.On
        self.status = state
        return self.state, self.status

    def ReadOne(self, axis):
        attr = self.AXIS_ATTR
        value = self.device.read_attibute(attr).value
        temp = value / self.attributes[axis]['step_per_unit']
        return temp

    def StartOne(self, axis, temperature):
        temperature = temperature * self.attributes[axis]['step_per_unit']
        velocity = self.attributes[axis]['velocity']
        self.device.command_inout('StartRamp', velocity, temperature)

    def AbortOne(self, axis):
        self.device.command_inout('HoldTemp')

    def SetAxisPar(self, axis, name, value):
        """ Set the standard pool motor parameters.
        @param axis to set the parameter
        @param name of the parameter
        @param value to be set
        """
        name = name.lower()
        if name == 'velocity':
            self.attributes[axis]['velocity'] = float(value)

        elif name in ['acceleration', 'deceleration']:
            self.attributes[axis]['acceleration'] = float(value)

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
            value = self.attributes[axis]['velocity']

        elif name in ['acceleration', 'deceleration']:
            value = self.attributes[axis]['acceleration']

        elif name == "step_per_unit":
            value = self.attributes[axis]["step_per_unit"]

        elif name == "base_rate":
            value = self.attributes[axis]["base_rate"]

        return value


