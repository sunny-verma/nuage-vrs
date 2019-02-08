Nuage VRS
------------------

Overview
========

The principle use of this charm is with the nova-compute charm as a subordinate and used within an OpenStack deployment .

This charm should be used with other principle charms to install and configure
the service units as Transport Nodes within a Nuage controller cluster.

NOTE: this charm relies on binaries that are distributed to customers of Nuage Networks VSP solution.

Usage
=====

The VRS repositories are as an URL (http/ppa) by Nuage Networks to customers to download and deploy using Juju deployer..

The charm expects to find deb's; if they are missing the install hook will error out.

To deploy:
    juju deploy nuage-vrs
	juju add-relation nuage-vrs nova-compute
	juju add-relation nuage-vrs nuage-vsc 

Note that the nuage-vsc relation is optional if the nuage services are not deployed using JUJU chanrms.

Below Configuration are must for Nuage-VRS deployment:
=============


  vrs-repository-url:
    description: Nuage VRS repository containing Debian packages.This is must for installing vrs-packages
    Note : You must give this configuration as your deployment will fail is this parameter is not provided.
    This will have all the vrs-packages as debians.
