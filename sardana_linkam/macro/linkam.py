import time
import numpy as np
import PyTango as tango
from sardana.macroserver.macro import Macro, Type

LINKAMT95=95
LINKAMT96=96
UPDATE_LINE = u'\033[1A\033[K'


class linkam_base(Macro):
    def prepare(self, *args, **kwargs):
        dev_name = self.getEnv("LinkamDevice")
        self.linkam_dev = tango.DeviceProxy(dev_name)
        if hasattr(self.linkam_dev, "tst_gap"):
            self.temperature_attr = "temperature_t96"
            self.model = LINKAMT96
        else:
            self.temperature_attr = "Temperature"
            self.model = LINKAMT95

    def get_linkam_temperature(self):
        return self.linkam_dev.read_attribute(self.temperature_attr).value


class linkam_force_zero(linkam_base):
    """Macro that resets the force to zero in the Linkam Device Server."""
    def run(self):
        assert self.model == LINKAMT96, "Use model LinkamT96"
        self.linkam_dev.ForceZeroTST()
        self.output("LinkamT96 force reseted to zero")

class linkam_read_status(linkam_base):
    """Read linkam status."""

    def run(self):
        status = self.linkam_dev.read_attribute('Status').value
        self.output('Linkam Status: %s' % status)
        return status


class linkam_read_temperature(linkam_base):
    """Read linkam temperature."""

    def run(self):
        temperature = self.get_linkam_temperature()
        self.output('Linkam Temperature: %.1f' % temperature)
        return temperature


class linkam_read_pumpspeed(linkam_base):
    """Read linkam pumpspeed."""

    def run(self):
        pumpspeed = self.linkam_dev.read_attribute('Pumpspeed').value
        self.output('Linkam Pumpspeed: %d' % pumpspeed)
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
    param_def = [['target', Type.Float, None, 'Target temperature (degC)'],
                 ['rate', Type.Float, None, 'Ramp rate (degC/min)']]

    def run(self, target, rate):
        args = (rate, target)
        self.linkam_dev.command_inout('StartRamp', args)
        self.debug("Linkam temperature ramp started.")

    


class linkam_stop_ramp(linkam_base):
    """Stop linkam ramping."""

    def run(self):
        self.linkam_dev.command_inout('StopRamp')
        self.debug("Linkam temperature ramp stopped. This cuts the power to the heater.")


class linkam_stop_t96gap(linkam_base):
    """Stop linkam gap movement."""

    def run(self):
        self.linkam_dev.command_inout('StopTSTMotor')
        self.debug("Linkam gap movement stopped. Motor stopped moving.")


class linkam_hold_temperature(linkam_base):
    """Hold current temperature"""

    def run(self):
        self.linkam_dev.command_inout('HoldTemp')
        self.debug("Holding current linkam temperature.")


class linkam_stop(linkam_base):
    """Stop linkam temperature ramp."""

    def run(self):
        self.linkam_dev.command_inout('StopRamp')
        self.linkam_dev.write_attribute('Pumpspeed', 0)
        self.linkam_dev.write_attribute('PumpMode', 0)  # Auto
        self.debug("Linkam temperature ramp stopped. This cuts the power to the heater.")
        self.debug("Linkam LNP (Liquid Nitrogen Pump) mode to automatic and LNP speed to 0.")


class linkam_ramp(linkam_base):
    """Proceed with a linkam temperature ramp"""
    param_def = [['target', Type.Float, None, 'Target temperature (degC)'],
                 ['rate', Type.Float, None, 'Ramp rate (degC/min)']]


    def on_abort(self):
        self.linkam_dev.command_inout('HoldTemp')

    def run(self, target, rate, output_block=True):
        self.info('Running Linkam ramp')
        # initial temperature
        tempi = self.get_linkam_temperature()
        rampup = target > tempi

        args = (rate, target)
        self.linkam_dev.command_inout('StartRamp', args)

        temp, t0 = tempi, ''
        while ((target > temp and rampup) or
               (target < temp and not rampup)):
            time.sleep(0.1)
            temp = self.get_linkam_temperature()
            progress = 100 * (temp - tempi) / (target - tempi)
            yield progress if progress < 100 else 100
            if output_block:
                if temp != t0:
                    self.info(
                        UPDATE_LINE + 'Linkam Temperature: %.2f degC [Progress: %.1f%%]' % (
                        temp, progress))
                    t0 = temp
            self.checkPoint()
        self.info(UPDATE_LINE + 'Linkam is holding at %s degC' % target)


class linkam_ramp_old(linkam_base):
    """Proceed with a linkam temperature ramp"""
    param_def = [['rate', Type.Float, None, 'Rate in deg/sec.'],
                 ['temperature', Type.Float, None, 'Target temperature.'],
                 ['pump_profile', Type.String, '', 'Pump speed profile file']]

    def on_abort(self):
        self.linkam_dev.command_inout('HoldTemp')

    def run(self, rate, temperature, pump_profile):
        # initial temperature
        tempi = self.get_linkam_temperature()
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
            temp = self.get_linkam_temperature()
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
        try:
            ds = tango.DeviceProxy(device)
            self.debug("Device %s is %s" % (device, str(ds.state())))
            self.execMacro('senv LinkamDevice %s' % device)
        except Exception as error:
            for e in error.args:
                self.error(e.desc)
