from mock import patch, call

from test_utils import (
    CharmTestCase,
)
import nuage_vrs_hooks as hooks

with patch('charmhelpers.core.hookenv.config') as config:
    config.return_value = 'nuage-vrs'


hooks.hooks._config_save = False

TO_PATCH = [
    'config',
    'apt_update',
    'apt_install',
    'add_source',
    'relation_get',
    'relation_set',
    'service_stop',
    'update_config_file',
    'vrs_full_restart',
    'config_value_changed',
    'status_set',
    'set_db_value',
    'get_db_value',
    'has_db_value',
    'create_nuage_metadata_file',
    'enable_nova_metadata',
    'get_shared_secret',
    'relation_ids',
    'get_host_ip',
    'unit_get',
    'json'
]

nuage_vrs_config_changed = {
    'vrs-packages': True,
    'vsc-controller-active': True,
    'vsc-controller-standby': True,
}


def _mock_config_value_changed(option):
    return nuage_vrs_config_changed[option]


class TestNuageVRS(CharmTestCase):
    def _call_hook(self, hookname):
        hooks.hooks.execute([
            'hooks/{}'.format(hookname)])

    def setUp(self):
        super(TestNuageVRS, self).setUp(hooks, TO_PATCH)
        self.config.side_effect = self.test_config.get
        self.relation_get.side_effect = self.test_relation.get
        self.config_value_changed.side_effect = _mock_config_value_changed

    def test_install_nuage_vrs(self):
        _pkgs = ["libjson-perl", "python-twisted-core"]

        self._call_hook('install')
        self.apt_update.assert_called_with(fatal=True)
        self.apt_install.assert_has_calls([
            call(_pkgs, fatal=True),
        ])

    def test_config_changed_nuage_vrs_defaults(self):  # , config_val_changed):
        with self.assertRaises(Exception) as context:
            self._call_hook('config-changed')
        self.assertEqual(context.exception.message,
                         'vrs-repository-url is not specified')
        vrs_repo_url = 'http://www.nuagerepo.net/vrs'
        self.test_config.set('vrs-repository-url',
                             vrs_repo_url)
        _vrspkgs = ["nuage-metadata-agent", "nuage-openvswitch-common",
                    "nuage-openvswitch-datapath-dkms",
                    "nuage-python-openvswitch", "nuage-openvswitch-switch"]

        nuage_vrs_config_changed['vrs-packages'] = False
        nuage_vrs_config_changed['vsc-controller-active'] = False
        nuage_vrs_config_changed['vsc-controller-standby'] = False
        self._call_hook('config_changed')
        self.add_source.assert_called_with(vrs_repo_url, None)
        self.apt_update.assert_called_with(fatal=True)
        self.apt_install.assert_has_calls([
            call(_vrspkgs, fatal=True),
        ])
        self.assertFalse(self.service_stop.called)
        self.assertFalse(self.update_config_file.called)
        self.assertFalse(self.vrs_full_restart.called)

        nuage_vrs_config_changed['vrs-packages'] = True
        nuage_vrs_config_changed['vsc-controller-active'] = True
        nuage_vrs_config_changed['vsc-controller-standby'] = True
        self._call_hook('config_changed')
        self.apt_install.assert_has_calls([
            call(_vrspkgs, fatal=True),
        ])
        self.assertTrue(self.service_stop.called)
        self.assertTrue(self.vrs_full_restart.called)
        self.assertTrue(self.update_config_file.called)

    def test_config_changed_nuage_vrs_active(self):  # , config_val_changed):
        self.test_config.set('vrs-repository-url',
                             'http://www.nuagerepo.net/vrs')
        _vrspkgs = ["nuage-metadata-agent", "nuage-openvswitch-common",
                    "nuage-openvswitch-datapath-dkms",
                    "nuage-python-openvswitch", "nuage-openvswitch-switch"]
        vrs_config_file = '/etc/default/openvswitch-switch'

        self.test_config.set('vsc-controller-active', '1.1.1.1')
        self._call_hook('config_changed')
        self.apt_install.assert_has_calls([
            call(_vrspkgs, fatal=True),
        ])
        self.assertTrue(self.service_stop.called)
        self.update_config_file.assert_has_calls([
            call(vrs_config_file, 'ACTIVE_CONTROLLER', '1.1.1.1'),
        ])
        self.assertTrue(self.vrs_full_restart.called)

    def test_config_changed_nuage_vrs_standby(self):  # , config_val_changed):
        self.test_config.set('vrs-repository-url',
                             'http://www.nuagerepo.net/vrs')
        _vrspkgs = ["nuage-metadata-agent", "nuage-openvswitch-common",
                    "nuage-openvswitch-datapath-dkms",
                    "nuage-python-openvswitch", "nuage-openvswitch-switch"]
        vrs_config_file = '/etc/default/openvswitch-switch'
        nuage_vrs_config_changed['vrs-packages'] = True
        nuage_vrs_config_changed['vsc-controller-active'] = True
        nuage_vrs_config_changed['vsc-controller-standby'] = True
        self.test_config.set('vsc-controller-active', '1.1.1.1')
        self.test_config.set('vsc-controller-standby', '2.2.2.2')
        self._call_hook('config_changed')
        self.apt_install.assert_has_calls([
            call(_vrspkgs, fatal=True),
        ])
        self.assertTrue(self.vrs_full_restart.called)
        self.update_config_file.assert_has_calls([
            call(vrs_config_file, 'ACTIVE_CONTROLLER', '1.1.1.1'),
            call(vrs_config_file, 'STANDBY_CONTROLLER', '2.2.2.2'),
        ])

    def test_config_changed_nuage_vrs_packages(self):  # , config_val_changed):
        self.test_config.set('vrs-repository-url',
                             'http://www.nuagerepo.net/vrs')
        _vrspkgs = ["nuage-metadata-agent", "nuage-openvswitch-common",
                    "nuage-openvswitch-datapath-dkms",
                    "nuage-python-openvswitch", "nuage-openvswitch-switch"]
        vrs_config_file = '/etc/default/openvswitch-switch'
        self.test_config.set('vsc-controller-active', '1.1.1.1')
        self.test_config.set('vsc-controller-standby', '2.2.2.2')
        nuage_vrs_config_changed['vrs-packages'] = False
        nuage_vrs_config_changed['vsc-controller-active'] = True
        nuage_vrs_config_changed['vsc-controller-standby'] = True
        self._call_hook('config_changed')
        self.apt_install.assert_has_calls([
            call(_vrspkgs, fatal=True),
        ])
        self.assertFalse(self.service_stop.called)
        self.assertTrue(self.vrs_full_restart.called)
        self.update_config_file.assert_has_calls([
            call(vrs_config_file, 'ACTIVE_CONTROLLER', '1.1.1.1'),
            call(vrs_config_file, 'STANDBY_CONTROLLER', '2.2.2.2'),
        ])

    def test_vrs_controller_relation_changed(self):
        self.test_relation.set({
            'vsc-ip-address': '10.11.12.13',
        })
        self._call_hook('vrs-controller-service-relation-changed')
        vrs_config_file = '/etc/default/openvswitch-switch'
        self.update_config_file.assert_has_calls([
            call(vrs_config_file, 'ACTIVE_CONTROLLER', '10.11.12.13'),
        ])

    def test_honoring_vsc_ip_form_relation(self):
        self.test_relation.set({
            'vsc-ip-address': '10.11.12.13',
        })
        self.test_config.set('vrs-repository-url',
                             'http://www.nuagerepo.net/vrs')
        vrs_config_file = '/etc/default/openvswitch-switch'

        self.test_config.set('vsc-controller-active', '1.1.1.1')
        self._call_hook('config_changed')

        self.update_config_file.assert_has_calls([
            call(vrs_config_file, 'ACTIVE_CONTROLLER', '10.11.12.13'),
        ])

        self.test_config.set('vsc-controller-active', '1.1.1.2')
        self._call_hook('config_changed')
        self.update_config_file.assert_has_calls([
            call(vrs_config_file, 'ACTIVE_CONTROLLER', '10.11.12.13'),
        ])

    def test_identity_credentials_relation_joined(self):
        self.test_config.set('vrs-metadata-name', 'nuage')
        metadata_name = self.test_config.get('vrs-metadata-name')
        settings = {
            'username': metadata_name
        }

        self.relation_ids.return_value = ['identity-credentials']
        self._call_hook('identity-credentials-relation-joined')
        self.relation_set.assert_called_with(relation_id=
                                             'identity-credentials',
                                             **settings)

    @patch('charmhelpers.contrib.openstack.ip.unit_get')
    def test_identity_credentials_relation_changed(self, _unit_get):
        _unit_get.return_value = '10.0.0.1'

        self.test_relation.set({'credentials_username': 'fake'})
        self.test_relation.set({"credentials_password": 'fakepass'})
        self.test_relation.set({"credentials_project": 'services'})
        self.test_relation.set({"private-address": '10.0.0.0'})
        self.get_host_ip.return_value = "10.0.0.1"
        username = self.test_relation.get('credentials_username')
        password = self.test_relation.get("credentials_password")
        tenant = self.test_relation.get("credentials_project")
        keystone_ip = self.test_relation.get("private-address")

        host_ip_address = '10.0.0.1'
        self._call_hook('identity-credentials-relation-changed')
        self.create_nuage_metadata_file.assert_called_with(
            username, password,
            tenant, keystone_ip,
            host_ip_address
        )
        self.assertTrue(self.vrs_full_restart.called)

    @patch.object(hooks, 'json')
    def test_neutron_plugin_relation_joined(self, json):
        self.test_config.set('enable-metadata', True)
        secret = self.get_shared_secret.return_value
        config = {
            "nova-compute": {
                "/etc/nova/nova.conf": {
                    "sections": {
                        'DEFAULT': [
                            ('use_forward_for',
                             'true'),
                        ],
                    }
                }
            }
        }
        self._call_hook('neutron-plugin-relation-joined')
        rel_data = {
            'metadata-shared-secret': secret,
            'subordinate_configuration': json.dumps(config),
        }
        self.relation_set.assert_called_with(relation_id=None, **rel_data)
