# Copyright (c) 2016, Intel Corporation. All rights reserved.
# This file is licensed under the GPLv2 license.
# For the full content of this license, see the LICENSE.txt
# file at the top level of this source tree.

from manage_auth import require
from server import shutdown_http_server
import subprocess
import json
import ast
import os
from cgi import escape
import cherrypy
from tools import logging_helper, sysinfo_ops
import manage_config
import manage_package
import manage_worker


@require() 
class SecurityAutomation(object):
    exposed = True

    def PUT(self, **kwargs):
        retrieving_work, worker_result = manage_worker.do_work(manage_worker.worker_process_message_type_toggle_https,
                                                               kwargs)
        try:
            if retrieving_work:
                if worker_result['status'] == 'success':
                    # {u'status': u'success',
                    #  u'message': '',
                    #  u'in_progress': False,
                    #  u'work_type': ''}
                    # move the key work result to the 1st dictionary item

                    # restart Dev Hub server on success
                    shutdown_http_server()

        except Exception as e:
            worker_result['status'] = 'failure'
            worker_result['message'] = str(e)
        return json.dumps(worker_result)
