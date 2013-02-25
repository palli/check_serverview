#!/usr/bin/env python
# Author       : Stijn Gruwier <stijn.gruwier@notforadsgmail.com>
# Description  : Utils for creating nagios plugins with python
# $Id: schau_utils.py,v 1.2 2007/10/09 07:05:11 sg Exp $
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

import sys
from optparse import OptionParser

class NagiosPlugin(object):
    def __init__(self, label, plugin_method, extra_options, help):
        self.NAGIOS_RET_CODES = {
            'OK':0,
            'WARNING':1,
            'CRITICAL':2,
            'UNKNOWN':3}
        #help (h) and version (V) are also standard/reserved options
        self.standard_options = {
            'warning' : {'char':'w', 'type':'string'},
            'critical' : {'char':'c', 'type':'string'},
            'timeout' : {'char':'t', 'type':'int', 'default':25},
            'verbose' : {'char':'v', 'type':'int', 'default':0}}
        self.label = label
        self.plugin_method = plugin_method
        self.help = help
        self.extra_options = extra_options
        # warn and exit if an extra_option is already a standard option
        self._test_options()
        self.optparser = OptionParser(add_help_option=0)
        self._add_help_options()
        self._add_options(self.standard_options)
        self._add_options(self.extra_options)

    def run(self, debug = False):
        options_dict = {}
        (options_object, args) = self.optparser.parse_args()
        for opt in self.standard_options.keys() + self.extra_options.keys():
            if hasattr(options_object, opt):
                options_dict[opt] = getattr(options_object, opt)
        # Call plugin method specified by the user of this class
        try:
            retvals = self.plugin_method(options_dict)
            if len(retvals) == 3:
                status, msg, function = retvals
            elif len(retvals) == 2:
                status, msg = retvals
                function = ''
            else:
                raise '''plugin method returns too many/not enough vars'''
        except:
            if debug:
                raise
            else:
                status = 'UNKNOWN'
                msg = 'Unhandled exception in plugin %s' % self.help['filename']
                function = 'PYNAGLIB'
        self._NAGIOS_EXIT(status,msg,function)

    def _test_options(self):
        #help (h) and version (V) are also standard/reserved options
        for opt_extra in self.extra_options:
            opt_extra_char = self.extra_options[opt_extra]['char']
            for opt_standard in self.standard_options:
                opt_standard_char = self.standard_options[opt_standard]['char']
                if ( opt_standard_char == opt_extra_char) \
                or (opt_extra_char in ('h','V')) \
                or (opt_extra == opt_standard) \
                or (opt_extra in ('help','version')):
                    status = 'UNKNOWN'
                    msg = '"-%s|--%s" is a reserved option' % (opt_extra_char, 
                                                          opt_extra) 
                    function = 'PYNAGLIB'
                    self._NAGIOS_EXIT(status,msg,function)

    def _add_options(self, options):
        for option_name in options:
            opt = options[option_name]
            if opt.has_key('default'):
                self.optparser.add_option(
                '-' + opt['char'],
				'--' + option_name, action='store',
				type=opt['type'],
				dest=option_name,
				default=opt['default'] )
            else:
				self.optparser.add_option(
				'-' + opt['char'],
				'--' + option_name,
				action='store',
				type=opt['type'],
				dest=option_name )	
		
    def _add_help_options(self):
        self.optparser.add_option("-h", "--help", action="callback",
            callback=self._help_func)
        self.optparser.add_option("-V", "--version", action="callback",
            callback=self._ver_func)

    def _help_func(self, option, opt, value, parser):
        full_help = '%s %s\n\n%s\n\n%s\n\n%s\n\n%s\n\n%s' % \
        (self.help['filename'], self.help['version'], self.help['preamble'],
        self.help['use'], self.help['options'], self.help['bugs'],
        self.help['disclaimer'])
        print full_help
        sys.exit(self.NAGIOS_RET_CODES['UNKNOWN'])

    def _ver_func(self, option, opt, value, parser):
        print self.help['filename'] +' '+ self.help['version']
        sys.exit(self.NAGIOS_RET_CODES['UNKNOWN'])

    def _NAGIOS_EXIT(self, status, msg, function=''):
        status = status.upper()
        if not status in self.NAGIOS_RET_CODES:
            status = 'UNKNOWN'
        if function:
            print '%s %s - %s' % (function, status, msg)
        else:
            print '%s %s - %s' % (self.label, status, msg)
        sys.exit(self.NAGIOS_RET_CODES[status])
	

if  __name__ == '__main__':
    ##################################################################
    ##
    ### Example python nagios plugin using the NagiosPlugin class
    ##  steps:
    ##
    ##   1) define a help dictionary
    ##   2) define the options (parameters) your plugin will accept
    ##   3) define your plugin function
    ##   4) create a NagiosPlugin object using the stuff defined before
    ##   5) run the NagiosPlugin object
    ##
    ##   - you can modify the example help dictionary below
    ##   - a plugin function has the following interface:
    ##       * it accepts one argument, a dictionary containing all the
    ##         options specified on the commandline and their values
    ##       * it returns a list of 2 (optionally 3) values
    ##          a) the status, one of "OK", "UNKNOWN", "CRITICAL", "WARNING"
    ##          b) an output string (shouldn't contain a newline)
    ##        [ c) a label to replace the default plugin name ]
    ##
    ##
    ##
    ##    
    help = {
    # filename of the plugin
    'filename':
    '''check_pluginname''',
    
    # version
    'version':
    '''0.1''',
    
    # disclaimer, license, legal mumbo jumbo
    'disclaimer' : 
    '''This nagios plugin comes with ABSOLUTELY NO WARRANTY.  You may redistribute
    copies of the plugins under the terms of the GNU General Public License.
    Copyright (c) 2006 Gruwier Stijn''',
    
    # Summary
    'preamble' :
    '''This plugin does this and that.''',
    
    # Commandline usage
    'use' :
    '''Usage:	check_pluginname [-w limit] [-c limit] [-v verbose] [-t timeout]
                check_pluginname (-h|--help)
                check_pluginname (-V|--version)''', 
    
    # Description of every option
    'options' :
    '''check_pluginname
     -w, --warning=WARNINGLEVEL
        Exit with WARNING status if a variable matches WARNINGLEVEL
     -c, --critical=CRITICALLEVEL
        Exit with CRITICAL status if a variable matches CRITICALLEVEL
     -t, --timeout=SECONDS
        Seconds before plugin times out (default: 10)
     -v, --verbose=[0-]
        Set the amount of output
     -h, --help
        Print help 
     -V, --version
        Print version information''',
    
    # Known problems
    'bugs' :
    '''Bugs:	Didn't test X. Y might be broken because of Z''' }

    opties = { 'optie1' : {'char': 'o', 'type':'string'},
               'optie2' : {'char': 'T', 'type':'string','default':'test'}}

    def plugin_function(options):
        # in a real plugin this value would be obtained from somewhere
        # (not fixed)
        pressure = 100
        if testvalue > options['warning']:
            return ('WARNING', 'pressure %s' % pressure)
        elif testvalue > options['critical']:
            return ('CRITICAL', 'pressure %s' % pressure)
        else:
            return ('OK', 'pressure %s' % pressure)

    plug = NagiosPlugin('NIEUWPLUG', plugin_function, opties, help)
    plug.run()
