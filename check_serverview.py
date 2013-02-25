#! /bin/env python
# Author       : Stijn Gruwier <stijn.gruwier@notforadsgmail.com>
# Description  : Gets FSC ServerView (hardware) alerts through SNMP 
# $Id: check_serverview.py,v 1.8 2008/04/10 08:06:30 sg Exp $
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from schau_utils import NagiosPlugin
from schau_snmp import SnmpClient, SnmpError

###################################################
###   Definitions for building a NagiosPlugin   ###
###################################################


opties = {
    'host' : {'char': 'H', 'type':'string'},
    'protocol' : {'char': 'p', 'type':'int', 'default':1},
    'community' : {'char': 'C', 'type':'string', 'default':'public'},
    'ignore' : {'char': 'i', 'type':'string', 'default':''}
    }

help = {
# filename of the plugin
'filename':
'''check_serverview.py''',

# version
'version':
'''$Revision: 1.8 $''',

# disclaimer, license, legal mumbo jumbo
'disclaimer' : 
'''This nagios plugin comes with ABSOLUTELY NO WARRANTY.  You may redistribute
copies of the plugins under the terms of the GNU General Public License.
Copyright (c) 2007 Gruwier Stijn''',

# Summary
'preamble' :
'''This plugin checks all fsc serverview (hardware) subsystems, returns global status''',

# Commandline usage
'use' :
'''Usage:	check_serverview.py -H host [-C community] [-p protocol]
		[-i|--ignore=subsystem1[,subsystem2[,...]]]
	check_serverview.py (-h|--help)
	check_serverview.py (-V|--version)''', 

# Description of every option
'options' :
'''check_serverview.py
 -H, --host=hostname
    Connect to hostname
 -p, --protocol=[1|2|3]
    Snmp version to use (default 1)
    Affects the community option
 -C, --community=COMMUNITY
    community string with SNMPv1/v2 OR <user>:<password> with SNMPv3
    Default: public
 -i, --ignore=SUBSYSTEM1,SUBSYSTEM2,SUBSYSTEM3
    list of subsystem names to ignore
    comma separated(do not use spaces!)
    Added this feature because I don't care about the deployment subsystem
 -w, --warning=WARNINGLEVEL
    Exit with WARNING status if a variable matches WARNINGLEVEL
    not implemented
 -c, --critical=CRITICALLEVEL
    Exit with CRITICAL status if a variable matches CRITICAL
    not implemented
 -t, --timeout=SECONDS
    seconds before plugin times out (default: 25)
    not implemented
 -v, --verbose=[0-]
    Set the amount of output
    not implemented
 -h, --help
    Print help 
 -V, --version
    Print version information''',

# Known problems
'bugs' :
'''Bugs:	Let me know - stijn.gruwier@gmailnotforads.com
        *remove the 'notforads' substring from the address*''' }

def serverview_function(options):
    # TODO: more option checks
    ignorelist = []
    host = options['host']
    community = options['community']
    protocol = int(options['protocol'])
    timeout = options['timeout']
    ignore = options['ignore']
    if not host:
        return('UNKNOWN', '-H, --host is a required argument')
    if not community:
        return('UNKNOWN', '-C, --community is a required argument')
    if not protocol in (1,2,3):
        return('UNKNOWN', 'invalid protocol')
    if ignore:
        ignorelist = ignore.lower().split(',')
    if protocol in (1,2):
        snmp = SnmpClient(host, protocol, community)
    else:
        user, key = community.split(':')
        snmp = SnmpClient(host, protocol, community=community)
    problem_list = []
    problem_string, subsystems_string = '', ''
    try:
        subsystems_string, problem_list = get_problem_list(snmp, ignorelist) 
    except SnmpError:
        return('CRITICAL', 'network or snmp related problem - NOT a hardware problem')
    for problem in problem_list:
        name, status, last_error = problem
        problem_string = problem_string + '%s: %s%s - ' % (name,status,last_error)    
    problem_string = problem_string.strip('- ')
    if problem_list:
        return('CRITICAL', problem_string)
    else:
        return('OK', 'All subsystems are good: %s' % subsystems_string)

def get_problem_list(snmp_client, ignorelist):
    '''Returns a string with subsystem names, and a list of failed ones '''
    OID_SUBSYSTEM_NAMES = '.1.3.6.1.4.1.231.2.10.2.11.2.3.0'
    OID_GLOBAL_STATUS = '.1.3.6.1.4.1.231.2.10.2.11.2.1.0'
    OID_SUBSYSTEM_COUNT = '.1.3.6.1.4.1.231.2.10.2.11.3.2.0'
    OID_SUBSYSTEM_STATUS = '.1.3.6.1.4.1.231.2.10.2.11.3.1.1.3.%s'
    OID_SUBSYSTEM_NAME = '.1.3.6.1.4.1.231.2.10.2.11.3.1.1.2.%s'
    OID_SUBSYSTEM_LAST_ERROR = '.1.3.6.1.4.1.231.2.10.2.11.3.1.1.4.%s'
    STATUS_NR2STRING = {1:'ok',2:'degraded',3:'error',4:'failed',5:'unknown-init'}
    problem_list = []
    subsystems, global_status, subsys_status, subsys_name, subsys_last_error = '',0,0,'',''
    subsystems = str(snmp_client.get(OID_SUBSYSTEM_NAMES)).lower()
    for subsys_ignore in ignorelist:
        subsystems = subsystems.replace(subsys_ignore, '') 
    # create comma separated string
    subsystems = ','.join(subsystems.split())
    global_status = int(snmp_client.get(OID_GLOBAL_STATUS))
    if global_status == 1:
        # if global status is ok, no need to do further checks
        # NOTE: I tested this and global status was inconsistent with subsystem
        #       statusses: global was ok, deployment subsys was unknown
        return (subsystems, problem_list)
    counter = int(snmp_client.get(OID_SUBSYSTEM_COUNT))
    for index in range (1, counter+1):
        index_str = str(index)
        subsys_status = int(snmp_client.get(OID_SUBSYSTEM_STATUS % index_str))
        if subsys_status != 1:
            try:
                subsys_status = STATUS_NR2STRING[subsys_status]
            except:
                subsys_status = 'outofrange' 
            subsys_name = str(snmp_client.get(OID_SUBSYSTEM_NAME % index_str))
            if subsys_name.lower() in ignorelist:
                continue
            subsys_last_error = str(snmp_client.get(OID_SUBSYSTEM_LAST_ERROR % index_str))
            if subsys_last_error == '<<not supported>>':
                subsys_last_error = ''
            else:
                subsys_last_error = ',%s' % subsys_last_error
            problem_list.append((subsys_name,subsys_status,subsys_last_error))
    return (subsystems, problem_list)

if __name__ == '__main__':
    plug = NagiosPlugin('SERVERVIEW', serverview_function, opties, help)
    plug.run(debug=True)
