from charmhelpers.core.host import (
    service
)
import mmap
import re
import os
from charmhelpers.core.hookenv import (
    config,
    log,
)

from charmhelpers.core import (
    unitdata,
)


def get_db_value(option):
    """
    Determine if config value changed since last call to this function.
    """
    hook_data = unitdata.HookData()
    with hook_data():
        db = unitdata.kv()
        return db.get(option)


def set_db_value(option, value):
    """
    Determine if config value changed since last call to this function.
    """
    hook_data = unitdata.HookData()
    with hook_data():
        db = unitdata.kv()
        db.set(option, value)


def has_db_value(option):
    """
    Determine if config value changed since last call to this function.
    """
    hook_data = unitdata.HookData()
    with hook_data():
        db = unitdata.kv()
        saved = db.get(option)
        if saved is not None:
            return True
        return False


def config_value_changed(option):
    """
    Determine if config value changed since last call to this function.
    """
    hook_data = unitdata.HookData()
    with hook_data():
        db = unitdata.kv()
        current = config(option)
        saved = db.get(option)
        db.set(option, current)
        if saved is None:
            return True
        log("config_value_changed {}:{}".format(option, (current != saved)))
        return current != saved


def update_config_file(config_file, key, value):
    """Updates or append configuration as key value pairs """
    insert_config = key + "=" + value
    with open(config_file, "r+") as vrs_file:
        mm = mmap.mmap(vrs_file.fileno(), 0)
        origFileSize = mm.size()
        newSize = len(insert_config)
        search_str = '^\s*' + key
        match = re.search(search_str, mm, re.MULTILINE)
        if match is not None:
            start_index = match.start()
            end_index = mm.find("\n", match.end())
            if end_index != -1:
                origSize = end_index - start_index
                if newSize > origSize:
                    newFileSize = origFileSize + len(insert_config) - origSize
                    mm.resize(newFileSize)
                    mm[start_index + newSize:] = mm[end_index:origFileSize]
                elif newSize < origSize:
                    insert_config += (" " * (int(origSize) - int(newSize)))
                    newSize = origSize
                mm[start_index:start_index + newSize] = str(insert_config)
            else:
                mm.resize(start_index + len(insert_config))
                mm[start_index:start_index + newSize] = str(insert_config)
        else:
            mm.seek(0, os.SEEK_END)
            mm.resize(origFileSize + len(insert_config) + 1)
            mm.write("\n" + insert_config)
        mm.close()


def create_nuage_metadata_file(username, password, tenant,
                               keystone_ip, host_ip_address):
    metadata_file = '/etc/default/nuage-metadata-agent'
    AUTH_URL = "http://" + str(keystone_ip) + ":5000/v2.0"

    update_config_file(metadata_file, "METADATA_PORT", str(9697))
    update_config_file(metadata_file, "NOVA_METADATA_IP", str(host_ip_address))
    update_config_file(metadata_file, "NOVA_METADATA_PORT", str(8775))
    update_config_file(metadata_file, "METADATA_PROXY_SHARED_SECRET",
                       get_shared_secret())
    update_config_file(metadata_file, "NOVA_CLIENT_VERSION", str(2))
    update_config_file(metadata_file, "NOVA_OS_USERNAME", str(username))
    update_config_file(metadata_file, "NOVA_OS_PASSWORD", str(password))
    update_config_file(metadata_file, "NOVA_OS_TENANT_NAME", str(tenant))
    update_config_file(metadata_file, "NOVA_OS_AUTH_URL", str(AUTH_URL))
    update_config_file(metadata_file, "NUAGE_METADATA_AGENT_START_WITH_OVS",
                       "true")
    update_config_file(metadata_file, "NOVA_API_ENDPOINT_TYPE", "publicURL")
    update_config_file(metadata_file, "NOVA_REGION_NAME", "RegionOne")


def vrs_full_restart():
    ''' Full restart and reload of Nuage VRS '''
    service('restart', 'nuage-openvswitch-switch')


def enable_nova_metadata():
    return config('enable-metadata')


def get_shared_secret():
    secret = 'NuageSharedSecret'
    return secret
