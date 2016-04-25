from charmhelpers.core.hookenv import unit_private_ip, config
from charms.reactive import (
    hook,
    when,
)
from charm.openstack.designate import DesignateCharmFactory
import ipaddress

from relations.hacluster.common import CRM
from relations.hacluster.common import ResourceDescriptor
from charm.openstack.charm import VirtualIP

@hook('install')
def install_packages():
    charm = DesignateCharmFactory.charm()
    charm.configure_source()
    charm.install()


@when('amqp.connected')
def setup_amqp_req(amqp):
    amqp.request_access(username='designate',
                        vhost='openstack')


@when('shared-db.connected')
def setup_database(database):
    database.configure('designate', 'designate',
                       unit_private_ip(), prefix='designate')
    database.configure('dpm', 'dpm',
                       unit_private_ip(), prefix='dpm')


@when('identity-service.connected')
def setup_endpoint(keystone):
    charm = DesignateCharmFactory.charm()
    keystone.register_endpoints(charm.service_type,
                                charm.region,
                                charm.public_url,
                                charm.internal_url,
                                charm.admin_url)


@when('dns-backend.available')
@when('shared-db.available')
@when('identity-service.available')
@when('amqp.available')
def render_stuff(amqp_interface, identity_interface, db_interface,
                 dns_interface):
    charm = DesignateCharmFactory.charm(
        interfaces=[amqp_interface, identity_interface, db_interface,
                    dns_interface]
    )
    charm.render_base_config()
    charm.db_sync()
    charm.create_domains()
    charm.render_full_config()

@when('ha.connected')
def cluster_connected(hacluster):
    user_config = config()
    resources = CRM()
    resources.add(VirtualIP(user_config['vip']))

    hacluster.bind_on(iface=user_config['vip_iface'], mcastport=4440)
    hacluster.manage_resources(resources)
