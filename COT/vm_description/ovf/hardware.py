#!/usr/bin/env python
#
# hardware.py - OVFHardware class
#
# June 2016, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Representation of OVF hardware definitions.

**Classes and Exceptions**

.. autosummary::
  :nosignatures:

  OVFHardware
  OVFHardwareDataError
"""

import copy
import logging

from COT.data_validation import natural_sort
from COT.xml_file import XML

from .item import OVFItem, OVFItemDataError

logger = logging.getLogger(__name__)


class OVFHardwareDataError(Exception):
    """The input data used to construct an :class:`OVFHardware` is not sane."""


class OVFHardware(object):
    """Helper class for :class:`~COT.vm_description.ovf.ovf.OVF`.

    Represents all hardware items defined by this OVF;
    i.e., the contents of all Items in the VirtualHardwareSection.

    Fundamentally it's just a dict of
    :class:`~COT.vm_description.ovf.item.OVFItem` objects
    with a bunch of helper methods.
    """

    def __init__(self, ovf):
        """Construct an OVFHardware object describing all Items in the OVF.

        Args:
          ovf (OVF): OVF instance to extract hardware information from.

        Raises:
          OVFHardwareDataError: if any data errors are seen
        """
        self.ovf = ovf
        self.item_dict = {}
        valid_profiles = set(ovf.config_profiles)
        item_count = 0
        for item in ovf.virtual_hw_section:
            namespace = ovf.namespace_for_item_tag(item.tag)
            if not namespace:
                continue
            item_count += 1
            # We index the dict by InstanceID as it's the one property of
            # an Item that uniquely identifies this set of hardware items.
            instance = item.find(namespace + self.ovf.INSTANCE_ID).text

            # Pre-sanity check - are all of the profiles associated with this
            # item properly defined in the OVF DeploymentOptionSection?
            item_profiles = set(item.get(self.ovf.ITEM_CONFIG, "").split())
            unknown_profiles = item_profiles - valid_profiles
            if unknown_profiles:
                raise OVFHardwareDataError("Unknown profile(s) {0} for "
                                           "Item instance {1}"
                                           .format(unknown_profiles, instance))

            if instance not in self.item_dict:
                self.item_dict[instance] = OVFItem(self.ovf, item)
            else:
                try:
                    self.item_dict[instance].add_item(item)
                except OVFItemDataError as exc:
                    logger.debug(exc)
                    # Mask away the nitty-gritty details from our caller
                    raise OVFHardwareDataError("Data conflict for instance {0}"
                                               .format(instance))
        logger.debug(
            "OVF contains %s hardware Item elements describing %s "
            "unique devices", item_count, len(self.item_dict))
        # Treat the current state as golden:
        for ovfitem in self.item_dict.values():
            ovfitem.modified = False

    def update_xml(self):
        """Regenerate all Items under the VirtualHardwareSection, if needed.

        Will do nothing if no Items have been changed.
        """
        modified = False
        if len(self.item_dict) != len(XML.find_all_children(
                self.ovf.virtual_hw_section,
                set([self.ovf.ITEM, self.ovf.STORAGE_ITEM,
                     self.ovf.ETHERNET_PORT_ITEM]))):
            modified = True
        else:
            for ovfitem in self.item_dict.values():
                if ovfitem.modified:
                    modified = True
                    break
        if not modified:
            logger.verbose("No changes to hardware definition, "
                           "so no XML update is required")
            return
        # Delete the existing Items:
        delete_count = 0
        for item in list(self.ovf.virtual_hw_section):
            if (item.tag == self.ovf.ITEM or
                    item.tag == self.ovf.STORAGE_ITEM or
                    item.tag == self.ovf.ETHERNET_PORT_ITEM):
                self.ovf.virtual_hw_section.remove(item)
                delete_count += 1
        logger.debug("Cleared %d existing items from VirtualHWSection",
                     delete_count)
        # Generate the new XML Items, in appropriately sorted order by Instance
        ordering = [self.ovf.INFO, self.ovf.SYSTEM, self.ovf.ITEM]
        for instance in natural_sort(self.item_dict):
            logger.debug("Writing Item(s) with InstanceID %s", instance)
            ovfitem = self.item_dict[instance]
            new_items = ovfitem.generate_items()
            logger.spam("Generated %d items", len(new_items))
            for item in new_items:
                XML.add_child(self.ovf.virtual_hw_section, item, ordering)
        logger.verbose("Updated XML VirtualHardwareSection, now contains %d "
                       "Items representing %d devices",
                       len(self.ovf.virtual_hw_section.findall(self.ovf.ITEM)),
                       len(self.item_dict))

    def find_unused_instance_id(self, start=1):
        """Find the first available ``InstanceID`` number.

        Args:
          start (int): First InstanceID value to consider (disregarding all
            lower InstanceIDs, even if available).
        Returns:
          str: An instance ID that is not yet in use.
        """
        instance = int(start)
        while str(instance) in self.item_dict.keys():
            instance += 1
        logger.debug("Found unused InstanceID %d", instance)
        return str(instance)

    def new_item(self, resource_type, profile_list=None):
        """Create a new OVFItem of the given type.

        Args:
          resource_type (str): String such as 'cpu' or 'harddisk' - used as
            a key to
            :data:`~COT.vm_description.ovf.name_helper.OVFNameHelper1.RES_MAP`
          profile_list (list): Profiles the new item should belong to

        Returns:
          tuple: ``(instance_id, ovfitem)``
        """
        instance = self.find_unused_instance_id()
        ovfitem = OVFItem(self.ovf)
        ovfitem.set_property(self.ovf.INSTANCE_ID, instance, profile_list)
        ovfitem.set_property(self.ovf.RESOURCE_TYPE,
                             self.ovf.RES_MAP[resource_type],
                             profile_list)
        # ovftool freaks out if we leave out the ElementName on an Item,
        # so provide a simple default value.
        ovfitem.set_property(self.ovf.ELEMENT_NAME, resource_type,
                             profile_list)
        self.item_dict[instance] = ovfitem
        ovfitem.modified = True
        logger.info("Created new %s under profile(s) %s, InstanceID is %s",
                    resource_type, profile_list, instance)
        return (instance, ovfitem)

    def delete_item(self, item):
        """Delete the given Item from the hardware.

        Args:
          item (OVFItem): Item to delete
        """
        instance = item.get_value(self.ovf.INSTANCE_ID)
        if self.item_dict[instance] == item:
            del self.item_dict[instance]
        # TODO: error handling - currently a no-op if item not in item_dict

    def clone_item(self, parent_item, profile_list):
        """Clone an OVFItem to create a new instance.

        Args:
          parent_item (OVFItem): Instance to clone from
          profile_list (list): List of profiles to clone into

        Returns:
          tuple: ``(instance_id, ovfitem)``
        """
        instance = self.find_unused_instance_id(start=parent_item.instance_id)
        logger.spam("Cloning existing Item %s with new instance ID %s",
                    parent_item, instance)
        ovfitem = copy.deepcopy(parent_item)

        # Delete any profiles from the parent that we don't need now,
        # otherwise we'll get an error when trying to set the instance ID
        # on our clone due to self-inconsistency (#64).
        for profile in self.ovf.config_profiles:
            if ovfitem.has_profile(profile) and profile not in profile_list:
                ovfitem.remove_profile(profile)

        ovfitem.set_property(self.ovf.INSTANCE_ID, instance, profile_list)
        ovfitem.modified = True
        self.item_dict[instance] = ovfitem
        logger.spam("Added clone of %s under %s, instance is %s",
                    parent_item, profile_list, instance)
        return (instance, ovfitem)

    def item_match(self, item, resource_type, properties, profile_list):
        """Check whether the given item matches the given filters.

        Args:
          item (OVFItem): Item to validate
          resource_type (str): Resource type string like 'scsi' or 'serial'
          properties (dict): Properties and their values to match
          profile_list (list): List of profiles to filter on

        Returns:
          bool: True if the item matches all filters, False if not.
        """
        if resource_type and (self.ovf.RES_MAP[resource_type] !=
                              item.get_value(self.ovf.RESOURCE_TYPE)):
            return False
        if profile_list:
            for profile in profile_list:
                if not item.has_profile(profile):
                    return False
        for (prop, value) in properties.items():
            if item.get_value(prop) != value:
                return False
        return True

    def find_all_items(self, resource_type=None, properties=None,
                       profile_list=None):
        """Find all items matching the given type, properties, and profiles.

        Args:
          resource_type (str): Resource type string like 'scsi' or 'serial'
          properties (dict): Properties and their values to match
          profile_list (list): List of profiles to filter on

        Returns:
          list: Matching OVFItem instances
        """
        items = [self.item_dict[instance] for instance in
                 natural_sort(self.item_dict)]
        filtered_items = []
        if properties is None:
            properties = {}
        for item in items:
            if self.item_match(item, resource_type, properties, profile_list):
                filtered_items.append(item)
        logger.spam("Found %s Items of type %s with properties %s and"
                    " profiles %s", len(filtered_items), resource_type,
                    properties, profile_list)
        return filtered_items

    def find_item(self, resource_type=None, properties=None, profile=None):
        """Find the only OVFItem of the given :attr:`resource_type`.

        Args:
          resource_type (str): Resource type string like 'scsi' or 'serial'
          properties (dict): Properties and their values to match
          profile (str): Single profile ID to search within

        Returns:
          OVFItem: Matching instance, or None

        Raises:
          LookupError: if more than one such Item exists.
        """
        matches = self.find_all_items(resource_type, properties, [profile])
        if len(matches) > 1:
            raise LookupError(
                "Found multiple matching '{0}' Items (instances {1})"
                .format(resource_type, [m.instance_id for m in matches]))
        elif len(matches) == 0:
            return None
        else:
            return matches[0]

    def get_item_count(self, resource_type, profile):
        """Wrapper for :meth:`get_item_count_per_profile`.

        Args:
          resource_type (str): Resource type string like 'scsi' or 'serial'
          profile (str): Single profile identifier string to look up.

        Returns:
          int: Number of items of this type in this profile.
        """
        return (self.get_item_count_per_profile(resource_type, [profile])
                [profile])

    def get_item_count_per_profile(self, resource_type, profile_list):
        """Get the number of Items of the given type per profile.

        Items present under "no profile" will be counted against
        the total for each profile.

        Args:
          resource_type (str): Resource type string like 'scsi' or 'serial'
          profile_list (list): List of profiles to filter on
              (default: apply across all profiles)

        Returns:
          dict: mapping profile strings to the number of items under each
          profile.
        """
        count_dict = {}
        if not profile_list:
            # Get the count under all profiles
            profile_list = self.ovf.config_profiles + [None]
        for profile in profile_list:
            count_dict[profile] = 0
        for ovfitem in self.find_all_items(resource_type):
            for profile in profile_list:
                if ovfitem.has_profile(profile):
                    count_dict[profile] += 1
        for (profile, count) in count_dict.items():
            logger.spam("Profile '%s' has %s %s Item(s)",
                        profile, count, resource_type)
        return count_dict

    def _update_existing_item_profiles(self, resource_type,
                                       count, profile_list):
        """Change profile membership of existing items as needed.

        Helper method for :meth:`set_item_count_per_profile`.

        Args:
          resource_type (str): 'cpu', 'harddisk', etc.
          count (int): Desired number of items
          profile_list (list): List of profiles to filter on
              (default: apply across all profiles)

        Returns:
          tuple: (count_dict, items_to_add, last_item)
        """
        count_dict = self.get_item_count_per_profile(resource_type,
                                                     profile_list)
        items_seen = dict.fromkeys(profile_list, 0)
        last_item = None

        # First, iterate over existing Items.
        # Once we've seen "count" items under a profile, remove all subsequent
        # items from this profile.
        # If we don't have enough items under a profile, add any items found
        # under other profiles to this profile as well.
        for ovfitem in self.find_all_items(resource_type):
            last_item = ovfitem
            for profile in profile_list:
                if ovfitem.has_profile(profile):
                    if items_seen[profile] >= count:
                        # Too many items - remove this one!
                        ovfitem.remove_profile(profile)
                    else:
                        items_seen[profile] += 1
                else:
                    if count_dict[profile] < count:
                        # Add this profile to this Item
                        ovfitem.add_profile(profile)
                        count_dict[profile] += 1
                        items_seen[profile] += 1

        # How many new Items do we need to create in total?
        items_to_add = 0
        for profile in profile_list:
            delta = count - items_seen[profile]
            if delta > items_to_add:
                items_to_add = delta

        return count_dict, items_to_add, last_item

    def _update_cloned_item(self, new_item, new_item_profiles, item_count):
        """Update a cloned item to make it distinct from its parent.

        Helper method for :meth:`set_item_count_per_profile`.

        Args:
          new_item (OVFItem): Newly cloned Item
          new_item_profiles (list): Profiles new_item should belong to
          item_count (int): How many Items of this type (including this
              item) now exist. Used with
              :meth:`COT.platform.Platform.guess_nic_name`

        Returns:
          OVFItem: Updated :param:`new_item`

        Raises:
          NotImplementedError: No support yet for updating ``Address``
          NotImplementedError: If updating ``AddressOnParent`` but the
              prior value varies across config profiles.
          NotImplementedError: if ``AddressOnParent`` is not an integer.
        """
        resource_type = new_item.hardware_type
        address = new_item.get(self.ovf.ADDRESS)
        if address:
            raise NotImplementedError("Don't know how to ensure a unique "
                                      "Address value when cloning an Item "
                                      "of type {0}".format(resource_type))

        address_on_parent = new_item.get(self.ovf.ADDRESS_ON_PARENT)
        if address_on_parent:
            address_list = new_item.get_all_values(self.ovf.ADDRESS_ON_PARENT)
            if len(address_list) > 1:
                raise NotImplementedError("AddressOnParent is not common "
                                          "across all profiles but has "
                                          "multiple values {0}. COT can't "
                                          "handle this yet."
                                          .format(address_list))
            address_on_parent = address_list[0]
            # Currently we only handle integer addresses
            try:
                address_on_parent = int(address_on_parent)
                address_on_parent += 1
                new_item.set_property(self.ovf.ADDRESS_ON_PARENT,
                                      str(address_on_parent),
                                      new_item_profiles)
            except ValueError:
                raise NotImplementedError("Don't know how to ensure a "
                                          "unique AddressOnParent value "
                                          "given base value '{0}'"
                                          .format(address_on_parent))

        if resource_type == 'ethernet':
            # Update ElementName to reflect the NIC number
            element_name = self.ovf.platform.guess_nic_name(item_count)
            new_item.set_property(self.ovf.ELEMENT_NAME, element_name,
                                  new_item_profiles)

        return new_item

    def set_item_count_per_profile(self, resource_type, count, profile_list):
        """Set the number of items of a given type under the given profile(s).

        If the new count is greater than the current count under this
        profile, then additional instances that already exist under
        another profile will be added to this profile, starting with
        the lowest-sequence instance not already present, and only as
        a last resort will new instances be created.

        If the new count is less than the current count under this profile,
        then the highest-numbered instances will be removed preferentially.

        Args:
          resource_type (str): 'cpu', 'harddisk', etc.
          count (int): Desired number of items
          profile_list (list): List of profiles to filter on
              (default: apply across all profiles)
        """
        if not profile_list:
            # Set the profile list for all profiles, including the default
            profile_list = self.ovf.config_profiles + [None]

        count_dict, items_to_add, last_item = \
            self._update_existing_item_profiles(
                resource_type, count, profile_list)

        logger.debug("Creating %d new items", items_to_add)
        while items_to_add > 0:
            # Which profiles does this Item need to belong to?
            new_item_profiles = []
            for profile in profile_list:
                if count_dict[profile] < count:
                    new_item_profiles.append(profile)
                    count_dict[profile] += 1
            if last_item is None:
                logger.notice("No existing items of type %s found. "
                              "Will create new %s from scratch.",
                              resource_type, resource_type)
                (_, new_item) = self.new_item(resource_type, new_item_profiles)
            else:
                (_, new_item) = self.clone_item(last_item, new_item_profiles)
            # Check/update other properties of the clone that should be unique:
            # TODO - we assume that the count is the same across profiles
            new_item = self._update_cloned_item(
                new_item, new_item_profiles, count_dict[new_item_profiles[0]])

            last_item = new_item
            items_to_add -= 1

    def set_value_for_all_items(self, resource_type, prop_name, new_value,
                                profile_list, create_new=False):
        """Set a property to the given value for all items of the given type.

        If no items of the given type exist, will create a new ``Item`` if
        :attr:`create_new` is set to ``True``; otherwise will log a warning
        and do nothing.

        Args:
          resource_type (str): Resource type such as 'cpu' or 'harddisk'
          prop_name (str): Property name to update
          new_value (str): New value to set the property to
          profile_list (list): List of profiles to filter on
              (default: apply across all profiles)
          create_new (bool): Whether to create a new entry if no items
              of this :attr:`resource_type` presently exist.
        """
        ovfitem_list = self.find_all_items(resource_type)
        if not ovfitem_list:
            if not create_new:
                logger.warning("No items of type %s found. Nothing to do.",
                               resource_type)
                return
            logger.notice("No existing items of type %s found. "
                          "Will create new %s from scratch.",
                          resource_type, resource_type)
            (_, ovfitem) = self.new_item(resource_type, profile_list)
            ovfitem_list = [ovfitem]
        for ovfitem in ovfitem_list:
            ovfitem.set_property(prop_name, new_value, profile_list)
        logger.debug("Updated %s %s to %s under profiles %s",
                     resource_type, prop_name, new_value, profile_list)

    def set_item_values_per_profile(self, resource_type, prop_name, value_list,
                                    profile_list, default=None):
        """Set value(s) for a property of multiple items of a type.

        Args:
          resource_type (str): Device type such as 'harddisk' or 'cpu'
          prop_name (str): Property name to update
          value_list (list): List of values to set (one value per item of the
              given :attr:`resource_type`)
          profile_list (list): List of profiles to filter on
              (default: apply across all profiles)
          default (str): If there are more matching items than entries in
              :attr:`value_list`, set extra items to this value
        """
        if profile_list is None:
            profile_list = self.ovf.config_profiles + [None]
        for ovfitem in self.find_all_items(resource_type):
            if len(value_list):
                new_value = value_list.pop(0)
            else:
                new_value = default
            for profile in profile_list:
                if ovfitem.has_profile(profile):
                    ovfitem.set_property(prop_name, new_value, [profile])
            logger.info("Updated %s property %s to %s under %s",
                        resource_type, prop_name, new_value, profile_list)
        if len(value_list):
            logger.warning("After scanning all known %s Items, not all "
                           "%s values were used - leftover %s",
                           resource_type, prop_name, value_list)
