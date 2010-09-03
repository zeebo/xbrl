from glob import glob
from pprint import pprint
import xml.etree.ElementTree as etree
import re
import sys

def parse_map(file):
    events = "start", "start-ns", "end-ns"
    root = None
    ns_map = []
    for event, elem in etree.iterparse(file, events):
        if event == "start-ns":
            x, y = elem[0], elem[1].decode()
            ns_map.append((x, y))
        elif event == "end-ns":
            ns_map.pop()
        elif event == "start":
            if root is None:
                root = elem
            elem.ns_map = dict(ns_map)
    return etree.ElementTree(root)

def get_keys(dic, value):
  keys = [k for k, v in dic.items() if v == value]
  
  if len(keys) == 0:
    raise ValueError('Value not found')
  else:
    return keys[0]

def get_tag(child):
  if not hasattr(child, 'ns_map'):
    return child.tag
  
  pattern = re.compile(
    r'^'      #beginning of string
    r'\{'     #match a single {
    r'(.*?)'  #grab the namespace url
    r'\}'     #match a sing }
    r'(.*?)'  #match the attribute name
    r'$'      #end of string
  )
  
  ns_url, element = pattern.search(child.tag).groups()
  if ns_url in child.ns_map.values():
    key = get_keys(child.ns_map, ns_url)
    
    if len(key) == 0:
      return element
    
    return '%s:%s' % (key, element)
  
  return child.tag

def tree_print(element, indent=0):
  if indent == 0:
    print(get_tag(element))
  for child in element:
    print('%s%s%s' % ('| '*indent, '|-', get_tag(child)))
    if len(child) > 0:
      tree_print(child, indent+1)

def parse_directory(directory):
  xmls = {}
  for fname in glob("isdr/*"):
    with open(fname) as fobj:
      xmls[fname] = parse_map(fobj)
  
  return xmls

xmls = parse_directory('isdr/*')
etree.QName("http://www.xbrl.org/2003/linkbase", tag='lol')

list(xmls.values())[0].write(sys.stdout)