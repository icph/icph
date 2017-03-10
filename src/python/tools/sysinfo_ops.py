#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2016, Intel Corporation. All rights reserved.
# This file is licensed under the GPLv2 license.
# For the full content of this license, see the LICENSE.txt
# file at the top level of this source tree.


import math
import socket
import platform
import os
import pwd
import grp
import manage_config
from time import ctime
from datetime import timedelta
from netifaces import interfaces, ifaddresses, AF_INET
from tools import logging_helper, shell_ops

# global variables used across modules
sysVersion = str("Not Set")
rcpl_version = str("Not Set")
arch = str("Not Set")
display_arch = str("Not Set")
os_type = str("Not Set")


class DataCollect(object):

    def __init__(self):
        self.__ss_id = None
        self.__data_set = {}
        # self.__lan_ip_addr = {}
        # self.__wan_ip_addr = {}
        self.__net_interface = {}
        self.__minutes = None
        self.__hours = None
        self.__days = None
        self.__disk_usage = {}
        self.__free = 0.0
        self.__total = 0.0
        self.__used = 0.0
        self.__log_helper = logging_helper.logging_helper.Logger()
        self.__uptime = None

    def getHostname(self):
        """ Return host name.
        Returns:
            str: host name
        """
        return socket.gethostname()

    def getModel(self):
        """ Return processor model.
        Returns:
            str: processor model
        """
        return platform.processor()

    def getLanIPAddr(self):
        """ Return land and wan ip addresses.
        Returns:
            tuple: 1st is str of lan ip address. 2nd is str of wan ip address.
        """
        iface_name = interfaces()

        for adapter in iface_name:
            if not ('lo' == adapter):  # filter out the 'lo' loopback interface
                adapter_config = ifaddresses(adapter).setdefault(AF_INET, [{'addr': 'na'}])  # get IPv4 address
                ip_address = adapter_config[0]['addr']
                if not (ip_address == 'na'):  # filter out interface without ip address
                    self.__net_interface[adapter] = ip_address
        return self.__net_interface


    def getWifiSSID(self):
        """ Return WiFi SSID.
        Returns:
            str: WiFi SSID
        """
        '''self.__ss_id = shell_ops.run_command('uci show wireless.@wifi-iface[0].ssid')
        if 'not found' in self.__ss_id:
            return 'No Wireless'
        self.__ss_id = self.__ss_id.strip('\n').split('=')'''
        return 'tbd'

    def getDateTime(self):
        """ Return current date time.
        Returns:
            str: current date time.
        """
        return ctime()

    def getUpTime(self):
        """ Return system up time.
        Returns:
            str: system up time.
        """
        with open('/proc/uptime', 'r') as f:
            r = float(f.readline().split()[0])
            upt = timedelta(seconds = r)
        t = str(upt)
        if upt.days > 0:
            t = t.split(' ')[2]
        t = t.split(':')
        self.__days = upt.days
        self.__minutes = t[1]
        self.__hours = t[0]
        self.__uptime = '%sd %sh %sm' % (self.__days, self.__hours, self.__minutes)
        return self.__uptime

    def getPlatform(self):
        config = manage_config.read_config_file()
        return config.get('General', 'target_platform')

    def getSensorConfig(self):
        config = manage_config.read_config_file()
        return config.get('General', 'sensor_tab')

    def getSoftSOCConfig(self):
        config = manage_config.read_config_file()
        return config.get('General', 'softsoc_tab')

    def getRefSWConfig(self):
        config = manage_config.read_config_file()
        return config.get('General', 'ref_sw_tab')

    def getPackageConfig(self):
        config = manage_config.read_config_file()
        return config.get('General', 'package_tab')

    def getAdminConfig(self):
        config = manage_config.read_config_file()
        return config.get('General', 'admin_tab')

    def getDocumentationConfig(self):
        config = manage_config.read_config_file()
        return config.get('General', 'documentation_tab')

    def getDefaultTabConfig(self):
        config = manage_config.read_config_file()
        return config.get('General', 'default_tab')

    def getSystemVersion(self):
        """ Return system version.
        Returns:
            str: system version
        """
        global sysVersion
        global rcpl_version
        global os_type
        with open('/etc/os-release') as os:
            release = {}
            for line in os:
                k, v = line.rstrip().split('=')
                release[k] = v.strip('"')
        if release['ID'] == 'wrlinux':
            version = release['VERSION'].split('.')
            rcpl_version = int(version[3])
        os_type = release['ID']
        sysVersion = release['VERSION']
        return sysVersion


    def getCPUType(self):
        """ Return cpu arch.
        Returns:
            str: cpu arch
        """
        global arch
        global display_arch
        if arch == "Not Set":
            self.__log_helper.logger.debug('Setting Arch')
            command = '''rpm -q --queryformat %{ARCH} bash'''
            arch = shell_ops.run_command(command)
            if arch == 'corei7_64':
                arch = "baytrail"
            elif arch == 'quark':
                arch = "quark"
            else:
                arch = "haswell"
        cpu_name = shell_ops.run_cmd_chk("cat /proc/cpuinfo | grep 'model name' | uniq")
        display_arch = cpu_name['cmd_output'].split(':')[1]
        return display_arch

    def getDiskUsage(self, path):
        """ Return disk usage statistics about the given path.
        Args:
            path (str): the target path to get usage info for.
        Returns:
            dict: keys are 'total', 'used' and 'free', which are the amount of total, used and free space, in bytes.
        """
        st = os.statvfs(path)
        self.__free = (st.f_bavail * st.f_frsize)/1000000000.0
        self.__total = (st.f_blocks * st.f_frsize)/1000000000.0
        self.__used = ((st.f_blocks - st.f_bfree) * st.f_frsize)/1000000000.0
        self.__disk_usage['total'] = '%.1f' % round(self.__total, 1)
        self.__disk_usage['used'] = '%.1f' % round(self.__used, 1)
        self.__disk_usage['free'] = '%.1f' % round(self.__free, 1)
        return self.__disk_usage

    def getMcafeeStatus(self):
        """ Return status of MEC service
        Returns:
            active / inactive
        """
        global os_type
        if os_type == 'wrlinux':
            chk_out = shell_ops.run_cmd_chk('systemctl is-active scsrvc.service')
            if chk_out['returncode']:
                result = 'Inactive'
            else:
                result = 'Active'
        else:
            result = ""
        return result

    def getDataSet(self):
        """ Return system info data.
        Returns:
            dict: keys are 'host_name', 'model', 'time', 'uptime', 'netinterface', 'ssid', 'disk', 'system_version'
        """
        self.__data_set['host_name'] = self.getHostname()
        self.__data_set['model'] = self.getCPUType()
        self.__data_set['time'] = self.getDateTime()
        self.__data_set['uptime'] = self.getUpTime()
        self.__data_set['netinterface'] = self.getLanIPAddr()
        self.__data_set['ssid'] = self.getWifiSSID()
        self.__data_set['disk'] = self.getDiskUsage('/')
        self.__data_set['system_version'] = self.getSystemVersion()
        self.__data_set['devhub_version'] = self.getDevHubVersion()
        self.__data_set['mcAfee_status'] = self.getMcafeeStatus()
        self.__data_set['platform'] = self.getPlatform()
        self.__data_set['sensor_config'] = self.getSensorConfig()
        self.__data_set['softsoc_config'] = self.getSoftSOCConfig()
        self.__data_set['ref_sw_config'] = self.getRefSWConfig()
        self.__data_set['package_config'] = self.getPackageConfig()
        self.__data_set['admin_config'] = self.getAdminConfig()
        self.__data_set['documentation_config'] = self.getDocumentationConfig()
        self.__data_set['default_tab'] = self.getDefaultTabConfig()
        return self.__data_set

    def platform_details(self):
        """ Return platform architecture and rcpl version.
        Returns:
            tuple: 1st is str of platform architecture. 2nd is str of rcpl version.
        """
        global rcpl_version
        architecture = platform.machine()
        if rcpl_version == 'Not Set':
            self.getSystemVersion()
        rcpl = 'rcpl' + str(rcpl_version)
        return architecture, rcpl
        
    def getDevHubVersion(self):
        devhub_version = shell_ops.run_command('rpm -q --queryformat %{version}-%{release} iot-developer-hub')
        return devhub_version

    def getTargetAccounts(self):
        # https://docs.python.org/2/library/pwd.html
        # useradd and  /etc/login.defs to define UID range
        account_list = []
        for p in pwd.getpwall():
            # grp.getgrgid(p[3])[0] can show group name
            if p[0] == 'root':
                account_list.append(p[0])
            elif p[0] == 'wra':
                account_list.append(p[0])
            elif 65534 > p[2] >= 1000:
                # useradd command will add user account with UID starting from 1000 based on /etc/login.defs
                account_list.append(p[0])
            else:
                pass
        return account_list
