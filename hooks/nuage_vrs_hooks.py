#!/usr/bin/python3
# vim: set et ts=4:

import sys
import json
from nuage_vrs_utils import (
    config_value_changed,
    set_db_value,
    has_db_value,
    get_db_value,
    update_config_file,
    create_nuage_metadata_file,
    vrs_full_restart,
    enable_nova_metadata,
    get_shared_secret
)

from charmhelpers.core.hookenv import (
    config,
    log,
    ERROR,
    Hooks,
    UnregisteredHookError,
    unit_get,
    relation_get,
    relation_set,
    relation_ids,
    status_set,
)

from charmhelpers.core.host import (
    service_stop
)

from charmhelpers.fetch import (
    apt_update, apt_install, add_source
)

from charmhelpers.contrib.openstack.utils import (
    get_host_ip,
)

hooks = Hooks()


class ConfigurationError(Exception):
    pass


@hooks.hook()
def install():
    apt_update(fatal=True)
    dependencies = 'libjson-perl python-twisted-core'
    apt_install(dependencies.split(), fatal=True)


@hooks.hook('config-changed')
def config_changed():
    vrs_restart_flag = False
    # Install configured packages
    if config('vrs-repository-url') is not None:
        key = None
        if config('vrs-ppa-key') is not None:
            key = config('vrs-ppa-key')
        add_source(config('vrs-repository-url'), key)
    else:
        e = 'vrs-repository-url is not specified'
        status_set('blocked', e)
        raise ConfigurationError(e)

    status_set('maintenance', "Installing Packages")
    apt_update(fatal=True)
    apt_install(config('vrs-packages').split(), fatal=True)

    vrs_config_file = '/etc/default/openvswitch-switch'
    if config_value_changed('vrs-packages'):
        service_stop('nuage-openvswitch-switch')
        vrs_restart_flag = True

    if relation_get('vsc-ip-address') is not None:
        if (not(has_db_value('vsc-relation-active-ip')) or
                (relation_get('vsc-ip-address') is not
                    get_db_value('vsc-relation-active-ip'))):
            vrs_restart_flag = True
            set_db_value('vsc-relation-active-ip',
                         relation_get('vsc-ip-address'))
            vsc_active_controller = relation_get('vsc-ip-address')
            update_config_file(vrs_config_file, 'ACTIVE_CONTROLLER',
                               vsc_active_controller)
            status_set('active',
                       'vsc_active_controller: {}'.
                       format(vsc_active_controller))
    elif ((config_value_changed('vsc-controller-active')) and
            (config('vsc-controller-active') is not None)):
        vsc_active_controller = config('vsc-controller-active')
        vrs_restart_flag = True
        update_config_file(vrs_config_file, 'ACTIVE_CONTROLLER',
                           vsc_active_controller)
        status_set('active',
                   'vsc_active_controller: {}'.format(vsc_active_controller))

    else:
        status_set('waiting', 'ACTIVE VSC IP is not provided')
    # Standby VSC_IP_Address
    if ((config_value_changed('vsc-controller-standby')) and
            (config('vsc-controller-standby') is not None)):
        vsc_standby_controller = config('vsc-controller-standby')
        vrs_restart_flag = True
        update_config_file(vrs_config_file, 'STANDBY_CONTROLLER',
                           vsc_standby_controller)

    if vrs_restart_flag:
        vrs_full_restart()  # Full restart to clear states


@hooks.hook('vrs-controller-service-relation-changed')
def vrs_controller_changed(relation_id=None, remote_unit=None):
    vsc_ip_address = relation_get('vsc-ip-address')
    if not vsc_ip_address:
        log('Received no vsc_ip_address in vrs_controller_changed hook')
        return
    if get_db_value('vsc-relation-active-ip') is vsc_ip_address:
        log("vsc_ip_address has not changed ")
        return

    vrs_config_file = '/etc/default/openvswitch-switch'
    update_config_file(vrs_config_file, 'ACTIVE_CONTROLLER',
                       str(vsc_ip_address))
    vrs_full_restart()
    status_set('active', 'vsc_active_controller: {}'.format(vsc_ip_address))


@hooks.hook('identity-credentials-relation-joined')
def vrs_get_credentials_for_metadata_agent(relation_id=None, remote_unit=None):
    settings = {
        'username': config('vrs-metadata-name')
    }
    for r_id in relation_ids('identity-credentials'):
        relation_set(relation_id=r_id, **settings)


@hooks.hook('identity-credentials-relation-changed')
def vrs_set_credentials_for_metadata_agent(relation_id=None, remote_unit=None):
    username = relation_get("credentials_username")
    password = relation_get("credentials_password")
    tenant = relation_get("credentials_project")
    keystone_ip = relation_get("private-address")
    host_ip_address = get_host_ip(unit_get('private-address'))
    log("username:{}, password:{}, tenant:{}, keystone_ip:{}, private_ip: {}"
        .format(username, password, tenant, keystone_ip, host_ip_address))
    create_nuage_metadata_file(username, password,
                               tenant, keystone_ip,
                               host_ip_address)
    vrs_full_restart()


@hooks.hook('neutron-plugin-relation-joined')
def vrs_nova_plugin_joined(relation_id=None, remote_unit=None):
    secret = get_shared_secret() if enable_nova_metadata() else None
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
    if secret is not None:
        rel_data = {
            'metadata-shared-secret': secret,
            'subordinate_configuration': json.dumps(config),
        }
        log("Enabling and Configuring metadata agent")
        relation_set(relation_id=relation_id, **rel_data)


@hooks.hook()
def upgrade_charm():
    install()
    config_changed()


if __name__ == '__main__':
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {}, skipping'.format(e))
    except ConfigurationError as ce:
        log('Configuration error: {}'.format(ce), level=ERROR)
        sys.exit(1)
