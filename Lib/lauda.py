"""A small wrapper  / driver / to control the Lauda RP 250 E circulation thermostat
Defines a class for the instrument and stablish connection via raw TCP/IP serial 
"""

import time
import serial
import yaml
from PyQt6.QtCore import QThread


ERROR_TABLE = {
    'ERR_0': 'Connection with instrument not stablished.',
    'ERR_2': 'Wrong entry (for example, buffer overflow).',
    'ERR_3': 'Wrong command.',
    'ERR_5': 'Syntax error in value.',
    'ERR_6': 'Impermissible value.',
    'ERR_8': 'Module or value not available.',
    'ERR_30': 'All segments in the programmer are occupied.',
    'ERR_31': 'Not possible to specify set point value, analog set point input set to ON.',
    'ERR_33': 'An external temperature probe is missing.',
    'ERR_34': 'Analog value not present.',
    'ERR_35': 'Safety mode cannot be started because the Safety Mode function has not been activated.',
    'ERR_36': 'Not possible to specify set point value, programmer is running or has been paused.',
    'ERR_37': 'Impossible to start the programmer, analog set point value input is turned on.',
    'ERR_38 ': 'Not possible to activate from Safety Mode.',
}


class Lauda(QThread):
    """ Class Lauda describes the thermostat and all its parameters.
    Methods allow handling the instrument (setting and getting parameters)
    """

    def __init__(self, url=None):
        self.conn = None
        # temperature
        self.t_set = None
        self.t_int = None
        self.t_ext = None
        # pump
        self.pump_power_stage = None
        # bath level
        self.bath_level = None
        # actuating signal
        # self.signal = None
        # cooling
        self.cooling_mode = None
        # safety
        self.timeout = None
        self.safety_mode = None
        #control parameters
        self.xp = None
        self.tn = None
        self.tv = None
        self.td = None
        self.kp_e = None
        self.tn_e = None
        self.tv_e = None
        self.td_e = None
        self.correction = None
        self.xp_f = None
        self.p_rop_e = None
        # control
        self.t_set_offset = None
        self.control_var = None
        self.offset_var = None
        # status
        self.standby = None
        self.type = None
        self.device_status = None
        self.stat = None

        if url:
            self.open(url)
            if self.conn:
                self.get_all_parameters()


    def open(self, url):
        try:
            self.conn = serial.serial_for_url(f'socket://{url}', timeout=0.1, write_timeout=0.1)
        except serial.serialutil.SerialException as e:
            print(e)
            self.conn = None


    def close(self):
        if self.conn:
            self.conn.close()

    
    def _send_command(self, command):
        command = str.upper(command)
        if self.conn:
            self.conn.write(bytes(f'{command}\r\n', encoding='utf-8', errors='strict'))
            result = self.conn.read_until(b'\r\n').decode().strip()
        else:
            result = 'ERR_0'

        return result


    def set_t_set(self, t_set):
        result = self._send_command(f'OUT_SP_00_{t_set}')
        if result == 'OK':
            self.t_set = t_set
        return result


    def set_pump_power_stage(self, pump_power_stage):
        result = self._send_command(f'OUT_SP_01_{pump_power_stage}')
        if result == 'OK':
            self.pump_power_stage = pump_power_stage
        return result


    def set_cooling_mode(self, cooling_mode):
        result = self._send_command(f'OUT_SP_02_{cooling_mode}')
        if result == 'OK':
            self.cooling_mode = cooling_mode
        return result


    def set_timeout(self, timeout):
        result = self._send_command(f'OUT_SP_08_{timeout}')
        if result == 'OK':
            self.timeout = timeout
        return result
    

    def set_safety_mode(self):
        result = self._send_command(f'OUT_MODE_06_1')
        if result == 'OK':
            self.safety_mode = 1
        return result


    def set_xp(self, xp):
        result = self._send_command(f'OUT_PAR_00_{xp}')
        if result == 'OK':
            self.xp = xp
        return result


    def set_tn(self, tn):
        result = self._send_command(f'OUT_PAR_01_{tn}')
        if result == 'OK':
            self.tn = tn
        return result


    def set_tv(self, tv):
        result = self._send_command(f'OUT_PAR_02_{tv}')
        if result == 'OK':
            self.tv = tv
        return result


    def set_td(self, td):
        result = self._send_command(f'OUT_PAR_03_{td}')
        if result == 'OK':
            self.td = td
        return result


    def set_kp_e(self, kp_e):
        result = self._send_command(f'OUT_PAR_04_{kp_e}')
        if result == 'OK':
            self.kp_e = kp_e
        return result


    def set_tn_e(self, tn_e):
        result = self._send_command(f'OUT_PAR_05_{tn_e}')
        if result == 'OK':
            self.tn_e = tn_e
        return result


    def set_tv_e(self, tv_e):
        result = self._send_command(f'OUT_PAR_06_{tv_e}')
        if result == 'OK':
            self.tv_e = tv_e
        return result


    def set_td_e(self, td_e):
        result = self._send_command(f'OUT_PAR_07_{td_e}')
        if result == 'OK':
            self.td_e = td_e
        return result


    def set_correction(self, correction):
        result = self._send_command(f'OUT_PAR_09_{correction}')
        if result == 'OK':
            self.correction = correction
        return result


    def set_xp_f(self, xp_f):
        result = self._send_command(f'OUT_PAR_10_{xp_f}')
        if result == 'OK':
            self.xp_f = xp_f
        return result


    def set_p_rop_e(self, p_rop_e):
        result = self._send_command(f'OUT_PAR_15_{p_rop_e}')
        if result == 'OK':
            self.p_rop_e = p_rop_e
        return result


    def set_t_set_offset(self, t_set_offset):
        result = self._send_command(f'OUT_PAR_14_{t_set_offset}')
        if result == 'OK':
            self.t_set_offset = t_set_offset
        return result


    def set_control_var(self, control_var):
        result = self._send_command(f'OUT_MODE_01_{control_var}')
        if result == 'OK':
            self.control_var = control_var
        return result


    def set_offset_var(self, offset_var):
        result = self._send_command(f'OUT_MODE_04_{offset_var}')
        if result == 'OK':
            self.offset_var = offset_var
        return result


    def get_t_set(self):
        result = self._send_command(f'IN_SP_00')
        if 'ERR' in result:
            self.t_set = None
        else:
            self.t_set = float(result)
        return result


    def get_t_int(self):
        result = self._send_command(f'IN_PV_10')
        if 'ERR' in result:
            self.t_int = None
        else:
            self.t_int = float(result)
        return result


    def get_t_ext(self):
        result = self._send_command(f'IN_PV_13')
        if 'ERR' in result:
            self.t_ext = None
        else:
            self.t_ext = float(result)
        return result


    def get_pump_power_stage(self):
        result = self._send_command(f'IN_SP_01')
        if 'ERR' in result:
            self.pump_power_stage = None
        else:
            self.pump_power_stage = int(result)
        return result


    def get_bath_level(self):
        result = self._send_command(f'IN_PV_05')
        if 'ERR' in result:
            self.bath_level = None
        else:
            self.bath_level = int(result)
        return result


    # this command returns ERR_03 always. Probably not implemented in the thermostat
    # def get_signal(self):
    #     result = self._send_command(f'IN_PV_06')
    #     if 'ERR' in result:
    #         self.signal = None
    #     else:
    #         self.signal = float(result)
    #     return result


    def get_cooling_mode(self):
        result = self._send_command(f'IN_SP_02')
        if 'ERR' in result:
            self.cooling_mode = None
        else:
            self.cooling_mode = int(result)
        return result


    def get_timeout(self):
        result = self._send_command(f'IN_SP_08')
        if 'ERR' in result:
            self.timeout = None
        else:
            self.timeout = int(result)
        return result
    

    def get_safety_mode(self):
        result = self._send_command(f'IN_MODE_06')
        if 'ERR' in result:
            self.safety_mode = None
        else:
            self.safety_mode = int(result)
        return result


    def get_xp(self):
        result = self._send_command(f'IN_PAR_00')
        if 'ERR' in result:
            self.xp = None
        else:
            self.xp = float(result)
        return result


    def get_tn(self):
        result = self._send_command(f'IN_PAR_01')
        if 'ERR' in result:
            self.tn = None
        else:
            self.tn = float(result)
        return result


    def get_tv(self):
        result = self._send_command(f'IN_PAR_02')
        if 'ERR' in result:
            self.tv = None
        else:
            self.tv = float(result)
        return result


    def get_td(self):
        result = self._send_command(f'IN_PAR_03')
        if 'ERR' in result:
            self.td = None
        else:
            self.td = float(result)
        return result


    def get_kp_e(self):
        result = self._send_command(f'IN_PAR_04')
        if 'ERR' in result:
            self.kp_e = None
        else:
            self.kp_e = float(result)
        return result


    def get_tn_e(self):
        result = self._send_command(f'IN_PAR_05')
        if 'ERR' in result:
            self.tn_e = None
        else:
            self.tn_e = float(result)
        return result


    def get_tv_e(self):
        result = self._send_command(f'IN_PAR_06')
        if 'ERR' in result:
            self.tv_e = None
        else:
            self.tv_e = float(result)
        return result


    def get_td_e(self):
        result = self._send_command(f'IN_PAR_07')
        if 'ERR' in result:
            self.td_e = None
        else:
            self.td_e = float(result)
        return result


    def get_correction(self):
        result = self._send_command(f'IN_PAR_09')
        if 'ERR' in result:
            self.correction = None
        else:
            self.correction = float(result)
        return result


    def get_xp_f(self):
        result = self._send_command(f'IN_PAR_10')
        if 'ERR' in result:
            self.xp_f = None
        else:
            self.xp_f = float(result)
        return result


    def get_p_rop_e(self):
        result = self._send_command(f'IN_PAR_15')
        if 'ERR' in result:
            self.p_rop_e = None
        else:
            self.p_rop_e = float(result)
        return result


    def get_t_set_offset(self):
        result = self._send_command(f'IN_PAR_14')
        if 'ERR' in result:
            self.t_set_offset = None
        else:
            self.t_set_offset = float(result)
        return result


    def get_control_var(self):
        result = self._send_command(f'IN_MODE_01')
        if 'ERR' in result:
            self.control_var = None
        else:
            self.control_var = int(result)
        return result


    def get_offset_var(self):
        result = self._send_command(f'IN_MODE_04')
        if 'ERR' in result:
            self.offset_var = None
        else:
            self.offset_var = int(result)
        return result


    def get_standby(self):
        result = self._send_command(f'IN_MODE_02')
        if 'ERR' in result:
            self.standby = None
        else:
            self.standby = int(result)
        return result


    def get_type(self):
        result = self._send_command(f'TYPE')
        if 'ERR' in result:
            self.type = None
        else:
            self.type = result
        return result


    def get_device_status(self):
        result = self._send_command(f'STATUS')
        if 'ERR' in result:
            self.device_status = None
        else:
            self.device_status = int(result)
        return result

    def get_stat(self):
        result = self._send_command(f'STAT')
        if 'ERR' in result:
            self.stat = None
        else:
            self.stat = result
        return result


    def start(self):
        result = self._send_command('START')
        if result == '0K':
            self.standby = 0
            time.sleep(15)
        return result


    def stop(self):
        result = self._send_command('STOP')
        if result == '0K':
            self.standby = 1
        return result

    
    def get_all_parameters(self):
        self.get_t_set()
        self.get_t_int()
        self.get_t_ext()
        self.get_pump_power_stage()
        self.get_bath_level()
        # self.get_signal()
        self.get_cooling_mode()
        self.get_timeout()
        self.get_safety_mode()
        self.get_xp()
        self.get_tn()
        self.get_tv()
        self.get_td()
        self.get_kp_e()
        self.get_tn_e()
        self.get_tv_e()
        self.get_td_e()
        self.get_correction()
        self.get_xp_f()
        self.get_p_rop_e()
        self.get_t_set_offset()
        self.get_control_var()
        self.get_offset_var()
        self.get_standby()
        self.get_type()
        self.get_device_status()
        self.get_stat()


    def set_all_parameters(self, config_file):
        with open(config_file, 'r') as file:
            parameters = yaml.safe_load(file)

        if parameters:
            self.set_t_set(parameters['t_set'])
            self.set_pump_power_stage(parameters['pump_power_stage'])
            self.set_cooling_mode(parameters['cooling_mode'])

            self.set_xp(parameters['xp'])
            self.set_tn(parameters['tn'])
            self.set_tv(parameters['tv'])
            self.set_td(parameters['td'])
            self.set_kp_e(parameters['kp_e'])
            self.set_tn_e(parameters['tn_e'])
            self.set_tv_e(parameters['tv_e'])
            self.set_td_e(parameters['td_e'])
            self.set_correction(parameters['correction'])
            self.set_xp_f(parameters['xp_f'])
            self.set_p_rop_e(parameters['p_rop_e'])

            self.set_t_set_offset(parameters['t_set_offset'])
            self.set_control_var(parameters['control_x'])
            self.set_offset_var(parameters['offset_x'])


    def __str__(self):
        print(f'conn: {"CONNECTED" if self.conn else "NOT CONNECTED"}')
        print(f't_set: {self.t_set}')
        print(f't_int: {self.t_int}')
        print(f't_ext: {self.t_ext}')
        print(f'pump_power_stage: {self.pump_power_stage}')
        print(f'bath_level: {self.bath_level}')
        # print(f'signal: {self.signal}')
        print(f'cooling_mode: {self.cooling_mode}')
        print(f'timeout: {self.timeout}')
        print(f'safety_mode: {self.safety_mode}')
        print(f'xp: {self.xp}')
        print(f'tn: {self.tn}')        
        print(f'tv: {self.tv}')
        print(f'td: {self.td}')
        print(f'kp_e: {self.kp_e}')
        print(f'tn_e: {self.tn_e}')
        print(f'tv_e: {self.tv_e}')
        print(f'td_e: {self.td_e}')
        print(f'correction: {self.correction}')
        print(f'xp_f: {self.xp_f}')
        print(f'p_rop_e: {self.p_rop_e}')
        print(f't_set_offset: {self.t_set_offset}')
        print(f'control_var: {self.control_var}')
        print(f'offset_var: {self.offset_var}')
        print(f'standby: {self.standby}')
        print(f'type: {self.type}')
        print(f'device_status: {self.device_status}')
        print(f'stat: {self.stat}')
