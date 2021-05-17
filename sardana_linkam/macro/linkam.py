import time
import numpy as np
import PyTango as tango
from sardana.macroserver.macro import Macro, Type


class linkam_base(Macro):
    def prepare(self):
        dev_name = self.getEnv("LinkamDevice")
        self.linkam_dev = tango.DeviceProxy(dev_name)


class linkam_read_status(linkam_base):
    """Read linkam status."""
    def run(self):
        status = self.linkam_dev.read_attribute('Status').value
        self.output('Linkam TP94 Status: %s' % status)
        return status


class linkam_read_temperature(linkam_base):
    """Read linkam temperature."""
    def run(self):
        temperature = self.linkam_dev.read_attribute('Temperature').value
        self.output('Linkam TP94 Temperature: %.1f' % temperature)
        return temperature


class linkam_read_pumpspeed(linkam_base):
    """Read linkam pumpspeed."""
    def run(self):
        pumpspeed = self.linkam_dev.read_attribute('Pumpspeed').value
        self.output('Linkam TP94 Pumpspeed: %d' % pumpspeed)
        return pumpspeed


class linkam_write_pumpspeed(linkam_base):
    """Write linkam pumpspeed."""
    param_def = [['speed', Type.Integer, 0, '0-30 value (0 is stop).']]
    def run(self, speed):
        self.linkam_dev.write_attribute('Pumpspeed', speed)


class linkam_pumpmode(linkam_base):
    """Set linkam pump mode. 0: automatic 1: manual 2: driven."""
    param_def = [['mode', Type.Integer, 1, '0 Auto, 1 Manual, 2, Driven']]
    def run(self, mode):
        self.linkam_dev.write_attribute('PumpMode', mode)


class linkam_start_ramp(linkam_base):
    """Start linkam ramping."""
    param_def = [['rate', Type.Float, None, 'Rate in deg/sec.'],
                 ['temperature', Type.Float, None, 'Target temperature.']]
    def run(self, rate, temperature):
        args = (rate, temperature)
        self.linkam_dev.command_inout('StartRamp', args)
        self.output('Done. (check status with %linkam_read_status macro)')
        

class linkam_stop_ramp(linkam_base):
    """Stop linkam ramping."""
    def run(self):
        self.linkam_dev.command_inout('StopRamp')


class linkam_hold_temperature(linkam_base):
    """Hold current temperature"""
    def run(self):
        self.linkam_dev.command_inout('HoldTemp')


class linkam_stop(linkam_base):
    """Stop linkam."""
    def run(self):
        self.linkam_dev.command_inout('StopRamp')
        self.linkam_dev.write_attribute('Pumpspeed', 0)
        self.linkam_dev.write_attribute('PumpMode', 0) # Auto


class linkam_ramp(linkam_base):
    """Proceed with a linkam temperature ramp"""
    param_def = [['rate', Type.Float, None, 'Rate in deg/sec.'],
                 ['temperature', Type.Float, None, 'Target temperature.']]

    def on_abort(self):
        self.linkam_dev.command_inout('HoldTemp')

    def run(self, rate, temperature, output_block=False):
        #initial temperature
        tempi = self.linkam_dev.read_attribute('Temperature').value
        rampup = temperature > tempi

        args = (rate, temperature)
        self.linkam_dev.command_inout('StartRamp', args)

        temp = tempi
        while ((temperature > temp and rampup) or 
               (temperature < temp and not rampup)):
            time.sleep(0.1)
            temp = self.linkam_dev.read_attribute('Temperature').value

            progress = 100 * (temp - tempi) / (temperature - tempi)
            yield progress if progress < 100 else 100
            if output_block:
                self.outputBlock('Current Temp: %2.4f' %temp)
            self.checkPoint()


class linkam_ramp_old(linkam_base):
    """Proceed with a linkam temperature ramp"""
    param_def = [['rate', Type.Float, None, 'Rate in deg/sec.'],
                 ['temperature', Type.Float, None, 'Target temperature.'],
                 ['pump_profile', Type.String, '', 'Pump speed profile file']]

    def on_abort(self):
        self.linkam_dev.command_inout('HoldTemp')

    def run(self, rate, temperature, pump_profile):
        #initial temperature
        tempi = self.linkam_dev.read_attribute('Temperature').value
        rampup = temperature > tempi
        pumpDynamic = pump_profile != ''

        # If a pump speed profile is given the pump speed will be adjusted
        # during the ramp. 
        # Here the profile data is loaded from the file into T and P tables
        if pumpDynamic:
            pumpFile = file(pump_profile)
            lines = pumpFile.readlines()
            pumpFile.close()
            self.T_table, self.P_table = [], []
            for line in lines[1:]:
                val = list(map(float, line.split()))
                self.T_table.append(val[0])
                self.P_table.append(val[1])
            if rampup:
                self.linkam_dev.write_attribute('Pumpspeed', 0)

        args = (rate, temperature)
        self.linkam_dev.command_inout('StartRamp', args)

        temp = tempi
        while ((temperature > temp and rampup) or 
               (temperature < temp and not rampup)):
            time.sleep(0.1)
            temp = self.linkam_dev.read_attribute('Temperature').value
        # The pump speed will be interpolated from the values given in the
        # pump profile file. Only for ramp down. In ramp ups the pump is off
            if pumpDynamic and not rampup:
                pump = np.interp(temp, self.T_table, self.P_table)
                self.linkam_dev.write_attribute('Pumpspeed', int(pump))

            progress = 100 * (temp - tempi) / (temperature - tempi)
            yield progress if progress < 100 else 100
            self.checkPoint()

        if pumpDynamic:
            pump = np.interp(temp, self.T_table, self.P_table)
            self.linkam_dev.write_attribute('Pumpspeed', int(pump))


class linkam_set_device(Macro):
    """Set linkam device server"""
    param_def = [['device', Type.String, None, 'Device name.']]
    
    
    def run(self, device):
        self.execMacro('senv LinkamDevice %s' % device)

