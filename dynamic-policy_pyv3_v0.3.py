#!/usr/bin/env python

from xml.dom import minidom
from xml.etree import ElementTree as ET
# from xml.etree.ElementTree import Element, SubElement, Comment, tostring

import fileinput
import getpass
import hashlib
import netaddr
import optparse
import os
import re
import sys
import time
import shutil
import yaml
from jnpr.junos import Device
from jnpr.junos.utils.config import Config

# location for file location
feed_location = '/var/www/html/'
temp_location = '/var/tmp/'


def yaml_loader(filepath):
    """Loads a yaml file"""
    with open(filepath, "r") as file_descriptor:
        data = yaml.load(file_descriptor)
    return(data)


def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def modify_file(file_name, pattern, value=""):
    fh = fileinput.input(file_name, inplace=True)
    for line in fh:
        replacement = line + value
        line = re.sub(pattern, replacement, line)
        sys.stdout.write(line)
    fh.close()


def delete_line(pattern, t_Feed):
    readFile = open(t_Feed, 'r')
    lines = readFile.readlines()
    readFile.close()

    writeFile = open(t_Feed, 'w')

    for line in lines:
        if line != pattern+"\n":
            # print "Not found--->" + line
            writeFile.write(line)

    writeFile.close()


def update_manifest(feedname, t_Feed, t_Manifest):
    ts = int(time.time())
    print("Modifying total number of objects for  -> " + feedname)
    with open(t_Feed, 'r') as feed:
        count = sum(1 for line in feed) - 5
        print("Revised address count of       -> " + str(count) + "\n")
    feed.close()

    tree = ET.parse(t_Manifest)
    root = tree.getroot()

    for feed in root.iter('feed'):
        name = feed.get('name')
        # print(name)
        if name == str(feedname):
            feed.set('data_ts', str(ts))
            feed.set('objects', str(count))
        tree.write(t_Manifest)


def create_manifest_entry(t_Manifest, feedname):
    ts = str(int(time.time()))
    print("Inserting new feed into manifest file located at " + feed_location)

    tree = ET.parse(t_Manifest)
    root = tree.getroot()

    category = root.find('category')
    feed = ET.SubElement(category, 'feed',
                         dict(data_ts=ts, name=feedname, objects="0",
                              options="", types="ip_addr ip_range",
                              version=feedname))
    data = ET.SubElement(feed, 'data')
    url = ET.SubElement(data, 'url')
    url.text = '/'

    text = (prettify(root))
    cleantext = "".join([s for s in text.strip().splitlines(True)
                        if s.strip()])

    with open(t_Manifest, 'w') as file:
        file.write(cleantext)


def copy_feed_to_tempFeed(o_Feed, t_Feed):
    shutil.copyfile(o_Feed, t_Feed)
    readFile = open(t_Feed)
    lines = readFile.readlines()
    readFile.close()
    writeFile = open(t_Feed, 'w')
    writeFile.writelines([item for item in lines[:-1]])
    writeFile.close()


def copy_tempFeed_to_feed(o_Feed, t_Feed):
    shutil.copyfile(t_Feed, o_Feed)


def copy_tempManifest_to_Manifest(o_manifest, t_Manifest):
    shutil.copyfile(t_Manifest, o_manifest)


def copy_Manifest_to_tempManifest(o_manifest, t_Manifest):
    shutil.copyfile(o_manifest, t_Manifest)


def create_newFeed(Blank_Feed, name):
    shutil.copyfile(Blank_Feed, name)


def calculate_md5(t_Feed):
    with open(t_Feed, "r") as file:
        data = file.read()
        md5_returned = hashlib.md5(data.encode('utf-8')).hexdigest()
        file.close()

    writeFile = open(t_Feed, 'a')
    writeFile.write(md5_returned)
    writeFile.close()


def checkRequiredArguments(opts, parser):
    if len(sys.argv) <= 1:
        return False
    return True


def setup():
    pass


def add_entry(f_loc, t_loc, feedname, ip_address):
    feed = f_loc + str(feedname)
    tempFeed = t_loc + str(feedname)
    manifest = f_loc + 'manifest.xml'
    tempManifest = t_loc + 'manifest.xml'
    copy_feed_to_tempFeed(feed, tempFeed)
    copy_Manifest_to_tempManifest(manifest, tempManifest)
    ip = netaddr.IPNetwork(ip_address)
    address = ip.ip
    size = ip.size
    adj_size = size - 1
    value = ip.value
    print("\nAdding address of              -> " + str(ip_address) +
          " (including " + str(adj_size) + " subequent hosts)")

    print("\n\n IP address is {};  IP Size is {}; IP Valuse is {}; IP Networks is {} \n\n".format(address, size, value, ip.network))

    if adj_size == 0:
        newentry = '{"1":' + str(value) + '}'
    else:
        newentry = '{"2":[' + str(value) + ', ' + str(adj_size) + ']}'
    # print(newentry)
    modify_file(tempFeed, '#add', newentry)
    calculate_md5(tempFeed)
    update_manifest(feedname, tempFeed, tempManifest)
    copy_tempFeed_to_feed(feed, tempFeed)
    copy_tempManifest_to_Manifest(manifest, tempManifest)

def del_entry(f_loc, t_loc, feedname, ip_address):
    feed = f_loc + str(feedname)
    tempFeed = t_loc + str(feedname)
    manifest = f_loc + 'manifest.xml'
    tempManifest = t_loc + 'manifest.xml'
    copy_feed_to_tempFeed(feed, tempFeed)
    copy_Manifest_to_tempManifest(manifest, tempManifest)
    ip = netaddr.IPNetwork(ip_address)
    address = ip.ip   # assigned but never used
    size = ip.size
    adj_size = size - 1
    value = ip.value
    print("\nRemoving address of            -> " + str(ip_address)
          + " (including " + str(adj_size) + " subequent hosts)")

    print("\n\n IP address is {};  IP Size is {}; IP Valuse is {} \n\n".format(address, size, value))

    if adj_size == 0:
        oldline = '{"1":' + str(value) + '}'
    else:
        oldline = '{"2":[' + str(value) + ', ' + str(adj_size) + ']}'
    delete_line(oldline, tempFeed)

    calculate_md5(tempFeed)
    update_manifest(feedname, tempFeed, tempManifest)
    copy_tempFeed_to_feed(feed, tempFeed)
    copy_tempManifest_to_Manifest(manifest, tempManifest)


def list_entry(f_loc, feedname):
    feed = f_loc + str(feedname)

    pattern_network = '{"(\d+)":\[\d+, \d+\]}'
    pattern_host = '{"(\d+)":\d+}'
    pattern_ip_network = '{"\d+":\[(\d+), \d+]}'
    pattern_ip_host = '{"\d+":(\d+)}'
    pattern_range = '\d+":\[\d+, (\d+)]}'

    with open(feed, 'r') as file:
        lines = file.readlines()

    for line in lines:
        host = re.search(pattern_host, line)
        network = re.search(pattern_network, line)
        if host:
            ip = str(netaddr.IPAddress(re.findall(pattern_ip_host,
                                                  line)[0]))
            print("Host entry:    " + ip)

        elif network:
            # ip = re.findall(pattern_ip_network, line)[0]
            ip = str(netaddr.IPAddress(re.findall(pattern_ip_network,
                                                  line)[0]))
            range = re.findall(pattern_range, line)[0]
            print("Network Entry: " + ip + " (+" + range + " hosts)")


def auto_task():
    pass


def new_feed(f_loc, t_loc, feedname):
    name = str(feedname)
    feed = f_loc + str(feedname)
    feed_template = f_loc + 'Feed'
    manifest = f_loc + 'manifest.xml'
    tempManifest = t_loc + 'manifest.xml'
    copy_Manifest_to_tempManifest(manifest, tempManifest)
    print(name)
    create_newFeed(feed_template, feed)
    create_manifest_entry(tempManifest, name)
    copy_tempManifest_to_Manifest(manifest, tempManifest)
    # print "Completed, add the following line to your SRX to accept feed:\n
    #         set security dynamic-address address-name "+name+
    #         " profile category IPFilter feed "+name
    username = input("Please enter your SRX Username:")
    password = getpass.getpass()
    srx_list = 'srx-list'
    srxs = open(srx_list, 'r')
    for srx in srxs:
        print("Logging into SRX "+srx)
        login = str(srx)
        dev = Device(host=login, user=username, password=password)
        dev.open()
        dev.timeout = 300
        cu = Config(dev)
        set_cmd = 'set security dynamic-address address-name ' + name + \
                  ' profile category IPFilter feed '+name
        cu.load(set_cmd, format='set')
        print("Applying changes, please wait....")
        cu.commit()
        dev.close()


def drop_feed(f_loc, t_loc, feedname):
    pass


def main():
    base_dir = os.getcwd()

    parser = optparse.OptionParser()
    group1 = optparse.OptionGroup(parser, 'Mutually Exclusive Options')
    group2 = optparse.OptionGroup(parser, 'Aadditional Options')
    group1.add_option('--conf', dest='conf_file', help='YAML input file name', metavar="CONF_FILE", default="undefined")
    group1.add_option('-a', '--add', dest='a', help='Add ip entry to FEED (Requires --feed and --ip)', default=False, action="store_true")
    group1.add_option('-d', '--del', dest='d', help='Delete IP entry from FEED (Requires --feed and --ip)', default=False, action="store_true")
    group1.add_option('-l', '--list', dest='l', help='List all of the IP addresses in the FEED (Requires --feed)', default=False, action="store_true")
    group1.add_option('-s', '--setup', dest='s', help='Copy files to the correct location', default=False, action="store_true")
    group1.add_option('--auto', dest='auto', help='Add IP addresses from failed Authentication to FEED', default=False, action="store_true")
    group1.add_option('--new', dest='new_feed', help='Create a New Feed and add to SRX (Requires --feed)', default=False, action="store_true")
    group1.add_option('--drop', dest='drop_feed', help='Drop an Existing Feed and remove from SRX (Requires --feed)', default=False, action="store_true")
    # below are required depending on above actions
    group2.add_option('-f', '--feed', dest='feed', help='Name of the FEED', metavar="FEED", default="undefined")
    group2.add_option('-i', '--ip', dest='ip_addr', help='IP Address', metavar="IP ADDRESS", default="undefined")
    parser.add_option_group(group1)
    parser.add_option_group(group2)
    (options, args) = parser.parse_args()
    if not checkRequiredArguments(options, args):
        parser.print_help()
        sys.exit()

    if options.conf_file is not None:
        config_file = os.path.join(base_dir, "dynamic-policy.conf")
    else:
        config_file = options.conf_file
    configdata = yaml_loader(config_file)

    """ process the YAML file incase of changes to variable and then """
    if options.s:
        setup(feed_location, temp_location)
    elif (options.a and (options.feed is not None)):
        add_entry(feed_location, temp_location, options.feed, options.ip_addr)
    elif (options.d and (options.feed is not None)):
        del_entry(feed_location, temp_location, options.feed, options.ip_addr)
    elif (options.l and (options.feed is not None)):
        list_entry(feed_location, options.feed)
    elif (options.auto and (options.feed is not None)):
        auto_task()
    elif (options.new_feed and (options.feed is not None)):
        new_feed(feed_location, temp_location, options.feed)
    elif (options.drop_feed and (options.feed is not None)):
        drop_feed(feed_location, temp_location, options.feed)


if __name__ == '__main__':
    main()
