#!/usr/bin/env python
#
# item.py - OVFItem class
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

"""Module for working with individual hardware elements in an OVF.

Represents all variations of a given hardware ``Item`` amongst different
hardware configuration profiles.

**Functions**

.. autosummary::
  :nosignatures:

  list_union

**Classes and Exceptions**

.. autosummary::
  :nosignatures:

  OVFItem
  OVFItemDataError
"""

import re
import logging
import xml.etree.ElementTree as ET

from COT.data_validation import natural_sort, ValueUnsupportedError
from COT.xml_file import XML

from COT.ovf.name_helper import name_helper

logger = logging.getLogger(__name__)


def list_union(*lists):
    """Get union of lists."""
    result = []
    for l in lists:
        result.extend([x for x in l if x not in result])
    logger.debug("Union of %s is %s", lists, result)
    return result


class OVFItemDataError(Exception):
    """Data to be added to an :class:`OVFItem` conflicts with existing data."""


class OVFItem(object):
    """Helper class for :class:`OVF`.

    Represents all variations of a given hardware ``Item`` amongst different
    hardware configuration profiles.

    In essence, it is:

    * a dict of ``Item`` properties (indexed by element name)
    * each of which is a dict of sets of profiles (indexed by element value)
    """

    # Magic strings
    ATTRIB_KEY_SUFFIX = " {Item attribute}"
    ELEMENT_KEY_SUFFIX = " {custom element}"

    def __init__(self, ovf, item=None):
        """Create a new OVFItem with contents based on the given Item element.

        :param OVF ovf: OVF instance that owns the Item (optional)
        :param xml.etree.ElementTree.Element item: 'Item' element (optional)
        """
        self.ovf = ovf
        if ovf is not None:
            self.name_helper = ovf
        else:
            self.name_helper = name_helper(1.0)
        self.properties = {}
        """Dict of dicts. properties[name][value] = (profile1, profile2)."""
        self.modified = False
        self.NS = self.RASD   # default for most item types
        if item is not None:
            self.add_item(item)

    def __str__(self):
        """Get human-readable string representation."""
        ret = "OVFItem:\n"
        for name in sorted(self.property_names):
            ret += "  " + name + "\n"
            for value in sorted(self.property_values(name)):
                ret += "    {0:20} : {1}\n".format(
                    str(value), sorted(self.property_profiles(name, value)))
        return ret

    def __getattr__(self, name):
        """Transparently pass attribute lookups off to OVF/OVFNameHelper."""
        # Don't pass 'special' attributes through to the helper
        if re.match(r"^__", name):
            raise AttributeError("'OVFItem' object has no attribute '{0}'"
                                 .format(name))
        # Pass through to designated helper
        return getattr(self.name_helper, name)

    @property
    def property_names(self):
        """List of names of all properties known to this OVFItem."""
        return list(self.properties.keys())

    def property_values(self, name):
        """Get list of values known for a given property name."""
        return list(self.properties[name].keys())

    def property_profiles(self, name, value):
        """Get set of profiles associated with a property name and value."""
        return self.properties[name][value]

    def all_profiles(self, name, default=None):
        """Superset of all profiles for which this name has a value."""
        value_dict = self.properties.get(name, None)
        if not value_dict:
            return default
        return set.union(*value_dict.values())

    def add_item(self, item):
        """Add the given ``Item`` element to this OVFItem.

        :param xml.etree.ElementTree.Element item: XML ``Item`` element
        :raise OVFItemDataError: if the new Item conflicts with existing data
          already in the OVFItem.
        """
        logger.debug("Adding new %s", item.tag)
        self.NS = self.name_helper.namespace_for_item_tag(item.tag)
        if not self.NS:
            raise ValueUnsupportedError("item",
                                        item.tag,
                                        "Item, StorageItem, EthernetPortItem")

        profiles = set(item.get(self.ITEM_CONFIG, "").split())
        # Store any attributes of the Item itself:
        for (attrib, value) in item.attrib.items():
            if attrib == self.ITEM_CONFIG:
                continue
            attrib_string = attrib + self.ATTRIB_KEY_SUFFIX
            self.set_property(attrib_string, value, profiles, overwrite=False)

        # Store any child elements of the Item.
        # We save the ElementName and Description elements for last because
        # they may include references to the VirtualQuantity, ResourceSubType,
        # and/or Connection entries, which we won't know until we process them.
        children = list(item)
        name_child = next(
            (child for child in children if
             XML.strip_ns(child.tag) == self.ELEMENT_NAME),
            None)
        desc_child = next(
            (child for child in children if
             XML.strip_ns(child.tag) == self.ITEM_DESCRIPTION),
            None)
        if name_child is not None:
            children.remove(name_child)
            children.append(name_child)
        # Description is *after* name because it may reference name
        if desc_child is not None:
            children.remove(desc_child)
            children.append(desc_child)

        for child in children:
            tag = XML.strip_ns(child.tag)
            if tag not in self.ITEM_CHILDREN:
                # Non-standard elements may not follow the standard rules -
                # for example, VMware OVF extensions may have multiple
                # vmw:Config elements, each distinguished by its vmw:key attr.
                # Rather than try to guess how these items do or do not match,
                # we simply store the whole item
                self.set_property((ET.tostring(child).decode().strip() +
                                   self.ELEMENT_KEY_SUFFIX),
                                  ET.tostring(child).decode(),
                                  profiles, overwrite=False)
                continue
            # Store the value of this element:
            self.set_property(tag, child.text, profiles, overwrite=False)
            # Store any attributes of this element
            for (attrib, value) in child.attrib.items():
                attrib_string = tag + "_attrib_" + attrib
                self.set_property(attrib_string, value, profiles,
                                  overwrite=False)

        self.modified = True
        logger.debug("Added %s - new status:\n%s", item.tag, str(self))
        self.validate()

    def value_add_wildcards(self, name, value, profiles):
        """Add wildcard placeholders to a string that may need updating."""
        # If the ElementName or Description references the VirtualQuantity,
        # Connection, or ResourceSubType, replace that reference with a
        # placeholder that we can regenerate at output time. That way, if the
        # VirtualQuantity or ResourceSubType changes, these can change too.
        if name == self.ELEMENT_NAME or name == self.ITEM_DESCRIPTION:
            vq_val = self.get_value(self.VIRTUAL_QUANTITY, profiles)
            if vq_val is not None:
                value = re.sub(vq_val, "_VQ_", value)
            rst_val = self.get_value(self.RESOURCE_SUB_TYPE, profiles)
            if rst_val is not None:
                if isinstance(rst_val, tuple):
                    rst_val = "/".join(rst_val)
                value = re.sub(rst_val, "_RST_", value)
            conn_val = self.get_value(self.CONNECTION, profiles)
            if conn_val is not None:
                value = re.sub(conn_val, "_CONN_", value)
        # Similarly, if the Description references the ElementName...
        if name == self.ITEM_DESCRIPTION:
            en_val = self.get_value(self.ELEMENT_NAME, profiles)
            if en_val is not None:
                value = re.sub(en_val, "_EN_", value)
        return value

    def value_replace_wildcards(self, name, value, profiles):
        """Replace wildcards with actual values."""
        if not value:
            return value
        if name == self.ELEMENT_NAME or name == self.ITEM_DESCRIPTION:
            # To regenerate text that depends on these values:
            rst_val = self._get_value(self.RESOURCE_SUB_TYPE, profiles)
            if isinstance(rst_val, tuple):
                rst_val = "/".join(rst_val)
            vq_val = self._get_value(self.VIRTUAL_QUANTITY, profiles)
            conn_val = self._get_value(self.CONNECTION, profiles)
            if rst_val is not None:
                value = re.sub("_RST_", str(rst_val), str(value))
            if vq_val is not None:
                value = re.sub("_VQ_", str(vq_val), str(value))
            if conn_val is not None:
                value = re.sub("_CONN_", str(conn_val), str(value))
        if name == self.ITEM_DESCRIPTION:
            en_val = self._get_value(self.ELEMENT_NAME, profiles)
            if en_val is not None:
                value = re.sub("_EN_", str(en_val), str(value))
        return value

    def _set_new_property(self, name, value, profiles):
        """Helper for :meth:`set_property`. Create a new property entry."""
        if not value:
            return

        if None in profiles:
            self.properties[name] = {value: set([None])}
        else:
            self.properties[name] = {value: profiles}
        self.modified = True

    def _set_existing_property(self, name, value, profiles, overwrite):
        """Helper for :meth:`set_property`. Update an existing property."""
        for (known_value, profile_set) in list(self.properties[name].items()):
            if not overwrite and profile_set.intersection(profiles):
                raise OVFItemDataError(
                    "Tried to set value:\n'{0}'\nfor property\n'{1}'\n"
                    "under profile(s) {2} but already had value:\n'{3}'\n"
                    "for this property under profile(s) {4}"
                    .format(value, name, profiles,
                            known_value,
                            profile_set.intersection(profiles)))
            new_set = profile_set.copy()

            if known_value != value:
                # Our profiles should not use this old value
                new_set -= profiles
            elif None in profile_set:
                # No need to add ourselves, we're already covered
                # implicitly by the default
                pass
            else:
                new_set |= profiles

            if new_set != profile_set:
                self.modified = True
                if not new_set:
                    logger.debug("No longer any profiles with value %s",
                                 known_value)
                    del self.properties[name][known_value]
                else:
                    self.properties[name][known_value] = new_set

        if value and value not in self.property_values(name):
            self.properties[name][value] = profiles
            self.modified = True
        elif not self.properties[name]:
            logger.debug("No longer any values saved for %s", name)
            del self.properties[name]
            self.modified = True

    def set_property(self, name, value, profiles=None, overwrite=True):
        """Store the value and profiles associated with it for the given name.

        :param str name: Property name
        :param str value: Value associated with :attr:`name`
        :param profiles: If ``None``, set for all profiles currently
          known to this item, else set only for the given list of profiles.
        :type profiles: list[str]
        :param boolean overwrite: Whether to permit overwriting of existing
          value set in this item.

        :raise OVFItemDataError: if a value is already defined and would be
          overwritten, unless :attr:`overwrite` is ``True``
        """
        # A ResourceSubType in the XML can be a single value or a
        # space-separated list of values. Internally, we'll store it as a
        # tuple, and re-join it later if needed.
        # pylint: disable=redefined-variable-type
        if name == self.RESOURCE_SUB_TYPE:
            if not value:
                # empty string -> empty list, not ['']
                value = []
            if isinstance(value, str):
                value = value.split(" ")  # pylint: disable=no-member
            # lists can't be used as hash keys, tuples can
            if isinstance(value, list):
                value = tuple(value)
        else:
            # Just to be safe...
            value = str(value)

        if name == self.RESOURCE_TYPE:
            self.NS = self.name_helper.namespace_for_resource_type(value)

        if not profiles:
            # Profiles not specified.
            # 1) If this property was already defined for a specific set of
            #    profiles, then change the value for all of these profiles.
            # 2) If this property was not defined previously, then set the
            #    value for all profiles (the magic set([None]))
            profiles = self.all_profiles(name, set([None]))
        profiles = set(profiles)

        value = self.value_add_wildcards(name, value, profiles)
        logger.debug("Setting %s to %s under profiles %s",
                     name, value, profiles)
        if name not in self.properties:
            self._set_new_property(name, value, profiles)
        else:
            self._set_existing_property(name, value, profiles, overwrite)

        if self.modified:
            self.validate()

    def add_profile(self, new_profile, from_item=None):
        """Add a new profile to this item.

        :param str new_profile: Profile name to add
        :param OVFItem from_item: Item to inherit properties from. If unset,
          this defaults to ``self``.
        """
        if self.has_profile(new_profile):
            logger.error("Profile %s already exists under %s!",
                         new_profile, self)
            return
        if from_item is None:
            from_item = self
        logger.debug("Adding profile %s to item %s from item %s",
                     new_profile,
                     self.properties.get(self.INSTANCE_ID,
                                         "<unknown instance>"),
                     from_item.properties[self.INSTANCE_ID])
        p_set = set([new_profile])
        for name in from_item.property_names:
            found = False
            if not from_item.properties[name]:
                logger.debug("No values stored for name %s - not cloning it",
                             name)
                continue
            for (value, profiles) in from_item.properties[name].items():
                if (None in profiles or
                        len(from_item.property_values(name)) == 1):
                    self.set_property(name, value, p_set)
                    found = True
                    break
            if not found:
                raise RuntimeError(
                    "Not sure which value to clone for {0}: {1}"
                    .format(name, from_item.properties[name].items()))
        self.modified = True
        self.validate()

    def remove_profile(self, profile, split_default=True):
        """Remove all trace of the given profile from this item.

        :param str profile: Profile name to remove
        :param bool split_default: If False, do not split out 'default'
          profile items to specifically exclude this profile. Used when the
          profile being removed will no longer exist anywhere and so
          'default' will continue to exclude this profile.
        """
        if not self.has_profile(profile):
            logger.error("Requested deletion of profile '%s' but it is "
                         "not present under %s!", profile, self)
            return
        logger.debug("Removing profile %s from item %s",
                     profile, self.properties[self.INSTANCE_ID])
        p_set = set([profile])
        for name in self.property_names:
            for (value, profiles) in list(self.properties[name].items()):
                profiles -= p_set
                # Convert "any profile" to a list of all profiles minus
                # this one and any profiles already set elsewhere
                if None in profiles and split_default:
                    logger.debug("Profile contains 'any profile'; "
                                 "fixing it up")
                    profiles.update(self.ovf.config_profiles)
                    profiles.discard(None)
                    profiles.discard(profile)
                    # Discard all profiles set elsewhere
                    for (v, p) in list(self.properties[name].items()):
                        if v == value:
                            continue
                        profiles -= p
                    logger.debug("profiles are now: %s", profiles)
                if not profiles:
                    logger.verbose("No more profiles for value %s, %s",
                                   name, value)
                    del self.properties[name][value]
        self.modified = True
        self.validate()

    def get(self, tag):
        """Get the dict associated with the given XML tag, if any.

        :param str tag: XML tag to look up
        :rtype: dict
        :return: Dictionary of values associated with this tag (TODO?)
        """
        return self.properties.get(tag, None)

    def _get_value(self, tag, profiles=None):
        """Get internal value string for the given tag.

        Unlike :meth:`get_value`, this retains any internal modifications of
        the value string such as wildcard tags and temporary substitutions.

        If the tag does not exist under these profiles, or
        the tag values differ across the profiles, returns ``None``.

        :param str tag: Tag to retrieve value for
        :param profiles: set of profile names, or None
        :type profiles: set of strings
        :return: Value, default value, or ``None``, unsanitized.
        """
        if profiles is not None:
            profiles = set(profiles)
        val_dict = self.properties.get(tag, {})
        if profiles is None:
            if len(val_dict) == 1:
                return list(val_dict.keys())[0]
            else:
                return None
        # A case we need to handle:
        # {'1': set([None])
        #  '4': set(['x'])
        # get_value([None, 'y', 'z'])  --> return '1'
        # get_value([None, 'x']) --> return None
        # We have to recognize that y and z are implicit in None but z is not.
        default_val = None
        for (val, prof) in val_dict.items():
            if prof.issuperset(profiles):
                return val
            if None in prof:
                default_val = val
            elif not prof.isdisjoint(profiles):
                return None
        return default_val

    def get_value(self, tag, profiles=None):
        """Get the value for the given tag under the given profiles.

        If the tag does not exist under these profiles, or the
        tag values differ across the profiles, returns ``None``.

        :param str tag: Tag to retrieve value for
        :param profiles: set of profile names, or None
        :type profiles: set of strings
        :return: Value string or list, or ``None``
        """
        val = self._get_value(tag, profiles)
        val = self.value_replace_wildcards(tag, val, profiles)
        # Sanity check
        if tag == self.ELEMENT_NAME or tag == self.ITEM_DESCRIPTION:
            if val and re.search(r"_RST_|_VQ_|_CONN_|_EN_", val):
                raise OVFItemDataError("Unreplaced wildcard in value "
                                       "for {0} profiles {1}:\n{2}\n{3}"
                                       .format(tag, profiles, val, self))
        return val

    def get_all_values(self, tag):
        """Get the list of all value strings for the given tag.

        :param str tag: Tag to retrieve value for
        :rtype: list
        """
        if tag == self.RESOURCE_SUB_TYPE:
            # ResourceSubType values may themselves be tuples
            return list_union(*self.properties.get(tag, {}).keys())
        return list(self.properties.get(tag, {}).keys())

    def validate(self):
        """Verify that the OVFItem describes a valid set of items.

        Also clean up any oddities (like a property value assigned to
        'all profiles' and also redundantly to a specific profile).

        :raise RuntimeError: if validation fails and self-repair is impossible.
        """
        # An OVFItem must describe only one InstanceID
        # All Items with a given InstanceID must have the same ResourceType
        for name in [self.INSTANCE_ID, self.RESOURCE_TYPE]:
            if len(self.properties.get(name, {})) > 1:
                raise RuntimeError("OVFItem illegally contains multiple {0} "
                                   "values: {1}"
                                   .format(name,
                                           self.property_values(name)))
        for (name, value_dict) in self.properties.items():
            set_so_far = set()
            for profile_set in value_dict.values():
                if None in profile_set and len(profile_set) > 1:
                    logger.verbose("Profile set %s contains redundant info; "
                                   "cleaning it up now...", profile_set)
                    # Clean up...
                    profile_set.clear()
                    profile_set.add(None)
                # Make sure the profile sets are mutually exclusive
                inter = set_so_far.intersection(profile_set)
                if inter:
                    raise RuntimeError("OVFItem illegally contains duplicate "
                                       "profiles %s under %s: %s",
                                       inter, name, value_dict)
                set_so_far |= profile_set

    def has_profile(self, profile):
        """Check if this Item exists under the given profile.

        :param str profile: Profile name
        :rtype: boolean
        """
        profiles = self.all_profiles(self.INSTANCE_ID)
        if profiles is None:
            return False
        if profile in profiles:
            return True
        elif None in profiles and profile in self.ovf.config_profiles:
            return True
        return False

    def get_nonintersecting_set_list(self):
        """Identify the minimal non-intersecting set of profiles.

        :return: List of profile-set strings.
        """
        set_list = []
        for name in self.property_names:
            for (_, new_set) in list(self.properties[name].items()):
                new_set_list = []
                for existing_set in set_list:
                    # If the sets are identical or do not intersect, do nothing
                    if (new_set == existing_set or
                            not new_set.intersection(existing_set)):
                        new_set_list.append(frozenset(existing_set))
                        continue
                    # Otherwise, need to re-partition!
                    set_a = existing_set.difference(new_set)
                    new_set_list.append(frozenset(set_a))

                    set_b = existing_set.intersection(new_set)
                    new_set_list.append(frozenset(set_b))

                    new_set = new_set.difference(existing_set)

                new_set_list.append(frozenset(new_set))
                # Remove duplicate and empty entries
                set_list = [x for x in set(new_set_list) if x]

        logger.debug("Final set list is %s", set_list)

        # Construct a list of profile strings
        set_string_list = []
        for final_set in set_list:
            if None in final_set:
                set_string_list.append("")
            else:
                set_string_list.append(" ".join(natural_sort(final_set)))
        set_string_list = natural_sort(set_string_list)

        logger.debug("set string list: %s", set_string_list)

        return set_string_list

    def generate_items(self):
        """Get a list of Item XML elements derived from this object's data.

        :rtype: list[xml.etree.ElementTree.Element]
        """
        set_string_list = self.get_nonintersecting_set_list()

        # Now, construct the Items
        item_tag = self.name_helper.item_tag_for_namespace(self.NS)
        child_ordering = [self.NS + i for i in self.ITEM_CHILDREN]
        item_list = []
        for set_string in set_string_list:
            if not set_string:
                # no config profile
                item = ET.Element(item_tag)
                final_set = set([None])
                set_string = '<generic>'
            else:
                item = ET.Element(item_tag, {self.ITEM_CONFIG: set_string})
                final_set = set(set_string.split())
            logger.debug("set string: %s; final_set: %s",
                         set_string, final_set)
            for name in sorted(self.property_names):
                val = self.get_value(name, final_set)
                if not val:
                    logger.info("No value defined for attribute '%s' "
                                "under profile set '%s' for instance %s",
                                name, set_string,
                                self.get_value(self.INSTANCE_ID))
                    continue
                # Convert list of ResourceSubType values to a space-separated
                # list for output
                if name == self.RESOURCE_SUB_TYPE:
                    val = " ".join(val) if val else None

                # Is this an attribute, a child, or a custom element?
                attrib_match = re.match(r"(.*)" + self.ATTRIB_KEY_SUFFIX, name)
                if attrib_match:
                    attrib_string = attrib_match.group(1)
                child_attrib = re.match(r"(.*)_attrib_(.*)", name)
                custom_elem = re.match(r"(.*)" + self.ELEMENT_KEY_SUFFIX, name)
                if attrib_match:
                    item.set(attrib_string, val)
                elif child_attrib:
                    child = XML.set_or_make_child(
                        item,
                        child_attrib.group(1),
                        None,
                        ordering=child_ordering,
                        known_namespaces=self.NSM.values())
                    child.set(child_attrib.group(2), val)
                elif custom_elem:
                    # Recreate the element in question and append it
                    item.append(ET.fromstring(val))
                else:
                    # Children of Item must be in sorted order
                    XML.set_or_make_child(item, self.NS + name, val,
                                          ordering=child_ordering,
                                          known_namespaces=self.NSM.values())
            logger.debug("Item is:\n%s", ET.tostring(item))
            item_list.append(item)

        return item_list
