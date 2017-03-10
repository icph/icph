#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2016, Intel Corporation. All rights reserved.
# This file is licensed under the GPLv2 license.
# For the full content of this license, see the LICENSE.txt
# file at the top level of this source tree.


from tools import logging_helper
from manage_auth import require
import json
import os
import manage_config
import manage_repo
import manage_package
from tools import shell_ops, logging_helper, sysinfo_ops

class FPGA(object):
    def __init__(self):
        """

        Args:
            TODO

        Returns:

        """
        #self.__log_helper = logging_helper.logging_helper.Logger()
        self.__error = None
        self.__bs_list = []
        self.__bs_list_desc = []
        self.__bs_local = dict()
        self.__bs_local_desc = dict()
        self.__bs_online = dict()
        self.__bs_online_desc = dict()
        self.__install_list = []
        self.__fpga_options = []

        # File locations
        self.__installed_file = "/tmp/json_packages_installed.txt"
        self.__config = manage_config.read_config_file()
        self.__deploy_folder = "/opt/intel/fpga_deploy/"
        self.__bitstream_folder = "/opt/intel/fpga_examples/"

    def fpga_list(self, network):
        """ Build table of available bitstreams

               Args:

               Returns:

        """
        # check if file exists and read bitstream.json to dict
        bs_file = self.__bitstream_folder + "bitstreams.json"
        bs_local = False
        if os.path.isfile(bs_file):
            with open(bs_file) as js:
                self.__bs_local = json.load(js)
            bs_local = True

        bs_online = False
        if network == 'True':
            # check for online bitstream file
            base_url = self.__config.get('DefaultRepo', 'base_repo')
            data_collector = sysinfo_ops.DataCollect()
            if sysinfo_ops.os_type == 'wrlinux':
                architecture, rcpl = data_collector.platform_details()
                base_url = base_url + '/' + rcpl + '/' + architecture
            bitstream_url = base_url + '/' + 'bitstreams.json'

            # Download and read online bitstreams.json
            local_path = '/tmp/bitstreams.json'
            result = shell_ops.run_cmd_chk('timeout 5 wget %s -O %s' % (bitstream_url, local_path))
            if result['returncode'] == 0:
                with open(local_path) as js:
                    self.__bs_online = json.load(js)
                bs_online = True
        if bs_online is False and bs_local is True:
            self.__bs_list = self.__bs_local['bitstreams']
            self.__bs_list_desc = self.__bs_local['descriptions']
        elif bs_online is True and bs_local is False:
            self.__bs_list = self.__bs_online['bitstreams']
            self.__bs_list_desc = self.__bs_online['descriptions']
        elif bs_online is True and bs_local is True:
            p = []
            # Build list of available Bitstreams
            for item in self.__bs_online['bitstreams']:
                self.__bs_list.append(item)
                for key, value in item.iteritems():
                    if key == 'name':
                        p.append(value)
            for item in self.__bs_local['bitstreams']:
                for key, value in item.iteritems():
                    if key == 'name':
                        if value not in p:
                            self.__bs_list.append(item)

            # Build list of Descriptions
            d = []
            for item in self.__bs_online['descriptions']:
                self.__bs_list_desc.append(item)
                for key, value in item.iteritems():
                    d.append(key)
            for item in self.__bs_local['descriptions']:
                for key, value in item.iteritems():
                    if key not in d:
                        self.__bs_list_desc.append(item)

        # Generate FPGA Options from json list.
        key_list = {key for data in self.__bs_list for key in data.keys()}
        for key in key_list:
            if key != "name" and key != "Hash" and key != "title":
                self.__fpga_options.append(key.replace("'", ""))


        # Check for installed bitstreams. Compare package install list and available bitstreams
        if network == 'True':
            if os.path.isfile(self.__installed_file):
                with open(self.__installed_file) as js:
                    il = json.load(js)
                for key, value in il.iteritems():
                    self.__install_list.append(key)
        else:
            # Build Installed list
            self.__install_list, _ = manage_package.get_installed_packages_new()

        for I in self.__bs_list:
            for key, value in I.iteritems():
                if key == 'name':
                    if value in self.__install_list:
                        installed = True
                    else:
                        installed = False
            I['installed'] = installed


        # Return dataset
        return self.__fpga_options, self.__bs_list, self.__bs_list_desc


@require()
class SoftSoc(object):
    exposed = True

    def GET(self, **kwargs):
        c = FPGA()
        options, bitstreams, list_desc = c.fpga_list(kwargs['update'])
        return json.dumps([options, bitstreams, list_desc])