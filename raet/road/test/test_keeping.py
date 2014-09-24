# -*- coding: utf-8 -*-
'''
Tests to try out keeping. Potentially ephemeral

'''
# pylint: skip-file
# pylint: disable=C0103
import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import os
import time
import tempfile
import shutil

from ioflo.base.odicting import odict
from ioflo.base.aiding import Timer, StoreTimer
from ioflo.base import storing
from ioflo.base.consoling import getConsole
console = getConsole()

from raet import raeting, nacling
from raet.road import estating, keeping, stacking


def setUpModule():
    console.reinit(verbosity=console.Wordage.concise)

def tearDownModule():
    pass

class BasicTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        self.store = storing.Store(stamp=0.0)
        self.timer = StoreTimer(store=self.store, duration=1.0)

        self.base = tempfile.mkdtemp(prefix="raet",  suffix="base", dir='/tmp')

    def tearDown(self):
        if os.path.exists(self.base):
            shutil.rmtree(self.base)

    def createRoadData(self, name, base, auto=None):
        '''
        Creates odict and populates with data to setup road stack
        {
            name: stack name local estate name
            dirpath: dirpath for keep files
            basedirpath: base dirpath for keep files
            sighex: signing key
            verhex: verify key
            prihex: private key
            pubhex: public key
        }
        '''
        data = odict()
        data['name'] = name
        data['auto'] = auto
        data['basedirpath'] = os.path.join(base, 'road', 'keep')
        data['dirpath'] = os.path.join(data['basedirpath'], name)
        signer = nacling.Signer()
        data['sighex'] = signer.keyhex
        data['verhex'] = signer.verhex
        privateer = nacling.Privateer()
        data['prihex'] = privateer.keyhex
        data['pubhex'] = privateer.pubhex


        return data

    def createRoadStack(self, data, uid=None, main=None, auto=None, ha=None, mutable=None):
        '''
        Creates stack and local estate from data with
        local estate.uid = uid
        stack.main = main
        stack.auto = auto
        stack.name = data['name']
        local estate.name = data['name']
        local estate.ha = ha

        returns stack

        '''

        stack = stacking.RoadStack(store=self.store,
                                   name=data['name'],
                                   uid=uid,
                                   ha=ha,
                                   sigkey=data['sighex'],
                                   prikey=data['prihex'],
                                   auto=auto if auto is not None else data['auto'],
                                   main=main,
                                   mutable=mutable,
                                   basedirpath=data['basedirpath'],)

        return stack

    def join(self, initiator, correspondent, deid=None, duration=1.0):
        '''
        Utility method to do join. Call from test method.
        '''
        console.terse("\nJoin Transaction **************\n")
        if not initiator.remotes:
            remote = initiator.addRemote(estating.RemoteEstate(stack=initiator,
                                                      fuid=0, # vacuous join
                                                      sid=0, # always 0 for join
                                                      ha=correspondent.local.ha))
            deid = remote.uid
        initiator.join(uid=deid)
        self.service(correspondent, initiator, duration=duration)

    def allow(self, other, main, duration=1.0):
        '''
        Utility method to do allow. Call from test method.
        '''
        console.terse("\nAllow Transaction **************\n")
        other.allow()
        self.service(main, other, duration=duration)

    def message(self, main,  other, mains, others, duration=2.0):
        '''
        Utility to send messages both ways
        '''
        for msg in mains:
            main.transmit(msg)
        for msg in others:
            other.transmit(msg)

        self.service(main, other, duration=duration)

    def service(self, main, other, duration=1.0):
        '''
        Utility method to service queues. Call from test method.
        '''
        self.timer.restart(duration=duration)
        while not self.timer.expired:
            other.serviceAll()
            main.serviceAll()
            if not (main.transactions or other.transactions):
                break
            self.store.advanceStamp(0.1)
            time.sleep(0.1)

    def flushRxMsgs(self, stack):
        '''
        Flush any queued up message packets in RxMessages
        '''
        while stack.rxMsgs:
            stack.rxMsgs.popleft()

    def testBasic(self):
        '''
        Basic keep setup for stack keep  persistence load and dump
        '''
        console.terse("{0}\n".format(self.testBasic.__doc__))
        auto = raeting.autoModes.once
        mainData = self.createRoadData(name='main',
                                       base=self.base,
                                       auto=auto)
        keeping.clearAllKeep(mainData['dirpath'])
        stack = self.createRoadStack(data=mainData,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        #console.terse("{0} keep dirpath = {1}\n".format(stack.name, stack.keep.dirpath))
        self.assertTrue(stack.keep.dirpath.endswith('/road/keep/main'))
        self.assertTrue(stack.keep.localfilepath.endswith('/road/keep/main/local/estate.json'))
        self.assertTrue(stack.keep.localrolepath.endswith('/road/keep/main/role/local/role.json'))
        self.assertTrue(stack.ha, ("0.0.0.0", raeting.RAET_PORT))

        # test round trip
        stack.clearLocalKeep()
        stack.clearRemoteKeeps()
        stack.clearLocalRoleKeep()
        stack.clearRemoteRoleKeeps()

        stack.dumpLocal()
        stack.dumpRemotes()

        self.assertTrue(os.path.exists(stack.keep.localdirpath))
        self.assertTrue(os.path.exists(stack.keep.remotedirpath))
        self.assertTrue(os.path.exists(stack.keep.localfilepath))
        self.assertTrue(os.path.exists(stack.keep.roledirpath))
        self.assertTrue(os.path.exists(stack.keep.remoteroledirpath))
        self.assertTrue(os.path.exists(stack.keep.localrolepath))

        localKeepData = stack.keep.loadLocalData()
        console.terse("Local keep data = '{0}'\n".format(localKeepData))
        validLocalKeepData =  odict([
                                        ('name', mainData['name']),
                                        ('uid', 1),
                                        ('ha', ['127.0.0.1', 7530]),
                                        ('iha', None),
                                        ('natted', None),
                                        ('fqdn', '1.0.0.127.in-addr.arpa'),
                                        ('dyned', None),
                                        ('sid', 0),
                                        ('puid', 1),
                                        ('aha', ['0.0.0.0', 7530]),
                                        ('role', mainData['name']),
                                        ('sighex', mainData['sighex']),
                                        ('prihex', mainData['prihex']),
                                    ])
        self.assertDictEqual(localKeepData, validLocalKeepData)

        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        self.assertDictEqual(remoteKeepData, {})

        # test round trip with stack methods
        stack.restoreLocal()
        localKeepData = odict([
                                ('uid', stack.local.uid),
                                ('name', stack.local.name),
                                ('ha', list(stack.local.ha)),
                                ('iha', None),
                                ('natted', None),
                                ('fqdn', stack.local.fqdn),
                                ('dyned', stack.local.dyned),
                                ('sid', stack.local.sid),
                                ('puid', stack.puid),
                                ('aha', list(stack.ha)),
                                ('role', stack.local.role),
                                ('sighex', stack.local.signer.keyhex),
                                ('prihex', stack.local.priver.keyhex),
                              ])
        self.assertDictEqual(localKeepData, validLocalKeepData)

        stack.removeAllRemotes(clear=False)
        stack.restoreRemotes()
        self.assertDictEqual(stack.remotes, {})

        # round trip with non empty remote data
        other1Data = self.createRoadData(name='other1',
                                         base=self.base,
                                         auto=raeting.autoModes.once,
                                         )
        stack.addRemote(estating.RemoteEstate(stack=stack,
                                              name=other1Data['name'],
                                              ha=('127.0.0.1', 7531),
                                              verkey=other1Data['verhex'],
                                              pubkey=other1Data['pubhex']))

        other2Data = self.createRoadData(name='other2',
                                         base=self.base,
                                         auto=raeting.autoModes.once,)
        stack.addRemote(estating.RemoteEstate(stack=stack,
                                              name=other2Data['name'],
                                              ha=('127.0.0.1', 7532),
                                              verkey=other2Data['verhex'],
                                              pubkey=other2Data['pubhex']))

        self.assertEqual(len(stack.remotes), len(stack.nameRemotes))
        for uid, remote in stack.remotes.items():
            self.assertEqual(stack.nameRemotes[remote.name], remote)
            self.assertEqual(stack.uidRemotes[remote.uid], remote)

        stack.dumpRemotes()
        self.assertTrue(os.path.exists(os.path.join(stack.keep.remotedirpath,
                "{0}.{1}.{2}".format(stack.keep.prefix,
                                     other1Data['name'],
                                     stack.keep.ext))))
        self.assertTrue(os.path.exists(os.path.join(stack.keep.remotedirpath,
                "{0}.{1}.{2}".format(stack.keep.prefix,
                                     other2Data['name'],
                                     stack.keep.ext))))
        self.assertTrue(os.path.exists(os.path.join(stack.keep.remoteroledirpath,
                "{0}.{1}.{2}".format('role',
                                     other1Data['name'],
                                     stack.keep.ext))))
        self.assertTrue(os.path.exists(os.path.join(stack.keep.remoteroledirpath,
                "{0}.{1}.{2}".format('role',
                                     other2Data['name'],
                                     stack.keep.ext))))

        for remote in stack.remotes.values():
            path = os.path.join(stack.keep.remotedirpath,
                     "{0}.{1}.{2}".format(stack.keep.prefix, remote.name, stack.keep.ext))
            self.assertTrue(os.path.exists(path))
        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        validRemoteKeepData = {
                                'other1':
                                    {'name': other1Data['name'],
                                     'uid': 2,
                                     'fuid': 0,
                                     'ha': ['127.0.0.1', 7531],
                                     'iha': None,
                                     'natted': None,
                                     'fqdn': '1.0.0.127.in-addr.arpa',
                                     'dyned': None,
                                     'sid': 0,
                                     'main': False,
                                     'kind': 0,
                                     'joined': None,
                                     'acceptance': None,
                                     'verhex': other1Data['verhex'],
                                     'pubhex': other1Data['pubhex'],
                                     'role': other1Data['name'],},
                                'other2':
                                    {'name': other2Data['name'],
                                     'uid': 3,
                                     'fuid': 0,
                                     'ha': ['127.0.0.1', 7532],
                                     'iha': None,
                                     'natted': None,
                                     'fqdn': '1.0.0.127.in-addr.arpa',
                                     'dyned': None,
                                     'sid': 0,
                                     'main': False,
                                     'kind': 0,
                                     'joined': None,
                                     'acceptance': None,
                                     'verhex': other2Data['verhex'],
                                     'pubhex': other2Data['pubhex'],
                                     'role': other2Data['name'],}
                                }
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        # stack method
        stack.removeAllRemotes(clear=False)
        stack.restoreRemotes()
        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.name] = odict([
                                                ('name', remote.name),
                                                ('uid', remote.uid),
                                                ('fuid', remote.fuid),
                                                ('ha', list(remote.ha)),
                                                ('iha', remote.iha),
                                                ('natted', remote.natted),
                                                ('fqdn', remote.fqdn),
                                                ('dyned', remote.dyned),
                                                ('sid', remote.sid),
                                                ('main', remote.main),
                                                ('kind', remote.kind),
                                                ('joined', remote.joined),
                                                ('role', remote.role),
                                                ('acceptance', remote.acceptance),
                                                ('verhex', remote.verfer.keyhex),
                                                ('pubhex', remote.pubber.keyhex),
                                              ])
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        stack.server.close()

        # bootstrap new stack from stored keep data
        stack = stacking.RoadStack(name=mainData['name'],
                                   auto=mainData['auto'],
                                   dirpath=mainData['dirpath'],
                                   store=self.store)
        localKeepData = odict([
                                ('name', stack.local.name),
                                ('uid', stack.local.uid),
                                ('ha', list(stack.local.ha)),
                                ('iha', stack.local.iha),
                                ('natted', stack.local.natted),
                                ('fqdn', stack.local.fqdn),
                                ('dyned', stack.local.dyned),
                                ('sid', stack.local.sid),
                                ('puid', stack.puid),
                                ('aha', list(stack.ha)),
                                ('role', stack.local.role),
                                ('sighex', stack.local.signer.keyhex),
                                ('prihex', stack.local.priver.keyhex),
                              ])
        console.terse("Local keep data = '{0}'\n".format(localKeepData))
        self.assertDictEqual(localKeepData, validLocalKeepData)

        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.name] = odict([
                                                ('name', remote.name),
                                                ('uid', remote.uid),
                                                ('fuid', remote.fuid),
                                                ('ha', list(remote.ha)),
                                                ('iha', remote.iha),
                                                ('natted', remote.natted),
                                                ('fqdn', remote.fqdn),
                                                ('dyned', remote.dyned),
                                                ('sid', remote.sid),
                                                ('main', remote.main),
                                                ('kind', remote.kind),
                                                ('joined', remote.joined),
                                                ('role', remote.role),
                                                ('acceptance', remote.acceptance),
                                                ('verhex', remote.verfer.keyhex),
                                                ('pubhex', remote.pubber.keyhex),
                                               ])
            validRemoteKeepData[remote.name]['sid'] += 1 #increments on stack load
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        stack.server.close()
        stack.clearAllKeeps()

    def testBasicMsgpack(self):
        '''
        Basic keep setup for stack keep  persistence load and dump with msgpack
        '''
        console.terse("{0}\n".format(self.testBasicMsgpack.__doc__))
        auto = raeting.autoModes.once
        mainData = self.createRoadData(name='main', base=self.base, auto=auto)
        keeping.clearAllKeep(mainData['dirpath'])
        keeping.RoadKeep.Ext = 'msgpack'
        stack = self.createRoadStack(data=mainData,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        #console.terse("{0} keep dirpath = {1}\n".format(stack.name, stack.keep.dirpath))
        self.assertTrue(stack.keep.dirpath.endswith('/road/keep/main'))
        self.assertTrue(stack.keep.localfilepath.endswith('/road/keep/main/local/estate.msgpack'))
        self.assertTrue(stack.keep.localrolepath.endswith('/road/keep/main/role/local/role.msgpack'))
        self.assertTrue(stack.ha, ("0.0.0.0", raeting.RAET_PORT))

        # test round trip
        stack.clearLocalKeep()
        stack.clearRemoteKeeps()
        stack.clearLocalRoleKeep()
        stack.clearRemoteRoleKeeps()

        stack.dumpLocal()
        stack.dumpRemotes()

        self.assertTrue(os.path.exists(stack.keep.localfilepath))
        self.assertTrue(os.path.exists(stack.keep.localrolepath))
        self.assertTrue(os.path.exists(stack.keep.localdirpath))
        self.assertTrue(os.path.exists(stack.keep.remotedirpath))
        self.assertTrue(os.path.exists(stack.keep.remoteroledirpath))

        localKeepData = stack.keep.loadLocalData()
        console.terse("Local keep data = '{0}'\n".format(localKeepData))
        validLocalKeepData =  odict([
                                        ('name', mainData['name']),
                                        ('uid', 1),
                                        ('ha', ['127.0.0.1', 7530]),
                                        ('iha', None),
                                        ('natted',  None),
                                        ('fqdn', '1.0.0.127.in-addr.arpa'),
                                        ('dyned', None),
                                        ('sid', 0),
                                        ('puid', 1),
                                        ('aha', ['0.0.0.0', 7530]),
                                        ('role', mainData['name']),
                                        ('sighex', mainData['sighex']),
                                        ('prihex', mainData['prihex']),
                                    ])
        self.assertDictEqual(localKeepData, validLocalKeepData)

        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        self.assertDictEqual(remoteKeepData, {})

        # test round trip with stack methods
        stack.restoreLocal()
        localKeepData = odict([
                                ('name', stack.local.name),
                                ('uid', stack.local.uid),
                                ('ha', list(stack.local.ha)),
                                ('iha', stack.local.iha),
                                ('natted', stack.local.natted),
                                ('fqdn', stack.local.fqdn),
                                ('dyned', stack.local.dyned),
                                ('sid', stack.local.sid),
                                ('puid', stack.puid),
                                ('aha', list(stack.ha)),
                                ('role', stack.local.role),
                                ('sighex', stack.local.signer.keyhex),
                                ('prihex', stack.local.priver.keyhex),
                              ])
        self.assertDictEqual(localKeepData, validLocalKeepData)

        stack.removeAllRemotes(clear=False)
        stack.restoreRemotes()
        self.assertDictEqual(stack.remotes, {})

        # round trip with non empty remote data
        other1Data = self.createRoadData(name='other1', base=self.base)
        stack.addRemote(estating.RemoteEstate(stack=stack,
                                              name=other1Data['name'],
                                              ha=('127.0.0.1', 7531),
                                              verkey=other1Data['verhex'],
                                              pubkey=other1Data['pubhex']))

        other2Data = self.createRoadData(name='other2', base=self.base)
        stack.addRemote(estating.RemoteEstate(stack=stack,
                                              name=other2Data['name'],
                                              ha=('127.0.0.1', 7532),
                                              verkey=other2Data['verhex'],
                                              pubkey=other2Data['pubhex']))

        self.assertEqual(len(stack.remotes), len(stack.nameRemotes))
        for uid, remote in stack.remotes.items():
            self.assertEqual(stack.nameRemotes[remote.name], remote)
            self.assertEqual(stack.uidRemotes[remote.uid], remote)

        stack.dumpRemotes()
        self.assertTrue(os.path.exists(os.path.join(stack.keep.remotedirpath,
                "{0}.{1}.{2}".format(stack.keep.prefix,
                                     other1Data['name'],
                                     stack.keep.ext))))
        self.assertTrue(os.path.exists(os.path.join(stack.keep.remotedirpath,
                "{0}.{1}.{2}".format(stack.keep.prefix,
                                     other2Data['name'],
                                     stack.keep.ext))))
        self.assertTrue(os.path.exists(os.path.join(stack.keep.remoteroledirpath,
                "{0}.{1}.{2}".format('role',
                                     other1Data['name'],
                                     stack.keep.ext))))
        self.assertTrue(os.path.exists(os.path.join(stack.keep.remoteroledirpath,
                "{0}.{1}.{2}".format('role',
                                     other2Data['name'],
                                     stack.keep.ext))))

        for remote in stack.remotes.values():
            path = os.path.join(stack.keep.remotedirpath,
                     "{0}.{1}.{2}".format(stack.keep.prefix, remote.name, stack.keep.ext))
            self.assertTrue(os.path.exists(path))
        remoteKeepData = stack.keep.loadAllRemoteData()
        console.terse("Remote keep data = '{0}'\n".format(remoteKeepData))
        validRemoteKeepData = {
                                'other1':
                                    {'name': other1Data['name'],
                                     'uid': 2,
                                     'fuid': 0,
                                     'ha': ['127.0.0.1', 7531],
                                     'iha': None,
                                     'natted': None,
                                     'fqdn': '1.0.0.127.in-addr.arpa',
                                     'dyned': None,
                                     'sid': 0,
                                     'main': False,
                                     'kind': 0,
                                     'joined': None,
                                     'role': other1Data['name'],
                                     'acceptance': None,
                                     'verhex': other1Data['verhex'],
                                     'pubhex': other1Data['pubhex'],
                                     },
                                'other2':
                                    {'name': other2Data['name'],
                                     'uid': 3,
                                     'fuid': 0,
                                     'ha': ['127.0.0.1', 7532],
                                     'iha': None,
                                     'natted': None,
                                     'fqdn': '1.0.0.127.in-addr.arpa',
                                     'dyned': None,
                                     'sid': 0,
                                     'main': False,
                                     'kind': 0,
                                     'joined': None,
                                     'role': other2Data['name'],
                                     'acceptance': None,
                                     'verhex': other2Data['verhex'],
                                     'pubhex': other2Data['pubhex'],
                                     }
                                }
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        # stack method
        stack.removeAllRemotes(clear=False)
        stack.restoreRemotes()
        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.name] = odict([
                                                ('name', remote.name),
                                                ('uid', remote.uid),
                                                ('fuid', remote.fuid),
                                                ('ha', list(remote.ha)),
                                                ('iha', remote.iha),
                                                ('natted', remote.natted),
                                                ('fqdn', remote.fqdn),
                                                ('dyned', remote.dyned),
                                                ('sid', remote.sid),
                                                ('main', remote.main),
                                                ('kind', remote.kind),
                                                ('joined', remote.joined),
                                                ('role', remote.role),
                                                ('acceptance', remote.acceptance),
                                                ('verhex', remote.verfer.keyhex),
                                                ('pubhex', remote.pubber.keyhex),
                                              ])
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        stack.server.close()

        # bootstrap new stack from stored keep data
        stack = stacking.RoadStack(name=mainData['name'],
                                   auto=mainData['auto'],
                                   dirpath=mainData['dirpath'],
                                   store=self.store)
        localKeepData = odict([
                                ('name', stack.local.name),
                                ('uid', stack.local.uid),
                                ('ha', list(stack.local.ha)),
                                ('iha', stack.local.iha),
                                ('natted', stack.local.natted),
                                ('fqdn', stack.local.fqdn),
                                ('dyned', stack.local.dyned),
                                ('sid', stack.local.sid),
                                ('puid', stack.puid),
                                ('aha', list(stack.ha)),
                                ('role', stack.local.role),
                                ('sighex', stack.local.signer.keyhex),
                                ('prihex', stack.local.priver.keyhex),
                              ])
        console.terse("Local keep data = '{0}'\n".format(localKeepData))
        self.assertDictEqual(localKeepData, validLocalKeepData)

        remoteKeepData = odict()
        for remote in stack.remotes.values():
            remoteKeepData[remote.name] = odict([
                                                ('name', remote.name),
                                                ('uid', remote.uid),
                                                ('fuid', remote.fuid),
                                                ('ha', list(remote.ha)),
                                                ('iha', remote.iha),
                                                ('natted', remote.natted),
                                                ('fqdn', remote.fqdn),
                                                ('dyned', remote.dyned),
                                                ('sid', remote.sid),
                                                ('main', remote.main),
                                                ('kind', remote.kind),
                                                ('joined', remote.joined),
                                                ('role', remote.role),
                                                ('acceptance', remote.acceptance),
                                                ('verhex', remote.verfer.keyhex),
                                                ('pubhex', remote.pubber.keyhex),
                                               ])
            validRemoteKeepData[remote.name]['sid'] += 1 #increments on stack load
        self.assertDictEqual(remoteKeepData, validRemoteKeepData)

        stack.server.close()
        stack.clearAllKeeps()

    def testAltDirpath(self):
        '''
        Keep fallback path function when don't have permissions to directory
        fallback to ~user/.raet
        '''
        console.terse("{0}\n".format(self.testAltDirpath.__doc__))
        base = '/var/cache/'
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=base,
                                   auto=auto)
        keeping.clearAllKeep(data['dirpath'])
        stack = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        #console.terse("{0} keep dirpath = {1}\n".format(stack.name, stack.keep.dirpath))
        self.assertTrue(".raet/keep/main" in stack.keep.dirpath)
        self.assertEqual(stack.ha, ("0.0.0.0", raeting.RAET_PORT))

        # test can write
        stack.clearLocalKeep()
        stack.clearRemoteKeeps()
        stack.clearLocalRoleKeep()
        stack.clearRemoteRoleKeeps()

        stack.dumpLocal()
        stack.dumpRemotes()

        stack.server.close()
        stack.clearAllKeeps()

    def testPending(self):
        '''
        Test pending behavior when not auto accept by main
        '''
        console.terse("{0}\n".format(self.testLostOtherKeep.__doc__))
        auto = raeting.autoModes.never #do not auto accept
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        keeping.clearAllKeep(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.never)

        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 1)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.acceptance, raeting.acceptances.pending)
        self.assertEqual(len(other.transactions), 1)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.acceptance, None)

        for remote in main.remotes.values():
            if remote.acceptance == raeting.acceptances.pending:
                main.keep.acceptRemote(remote)

        self.service(main, other, duration=3.0)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            self.assertEqual(len(stack.nameRemotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testPendingSavedKeep(self):
        '''
        Test pending behavior when not auto accept by main with saved keep data

        '''
        console.terse("{0}\n".format(self.testLostOtherKeep.__doc__))
        auto = raeting.autoModes.never #do not auto accept
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        keeping.clearAllKeep(data['dirpath'])
        savedOtherData = data
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.never)
        self.assertEqual(other.local.role, 'other')
        self.assertEqual(main.local.role, 'main')

        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 1)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.acceptance, raeting.acceptances.pending)
        self.assertEqual(len(other.transactions), 1)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None)
        self.assertEqual(remote.acceptance, None)

        #remove transactions
        remote = main.remotes.values()[0]
        for index in remote.transactions:
            remote.removeTransaction(index)

        remote = other.remotes.values()[0]
        for index in remote.transactions:
            remote.removeTransaction(index)

        for remote in main.remotes.values():
            if remote.acceptance == raeting.acceptances.pending:
                main.keep.acceptRemote(remote)

        #now reload from keep data
        main.removeAllRemotes(clear=False)
        main.restoreRemotes()
        main.restoreLocal()

        other.removeAllRemotes(clear=False)
        other.restoreRemotes()
        other.restoreLocal()

        # because main remote was not completely joined and was created as
        # part of vacuous join it was not dumped
        self.assertEqual(len(main.remotes), 0)
        roleData = main.keep.loadRemoteRoleData(other.local.role)
        self.assertIs(roleData['acceptance'], raeting.acceptances.accepted)

        self.join(other, main, duration=5.0)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        # now change name of other to see rejected on imutable road
        other.local.name = "whowho"
        self.join(other, main, duration=5.0)
        # main still has remote from prior join unchanged
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 1)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(remote.name, 'other') # not whowho
        # other has no remotes
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 0) # since rejected
        # but role of main on other from previous join still ok
        roleData = other.keep.loadRemoteRoleData(main.local.role)
        self.assertIs(roleData['acceptance'], raeting.acceptances.accepted)

        # change main to mutable and retry
        main.mutable = True
        self.join(other, main, duration=5.0)
        # main now has original and a new remote with new name
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 2)
        remote = main.remotes[3]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(remote.name, 'whowho')

        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main, other.remotes.values()[0].uid)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes[3]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        # now change ha  and unset unmutable
        main.mutable = None
        other.server.close()
        data = savedOtherData  # local keep will be there so it uses that data
        other = self.createRoadStack(data=data,
                                     main=None,)

        other.ha = ("0.0.0.0", 7532)
        other.local.ha = ("127.0.0.1", 7532)
        self.assertEqual(other.local.ha, ("127.0.0.1", 7532))
        self.assertEqual(len(main.remotes), 2)
        self.assertEqual(len(other.remotes), 1)
        self.join(other, main, duration=5.0)
        # old remote still there but ha unchanged
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes[3]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(remote.name, 'whowho')
        self.assertEqual(remote.ha, ('127.0.0.1', 7531))
        # other remote deleted since rejected
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 0)

        # change main to mutable and retry
        main.mutable = True
        other.server.close()
        other.clearLocalKeep()
        other.clearRemoteKeeps()
        other.clearLocalRoleKeep()
        other.clearRemoteRoleKeeps()

        data = savedOtherData
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", 7532))
        self.assertEqual(other.local.ha, ("127.0.0.1", 7532))
        other.local.name = "whowho"

        self.join(other, main, duration=5.0)
        # should reuse previous remote named whowho and update ha
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes[3]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)
        self.assertEqual(remote.name, 'whowho')
        self.assertEqual(remote.ha, ('127.0.0.1', 7532))

        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes[3]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testRejoin(self):
        '''
        Test rejoin after successful join with saved keys for both
        '''
        console.terse("{0}\n".format(self.testRejoin.__doc__))
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        mainDirpath = data['dirpath']
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertEqual(main.name, 'main')
        self.assertEqual(main.local.name, main.name)

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        otherDirpath = data['dirpath']
        keeping.clearAllKeep(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertEqual(other.name, 'other')
        self.assertEqual(other.local.name, other.name)
        self.assertIs(main.keep.auto, raeting.autoModes.once)

        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        #now close down and reload data
        main.server.close()
        other.server.close()

        # make new stacks with saved data
        main = stacking.RoadStack(dirpath=mainDirpath,
                                  store=self.store,
                                  main=True,
                                  auto=raeting.autoModes.once)
        other = stacking.RoadStack(dirpath=otherDirpath,
                                   store=self.store,
                                   auto=raeting.autoModes.once)

        # attempt to join to main with main auto accept enabled
        self.assertEqual(other.name, 'other')
        self.assertEqual(other.local.name, other.name)
        self.assertEqual(main.name, 'main')
        self.assertEqual(main.local.name, main.name)
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(other.keep.auto, raeting.autoModes.once)
        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        #now close down and reload data
        main.server.close()
        other.server.close()

        # attempt to join to main with main auto accept disabled
        # make new stacks with saved data
        main = stacking.RoadStack(dirpath=mainDirpath,
                                  store=self.store,
                                  main=True,
                                  auto=raeting.autoModes.never)
        other = stacking.RoadStack(dirpath=otherDirpath,
                                   store=self.store,
                                   auto=raeting.autoModes.once)


        self.assertIs(main.keep.auto, raeting.autoModes.never)
        self.assertIs(other.keep.auto, raeting.autoModes.once)
        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testRejoinFromMain(self):
        '''
        Test rejoin after successful join with saved keys for both initiated by main
        '''
        console.terse("{0}\n".format(self.testRejoinFromMain.__doc__))
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        mainDirpath = data['dirpath']
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertEqual(main.name, 'main')
        self.assertEqual(main.local.name, main.name)

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        otherDirpath = data['dirpath']
        keeping.clearAllKeep(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertEqual(other.name, 'other')
        self.assertEqual(other.local.name, other.name)
        self.assertIs(main.keep.auto, raeting.autoModes.once)

        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.joined)

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertTrue(remote.allowed)

        #now close down and reload data
        main.server.close()
        other.server.close()

        # make new stacks with saved data
        main = stacking.RoadStack(dirpath=mainDirpath,
                                  store=self.store,
                                  main=True,
                                  auto=raeting.autoModes.once)
        other = stacking.RoadStack(dirpath=otherDirpath, store=self.store)

        # attempt to join to other
        self.assertEqual(other.name, 'other')
        self.assertEqual(other.local.name, other.name)
        self.assertEqual(main.name, 'main')
        self.assertEqual(main.local.name, main.name)

        remote = main.remotes.values()[0]
        self.join(main, other, deid=remote.uid)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)

        self.allow(main, other)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testLostOtherKeep(self):
        '''
        Test rejection when other attempts to join with road data that are different
        from previous successful join
        '''
        console.terse("{0}\n".format(self.testLostOtherKeep.__doc__))
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        savedOtherData = data
        keeping.clearAllKeep(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)

        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        #now forget the other data
        for stack in [other]:
            stack.server.close()
            stack.clearAllKeeps()

        # reload with new data
        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept enabled should reject
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.join(other, main)
        # main still rememebers join from before
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, True)
        self.assertIs(remote.allowed,  True)
        # other is rejected so no remote
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 0)

        # now repeate with auto accept off but use old data
        # now forget the other data again
        for stack in [other]:
            stack.server.close()
            stack.clearAllKeeps()

        # reload with old data
        other = self.createRoadStack(data=savedOtherData,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept disabled
        main.keep.auto = raeting.autoModes.never # turn off auto accept
        self.assertIs(main.keep.auto, raeting.autoModes.never)
        self.join(other, main, duration=2.0)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        # now repeate with auto accept off but use new data
        # now forget the other data again
        for stack in [other]:
            stack.server.close()
            stack.clearAllKeeps()

        # reload with new data
        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept disabled
        main.keep.auto = raeting.autoModes.never # turn off auto accept
        self.assertIs(main.keep.auto, raeting.autoModes.never)
        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, True) # unlost other remote still there
        self.assertIs(remote.allowed,  True)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) #unlost other remote still accepted
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 0)

        # so try to send messages should fail
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 1) #didn't abort since duration too short
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0)
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testLostOtherKeepLocal(self):
        '''
        Test rejection when other attempts to join with local keys that are different
        from previous successful join
        '''
        console.terse("{0}\n".format(self.testLostOtherKeepLocal.__doc__))
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     mutable=None,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        savedOtherData = data
        keeping.clearAllKeep(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)

        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, None)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        # so try to send messages
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=3.0)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg[0])
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg[0])

        for stack in [main, other]:
            self.flushRxMsgs(stack)

        #now forget the other data local only to simulate just changing other keys
        other.server.close()
        other.clearLocalKeep()

        # reload with new data
        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept disabled
        main.keep.auto = raeting.autoModes.never # turn off auto accept
        self.assertIs(main.keep.auto, raeting.autoModes.never)
        self.join(other, main, duration=2.0)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, True) # unlost other remote still there
        self.assertIs(remote.allowed, True)
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) #unlost other remote still accepted
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 0)

        # so try to send messages should fail since keys not match
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 1) #didn't abort since duration too short
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0)
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        #remove transactions
        remote = main.remotes.values()[0]
        for index in remote.transactions:
            remote.removeTransaction(index)


        # now reload original local other data should work as rejoin
        other.server.close()
        other.clearLocalKeep()
        data = savedOtherData
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept disabled
        main.keep.auto = raeting.autoModes.never # turn off auto accept
        self.assertIs(main.keep.auto, raeting.autoModes.never)
        self.join(other, main, duration=2.0)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)

        # so try to send messages
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=3.0)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg[0])
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg[0])

        for stack in [main, other]:
            self.flushRxMsgs(stack)

        # now forget the other data again
        other.server.close()
        other.clearLocalKeep()

        # reload with new data
        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))


        # attempt to join to main with main auto accept enabled and mutable
        # still reject because keys differ
        main.keep.auto = raeting.autoModes.once # turn on auto accept
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        main.mutable =  True
        self.assertIs(main.mutable, True)
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertTrue(remote.joined)
        self.assertTrue(remote.allowed)
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 0)

        # now reload original local other data and see if works
        other.server.close()
        other.clearLocalKeep()
        data = savedOtherData
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))

        # attempt to join to main with main auto accept disabled and immutable
        main.keep.auto = raeting.autoModes.never # turn off auto accept
        self.assertIs(main.keep.auto, raeting.autoModes.never)
        main.mutable = None
        self.assertIs(main.mutable, None)
        self.join(other, main, duration=2.0)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testLostMainKeep(self):
        '''
        Test rejection when other attempts to join to main where main's data is
        different from previous successful join
        '''
        console.terse("{0}\n".format(self.testLostMainKeep.__doc__))
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        savedMainData = data
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)
        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        savedOtherData = data
        keeping.clearAllKeep(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertIs(other.keep.auto, raeting.autoModes.once)
        self.assertIs(other.mutable, None)

        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)


        #now forget the main data only to simulate main changing all data
        for stack in [main]:
            stack.server.close()
            stack.clearAllKeeps()

        # reload with new data
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)

        # attempt to join to main with main auto accept enabled
        # renew request refused by other since not mutable
        self.assertEqual(other.mutable, None)
        self.join(other, main, duration=4.0) # main will refuse renew
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 1)
        self.assertIs(remote.joined, None)

        # renew attempt refused by other since main credentials different and accept once
        other.mutable = True
        self.assertEqual(other.mutable, True)
        self.join(other, main, duration=4.0) # main will refuse and other will renew
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 1)
        self.assertIs(remote.joined, None)

        self.allow(other, main) # will fail
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0) # not joined so aborts
        remote = other.remotes.values()[0]
        self.assertIs(remote.allowed, None) # new other not joined so aborted allow

        # so try to send messages should fail
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertEqual(len(main.rxMsgs), 0)
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertEqual(len(other.rxMsgs), 0)

        # now restore original main keys  so it will work
        #now forget the new main data
        for stack in [main]:
            stack.server.close()
            stack.clearAllKeeps()

        # reload with original saved data
        auto = raeting.autoModes.once
        data = savedMainData
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)
        other.mutable = None
        self.assertEqual(other.mutable, None)

        # attempt to join to main with main auto accept enabled and immutable
        # will fail since renew not allowd on immutable other
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None)

        # attempt to join to main with main auto accept enabled and mutable other
        other.mutable = True
        self.assertEqual(other.mutable, True)
        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        # so try to send messages should succeed
        self.assertEqual(main.remotes.values()[0].fuid, other.remotes.values()[0].nuid)
        self.assertEqual(main.remotes.values()[0].nuid, other.remotes.values()[0].fuid)
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg[0])
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg[0])

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

    def testLostMainKeepLocal(self):
        '''
        Test rejection when other attempts to join to main where main's local keys are
        different from previous successful join
        '''
        console.terse("{0}\n".format(self.testLostMainKeepLocal.__doc__))
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        savedMainData = data
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        keeping.clearAllKeep(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertIs(other.keep.auto, raeting.autoModes.once)
        self.assertIs(other.mutable, None)

        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        #now forget the main local data only to simulate main changing keys
        main.server.close()
        main.clearLocalKeep()

        # reload with new local data and saved remote data
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)
        remote = main.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        # attempt to join to main with main auto accept enabled main will accept
        # but other reject since main keys differ from previous join and immutable
        # so main will delete remote
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None) # no lost main remote still there
        # no lost main still accepted
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        # allow will fail but trigger join which which will attempt join but
        # no remote on main side so trigger renew which will fail since immutable
        self.allow(other, main) # fails so attempts join which is renewed and fails
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.allowed, None) # new other not joined so aborted allow
        self.assertIs(remote.joined, None) # failed allow will start join

        # renew attempt refused by other since main credentials different and accept once
        other.mutable = True
        self.assertEqual(other.mutable, True)
        self.join(other, main, duration=4.0) # main will refuse and other will renew
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 1)
        self.assertIs(remote.joined, None)

        self.allow(other, main) # will fail
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0) # not joined so aborts
        remote = other.remotes.values()[0]
        self.assertIs(remote.allowed, None) # new other not joined so aborted allow

        # so try to send messages should fail since keys not match
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        # now restore original main keys to see if works
        # first forget the new main local data
        main.server.close()
        main.clearLocalKeep()

        # reload with original saved data
        auto = raeting.autoModes.once
        data = savedMainData
        main = self.createRoadStack(data=data,
                                     main=True,
                                     auto=auto,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))


        # attempt to join to main with main auto accept enabled will attempt
        # to renew but refused because immutable
        other.mutable = None
        self.assertEqual(other.mutable, None)
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        self.assertEqual(len(main.remotes), 0)
        self.assertEqual(len(other.transactions), 0)
        remote = other.remotes.values()[0]
        self.assertIs(remote.joined, None)

        # attempt to join to main with main auto accept enabled will renew
        # successfully because mutable
        other.mutable = True
        self.assertEqual(other.mutable, True)
        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        # so try to send messages should succeed
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg[0])
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg[0])

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()


    def testLostBothKeepLocal(self):
        '''
        Test when both other and main lose local data to simulate both changing
        their local keys but keeping their remote data
        '''
        console.terse("{0}\n".format(self.testLostMainKeepLocal.__doc__))
        #self.base = tempfile.mkdtemp(prefix="raet",  suffix="base", dir='/tmp')
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        savedMainData = data
        keeping.clearAllKeep(data['dirpath'])
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=raeting.autoModes.once)
        savedOtherData = data
        keeping.clearAllKeep(data['dirpath'])
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertIs(other.keep.auto, raeting.autoModes.once)
        self.assertIs(other.mutable, None)

        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        #save copy of other remotes
        otherRemotes = odict(other.remotes)

        #now forget the local local data only to simulate both changing keys
        main.server.close()
        main.clearLocalKeep()
        other.server.close()
        other.clearLocalKeep()

        # reload with new local data and saved remote data
        auto = raeting.autoModes.once
        data = self.createRoadData(name='main',
                                   base=self.base,
                                   auto=auto)
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        data = self.createRoadData(name='other',
                                   base=self.base,
                                   auto=auto)
        other = self.createRoadStack(data=data,
                                     main=None,
                                     ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        remote = main.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        remote = other.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        # attempt to join to main with main auto accept enabled
        self.join(other, main)
        self.assertEqual(len(main.transactions), 0)
        #Joinent will reject as name already in use
        remote = main.remotes.values()[0]
        self.assertIs(remote.joined, True) # Previous joined still there
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 0) # join nacked so remote deleted

        self.allow(other, main)
        self.assertEqual(len(main.transactions), 0)
        remote = main.remotes.values()[0]
        self.assertIs(remote.allowed, None) # not persisted
        self.assertEqual(len(other.transactions), 0)
        self.assertEqual(len(other.remotes), 0) # join nacked so remote deleted

        # so try to send messages should fail since keys not match
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(others), len(main.rxMsgs))
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertNotEqual(len(mains), len(other.rxMsgs))

        # now restore original local keys to see if works
        #now forget the new main data
        main.server.close()
        main.clearLocalKeep()
        other.server.close()
        other.clearLocalKeep()

        # reload with original saved data
        data = savedMainData
        main = self.createRoadStack(data=data,
                                     main=True,
                                     ha=None)
        #default ha is ("", raeting.RAET_PORT)

        data = savedOtherData
        other = self.createRoadStack(data=data,
                                    main=None,
                                    ha=("", raeting.RAET_TEST_PORT))

        self.assertTrue(main.keep.dirpath.endswith('road/keep/main'))
        self.assertEqual(main.ha, ("0.0.0.0", raeting.RAET_PORT))
        self.assertIs(main.keep.auto, raeting.autoModes.once)
        self.assertIs(main.mutable, None)
        remote = main.remotes.values()[0]
        self.assertEqual(remote.acceptance, raeting.acceptances.accepted) # saved still accepted

        self.assertTrue(other.keep.dirpath.endswith('road/keep/other'))
        self.assertEqual(other.ha, ("0.0.0.0", raeting.RAET_TEST_PORT))
        self.assertIs(other.keep.auto, raeting.autoModes.once)
        self.assertIs(other.mutable, None)
        # the failed join attempt deleted the remote
        self.assertEqual(len(other.remotes), 0)

        # attempt to join to main with main auto accept enabled
        self.join(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)


        self.allow(other, main)
        for stack in [main, other]:
            self.assertEqual(len(stack.transactions), 0)
            self.assertEqual(len(stack.remotes), 1)
            remote = stack.remotes.values()[0]
            self.assertIs(remote.joined, True)
            self.assertIs(remote.allowed, True)
            self.assertEqual(remote.acceptance, raeting.acceptances.accepted)

        # so try to send messages should succeed
        mains = [odict(content="Hello other body")]
        others = [odict(content="Hello main body")]
        self.message(main, other, mains, others,  duration=2.0)
        self.assertEqual(len(main.transactions), 0) #not allowed so aborted
        self.assertEqual(len(others), len(main.rxMsgs))
        for i, msg in enumerate(main.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(main.local.name, msg))
            self.assertDictEqual(others[i], msg[0])
        self.assertEqual(len(other.transactions), 0) #not allowed so aborted
        self.assertEqual(len(mains), len(other.rxMsgs))
        for i, msg in enumerate(other.rxMsgs):
            console.terse("Estate '{0}' rxed:\n'{1}'\n".format(other.local.name, msg))
            self.assertDictEqual(mains[i], msg[0])

        for stack in [main, other]:
            stack.server.close()
            stack.clearAllKeeps()

def runOne(test):
    '''
    Unittest Runner
    '''
    test = BasicTestCase(test)
    suite = unittest.TestSuite([test])
    unittest.TextTestRunner(verbosity=2).run(suite)

def runSome():
    '''
    Unittest runner
    '''
    tests =  []
    names = ['testBasic',
             'testBasicMsgpack',
             'testAltDirpath',
             'testPending',
             'testPendingSavedKeep',
             'testRejoin',
             'testRejoinFromMain',
             'testLostOtherKeep',
             'testLostOtherKeepLocal',
             'testLostMainKeep',
             'testLostMainKeepLocal',
             'testLostBothKeepLocal',]

    tests.extend(map(BasicTestCase, names))

    suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)

def runAll():
    '''
    Unittest runner
    '''
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BasicTestCase))

    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__' and __package__ is None:

    #console.reinit(verbosity=console.Wordage.concise)

    #runAll() #run all unittests

    runSome()#only run some

    #runOne('testRejoinFromMain')

