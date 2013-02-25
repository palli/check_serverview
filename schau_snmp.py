#! /bin/env python
# Author       : Stijn Gruwier <stijn.gruwier@notforadsgmail.com>
# Description  : Provides easier access to snmp for nagios
# $Id: schau_snmp.py,v 1.3 2007/10/09 07:05:11 sg Exp $
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

''' REQUIRED PACKAGES:
 --------------------
* PyCrypto
    http://pycrypto.sourceforge.net
    On CentOS with apt:
    apt-get install python-crypto
* PyASN1
    http://pyasn1.sourceforge.net
      wget http://heanet.dl.sourceforge.net/sourceforge/pyasn1/pyasn1-0.0.6a.tar.gz
      tar -xzf pyasn1-0.0.6a.tar.gz
      cd pyasn1-0.0.6a
      python setup install
* pysnmp v4.1 (with snmpv3 support)
    http://pysnmp.sourceforge.net
      wget http://heanet.dl.sourceforge.net/sourceforge/pysnmp/pysnmp-4.1.7a.tar.gz
      tar -xzf pysnmp-4.1.7a.tar.gz
      cd pysnmp-4.1.7a
      python setup install
 '''
 
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi.error import NoSuchObjectError
from pyasn1.error import PyAsn1Error
# ASN.1 library, used for manipulating SNMP numbers
from pyasn1.type.univ import ObjectIdentifier, Null


class SnmpError(Exception):
    def __init__(self, value=''):
        self.value = value
    def __str__(self):
        return repr(self.value)

class SnmpNoInstanceError(SnmpError):
    pass

class SnmpBadArgumentError(SnmpError):
    pass


class SnmpClient(object):
    '''Simple Snmpv1/2/3 Client class

    Required arguments
        * host:         string  - snmp agent hostname
        * protocol:     integer - snmp protocol version 1,2 or 3
    Arguments that might be required depending on the protocol version:
        * community:    string  - snmpv1 community string
        * secname       string  - snmpv1 security name
                                  
        * user:         string  - snmpv3 security user, default None
        * authkey:      string  - snmpv3 authentication key, default None
        * authProtocol: string  - snmpv3 authentication protocol 
                                  can be 'md5' or 'sha', default 'md5'
        * privkey:      string  - snmpv3 encrytion key, default None
    Other arguments:
        * port          integer - default 163
    The privacy protocol used is DES (only protocol implemented)

    Supplied methods
        * get
        * get_table
    
    SNMPv1 example:
       s = SnmpClient('netappa1', 1, community='password')
    SNMPv3 authNoPriv example:
       s = SnmpClient('jay1', 3, user='snmpuser', authkey='password')
       s.get('1.3.6.1.2.1.1.1.0')'''

    def __init__(self, host, protocol,community=None, secname='test-agent',
                user=None, authkey=None, privkey=None, timeout=None, port=161,
                authProtocol='md5'):
        errortext = self._validate_input(host, protocol, community, secname,
                    user, authkey, privkey,timeout, port, authProtocol)
        if errortext:
            raise SnmpBadArgumentError(errortext)
        # for oid conversions
        self.oid_converter = ObjectIdentifier()
        self.protocol = protocol
        self.timeout = timeout
        self.target = cmdgen.UdpTransportTarget((host, port))
        if protocol is 1:
            self.authentication = cmdgen.CommunityData(secname, community, 0)
        elif protocol is 2:
            self.authentication = cmdgen.CommunityData(secname, community)
        elif protocol is 3:
            if privkey:
                privprot = cmdgen.usmD
            else:
                privprot = cmdgen.usmNoPrivProtocol
            if authkey:
                if authProtocol == 'md5':
                    authprot = cmdgen.usmHMACMD5AuthProtocol
                else:
                    authprot = cmdgen.usmHMACSHAAuthProtocol
            else:
                authprot = cmdgen.usmNoAuthProtocol
            if privkey:
                privprot = cmdgen.usmDESPrivProtocol
            else:
                privprot = cmdgen.usmNoPrivProtocol
            self.authentication = cmdgen.UsmUserData(user, authkey, privkey,
                                                    authprot, privprot)
        self.snmpclient = cmdgen.CommandGenerator()

    def _validate_input(self, host,protocol, community, secname, user, authkey,
                        privkey, timeout, port, authProtocol):
        '''Validates arguments, returns False if valid, else error message'''
        if not protocol in (1,2,3):
            return 'unknown protocol version'
        if not type(port) is int:
            return 'port must be an integer'
        if (port < 0) or (port >= 2**16):
            return 'port must be >= 0 and < 2^16'
        if protocol in (1,2):
            if not community:
                return 'community is a required argument for snmpv1/2'
        if protocol is 3:
           if not user:
               return 'user is a required argument for snmpv3'
           if authkey:
               if not authProtocol in ('md5', 'sha'):
                   return 'unknown authentication protocol'
        return False

    def get(self, oid, bulk=False):
        '''Get the value for the oid, raises SnmpError
        
        Return value is always a string'''
        # Dotted string -> tuple of numerics OID conversion
        try:
            oid = self.oid_converter.prettyIn(oid)
        except PyAsn1Error:
            raise SnmpBadArgumentError('Invalid OID format')
        try:
            if bulk:
                result = self.snmpclient.bulkCmd(self.authentication,
                                                self.target, 0, 25, oid)
            else:
                result = self.snmpclient.getCmd(self.authentication,
                                                self.target, oid)
        except NoSuchObjectError:
            raise SnmpNoInstanceError
        errorIndication, errorStatus, errorIndex, varBinds = result
        # can't get anything from this SNMP agent:
        # network or authorization problem
        if errorIndication:
            raise SnmpError(errorIndication)
        else:
            # problem with this specific OID
            if errorStatus:
                raise SnmpError('%s at %s' % (errorStatus, 
                                                varBinds[int(errorIndex)-1]) )
            # no problems, we got the value
            else:
                resultdict = {}
                for row in varBinds:
                    if bulk:
                        [(name, val)] = row
                        resultdict[name]=val
                        return resultdict
                    else:
                        name, val = row
                        if isinstance(val, Null):
                            raise SnmpNoInstanceError("OID doesn't exist")
                        return val
                        

    def get_table(self, oid):
        '''This method accepts the oid of the table ENTRY and returns a 
        dictionary containing the table. Currently only works with snmpv2 and3'''
        # explanation http://dartware.com/support/faqs/snmpfaqs.html#table
        table = {}
        parent = self.oid_converter.prettyIn(oid)
        parent = ObjectIdentifier(parent)
        if self.protocol in (2,3):
            raw = self.get(oid, bulk=True)
            for child in raw:
                if not parent.isPrefixOf(child):
                    continue
                nrs = child.prettyPrint().split('.')
                rij = int(nrs.pop())
                kolom = int(nrs.pop())
                try:
                    table[kolom][rij]= raw[child]
                except:
                    table[kolom] = {}
                    table[kolom][rij]= raw[child]
            return table
        elif protocol is 1:
            # TODO implement with  SNMPVv1 getnext
            pass
            
    def get_dict(self, oid_dict):
        '''Accepts a dictionary like this: 
        {'oidname1': '.1.2.3.4.5', 'oidname2':'.1.2.3.4.6'}
        and replaces the oid strings with their values, if they could be
        retrieved. Only the retrieved oid's will be returned
        Returns False if an SNMP error occured (other than not being able to
        retrieve a value)'''
        results = {}
        for name in oid_dict:
            try:
                x = self.get(oid_dict[name])
            except SnmpNoInstanceError:
                continue 
            except:
                return False
            else:
                results[name] = x
        return results
