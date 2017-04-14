#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2016, Intel Corporation. All rights reserved.
# This file is licensed under the GPLv2 license.
# For the full content of this license, see the LICENSE.txt
# file at the top level of this source tree.

import cherrypy
import json
import manage_config
import os
import shutil
from manage_auth import require
from tools import shell_ops, logging_helper, sysinfo_ops

class TUTORIALS(object):
    def __init__(self):
        self.__log_helper = logging_helper.logging_helper.Logger()
        self.__file = 'tutorials.json'
        self.__tutorials = {}

    def get(self, update):
        """

        Args:
            update (bool): True if update requested

        Returns:

        """
        if update == 'True':
            self.update()
        self.read()
        return self.__tutorials

    def read(self):
        with open(self.__file) as json_data:
            self.__tutorials = json.load(json_data)

    def update(self):
        # Determine proper repository
        local_path = '/tmp/tutorials.json'
        file_path = os.path.dirname(os.path.realpath(__file__)) + '/' + 'tutorials.json'
        bk_file = os.path.dirname(os.path.realpath(__file__)) + '/' + 'tutorials.json.bk'
        config = manage_config.read_config_file()
        base_url = config.get('DefaultRepo', 'base_repo')
        data_collector = sysinfo_ops.DataCollect()
        if sysinfo_ops.os_type == 'wrlinux':
            architecture, rcpl = data_collector.platform_details()
            base_url = base_url + '/' + rcpl + '/' + architecture
        tutorial_url = base_url + '/' + 'tutorials.json'

        # Download and decompress the curated list
        # todo: this needs to return 'False' on timeout and give a json status of 'fail'
        result = shell_ops.run_cmd_chk('timeout 5 wget %s -O %s' % (tutorial_url, local_path))
        if result['returncode'] == 0:
            os.rename(file_path, bk_file)
            shutil.copy(local_path, file_path)


    def get_config_file(self,request_loc):
        file_path = "/var/www/www-repo-gui/config/{}.config.json".format(request_loc);
        result = None

        if os.path.isfile(file_path):
            with open(file_path) as data_file:
                result = {'result_code': 0, 'data': json.load(data_file)}
        else:
            result = {'result_code': 1, 'data': "File not found"}

        return result
        
    
@require()
class Tutorials(object):
    exposed = True

    def GET(self, **kwargs):
        t = TUTORIALS()
        tut = t.get_config_file(kwargs['conf'])
        return json.dumps(tut)


