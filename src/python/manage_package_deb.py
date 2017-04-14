#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2016, Intel Corporation. All rights reserved.
# This file is licensed under the GPLv2 license.
# For the full content of this license, see the LICENSE.txt
# file at the top level of this source tree.

import os
import codecs
import json
import rpm
import subprocess
import ast
from tools import logging_helper, data_ops, shell_ops, sysinfo_ops, network_ops
import manage_config
import manage_package
import manage_repo
import manage_worker
from manage_auth import require

# global variables used across multiple modules
constructed_packages_list = []  # only used by unit_test

def update_package_list():
    """ Grabs the curated.tar.gz file from download.01.org to update the curated package listings

    Returns:
        str: Json response with key 'status' and value 'success' or 'fail
    """
    log_helper = logging_helper.logging_helper.Logger()
    data_collector = sysinfo_ops.DataCollect()

    # Determine architecture and proper repository
    config = manage_config.read_config_file()
    base_url = config.get('DefaultRepo', 'base_repo')
    curated_url = base_url + '/' + 'curated.xml.gz'
    local_path = '/tmp/curated.xml.gz'
    local_file = 'curated.txt'

    # Download and decompress the curated list
    # todo: this needs to return 'False' on timeout and give a json status of 'fail'
    shell_ops.run_command('timeout 5 wget %s -O %s' % (curated_url, local_path))
    data_ops.uncompress(local_path, local_file)

    build_package_database()

    # Remove tar file after use
    try:
        os.remove(local_path)
    except:  # todo: This needs to throw an error. Try 'except (OSError, IOError):'
        pass

    # From the UI if json == null then the response failed (timed out)
    response = ({
        'status': 'success'
    })
    response = json.dumps(response)
    log_helper.logger.debug("Finished updating package list: '%s'" % response)
    return response

def get_installed_packages_deb():
    """ Get a list of the installed packages from rpm module

    Returns:
        tuple: 1st is list of installed package names. 2nd is dict.
    """
    dict_installed_packages = {}
    installed_packages = []
    log_helper = logging_helper.logging_helper.Logger()

    cmd = 'dpkg -l'
    result = shell_ops.run_cmd_chk(cmd)

    list_packages = result['cmd_output'].split("\n")
    for item in list_packages:
        if 'ii' in item:
            x = item.split(" ")
            y = []
            for element in x:
                if len(element) > 0:
                    y.append(element)
            installed_packages.append(y[1])
            dict_installed_packages[y[1]] = y[2]

    return installed_packages, dict_installed_packages

def build_package_database():
    """ Parses curated and non-curated packages and places them into a json format.

    The requirements of using this is to make sure that smart update is called to update cache,
    when add/remove repo is done.

    The json formatted string is saved to a file.
    """

    import apt

    global constructed_packages_list_new
    constructed_packages_list_new = []
    data = []
    curated_packages = []
    curated_dict = {}
    pkg_dict = []
    
    log_helper = logging_helper.logging_helper.Logger()
    log_helper.logger.debug("Starting Build...")

    # -------------------------------------------------
    # ------------- Step 1: Gather info ---------------
    # -------------------------------------------------

    # Get the latest installed packages list
    my_list, my_dict = get_installed_packages_deb()

    # Get the info for curated packages
    try:
        file_path = os.path.dirname(os.path.realpath(__file__))
        my_file = codecs.open(file_path + '/' + 'curated.txt', 'r')
        curated_packages = json.loads(my_file.read())  # list of json
        my_file.close()
    except Exception as e:
        log_helper.logger.error('Read curated.txt failed with ' + str(e))

    # Create a list of dict for curated packages, this can be used later..... dict key checking is
    # more efficient (due to hash table) than linear loop search
    for pc in curated_packages:
        try:
            curated_dict[pc['name']] = {'image': pc['image'], 'title': pc['title'],
                                        'summary': pc['summary'], 'url': pc['url'],
                                        'description': pc['description'], 'vertical': pc['vertical'],
                                        'service': pc['service'], 'launch': pc['launch'], 'curated': True,
                                        'group' : 'devel'}
        except Exception as e:
            log_helper.logger.error(str(e) + ' for ' + pc['name'])
            continue


    # -----------------------------------------------------------------
    # ----------- Step 2: Check for Install and upgrades --------------
    # -----------------------------------------------------------------

    # Check if package is Installed and update the dictonary
    for key in curated_dict.iterkeys():
        if key in my_list:
            curated_dict[key]['installed'] = True
            curated_dict[key]['version'] = my_dict[key]
        else:
            curated_dict[key]['installed'] = False
            curated_dict[key]['version'] = ''

    # Connect to apt Cache
    aptCache = apt.Cache()
    aptCache.open()

    for key in curated_dict:
        try:
            pkg = {}
            select_package = aptCache[key]
            pkg = curated_dict[key]
            pkg['name'] = key
            pkg['upgrade_ver'] = ''
            if curated_dict[key]['version']:
                if select_package.versions[0].version == curated_dict[key]['version']:
                    print 'version same'
                else:
                    pkg['upgrade_ver'] = select_package.versions[0].version
            pkg_dict.append(pkg)
        except:
            if key in my_list:
                pkg = curated_dict[key]
                pkg['name'] = key
                pkg_dict.append(pkg)
            continue

    # -------------------------------------------------------------
    # ------------------ Step 3: Store Update ---------------------
    # -------------------------------------------------------------

    constructed_packages_list_new = data

    # Output file with list of curated packages with additional info added
    with open(manage_config.package_data_file, 'w') as my_file:
        my_file.write(json.dumps(pkg_dict))
    log_helper.logger.debug("Finished building package database. Output written to " + manage_config.package_data_file)

    with open(manage_config.package_installed_data_file, 'w') as my_file:
        my_file.write(json.dumps(my_dict))
    log_helper.logger.debug(
        "Finished building package database. Output written to " + manage_config.package_installed_data_file)

def parse_package_installation_result(pkg_name, result_dict):
    """ Parse the result of Smart's package installation
    Args:
        pkg_name (str): package name
        result_dict (dict): the result of using shell_ops.run_cmd_chk to run smart package install.

    Returns:
        dict: dict of the result. The key is 'status'. If the 'status' is not 'success', then an extra key 'error'
              describes the error message.

    """
    response = ({'status': "success", 'error': ''})

    if ('returncode' in result_dict) and ('cmd_output' in result_dict):
        if result_dict['returncode']:
            if "E:" in result_dict['cmd_output']:
                # User clicked install/uninstall/upgrade then refreshed and page and hit it again
                if "Unable to locate package" in result_dict['cmd_output']:
                    error = "The package '" + pkg_name + "' could not be found in any repositories that have been added. Please check your network configuration and repositories list on the Administration page."
                    status = "failure"
                else:
                    error = "For " + pkg_name + ", "
                    error += result_dict['cmd_output'][result_dict['cmd_output'].index("error:") + 7:].replace("\n", "")
                    status = "failure"
                response = ({
                    'status': status,
                    'error': error
                })

    return response

def package_transaction(command_type, package):
    """ Package management: handle smart calls

    Args:
        command_type (str): String 'install', 'remove', 'upgrade
        package (dict): String name of rpm package

    Returns:
        str: In string format, Json array with 'status' and 'error'
    """
    log_helper = logging_helper.logging_helper.Logger()


    import apt
    response = {'status': 'success', 'message': '', 'p_list': []}

    # Halt unauthorized commands
    if command_type != "install" and command_type != "remove" \
            and command_type != "upgrade":
        return

    # Connect to apt Cache
    aptCache = apt.Cache()
    aptCache.open()
    tgt_pkg = package['package']
    if tgt_pkg == "all":
        aptCache.upgrade()
    else:
        pkg = aptCache[tgt_pkg]
        if command_type == "install":
            pkg.mark_install()
        elif command_type == "upgrade":
            pkg.mark_upgrade()
        elif command_type == "remove":
            pkg.mark_remove()

    try:
        aptCache.commit()
    except Exception, arg:
        response['message'] = str(arg)
        response['status'] = 'fail'

    if response['status'] == 'success':
        # package list is updated. Recreate package database
        build_package_database()
        response['p_list'] = manage_package.get_data()

    log_helper.logger.debug('Return from package_transaction')
    return json.dumps(response)
