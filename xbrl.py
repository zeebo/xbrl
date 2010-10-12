from glob import glob
from pprint import pprint
import xml.etree.ElementTree as etree
import re
import sys

def parse_xmlns(file):
    events = "start", "start-ns"
    root = None
    ns_map = []
    for event, elem in etree.iterparse(file, events):
        if event == "start-ns":
            ns_map.append(elem)
        elif event == "start":
            if root is None:
                root = elem
            for prefix, uri in ns_map:
                elem.set("xmlns:" + prefix, uri)
            ns_map = []
    return etree.ElementTree(root)

def fixup_element_prefixes(elem, uri_map, memo):
    def fixup(name):
        try:
            return memo[name]
        except KeyError:
            if name[0] != "{":
                return
            uri, tag = name[1:].split("}")
            if uri in uri_map:
                new_name = uri_map[uri] + ":" + tag
                memo[name] = new_name
                return new_name
    # fix element name
    name = fixup(elem.tag)
    if name:
        elem.tag = name
    # fix attribute names
    for key, value in elem.items():
        name = fixup(key)
        if name:
            elem.set(name, value)
            del elem.attrib[key]

def fixup_xmlns(elem, maps=None):
    if maps is None:
        maps = [{}]

    # check for local overrides
    xmlns = {}
    for key, value in elem.items():
        if key[:6] == "xmlns:":
            xmlns[value] = key[6:]
    if xmlns:
        uri_map = maps[-1].copy()
        uri_map.update(xmlns)
    else:
        uri_map = maps[-1]

    # fixup this element
    fixup_element_prefixes(elem, uri_map, {})

    # process elements
    maps.append(uri_map)
    for elem in elem:
        fixup_xmlns(elem, maps)
    maps.pop()


def write_xmlns(elem, file):
    if not etree.iselement(elem):
        elem = elem.getroot()
    fixup_xmlns(elem)
    etree.ElementTree(elem).write(file)

def get_keys(dic, value):
  keys = [k for k, v in dic.items() if v == value]
  
  if len(keys) == 0:
    raise ValueError('Value not found')
  else:
    return keys[0]

def get_tag(child):
  if not hasattr(child, 'ns_map'):
    return child.tag
  print child.ns_map
  
  pattern = re.compile(
    r'^'      #beginning of string
    r'\{'     #match a single {
    r'(.*?)'  #grab the namespace url
    r'\}'     #match a single }
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

def split_tag(tag):
    if tag.count(':') != 1:
        raise ValueError('Tag must contain a single namespace dawg')
    return tag.split(':')

def dict_tag(tag):
    return dict(zip(['ns','type'], split_tag(tag)))

def parse_directory(directory):
  xmls = {}
  for fname in glob("isdr/*"):
    with open(fname) as fobj:
      xmls[fname] = parse_xmlns(fobj)
      fixup_xmlns(xmls[fname].getroot())
  
  return xmls

xmls = parse_directory('isdr/*')

#write_xmlns(list(xmls.values())[0], sys.stdout)
#print xmls.keys()
#write_xmlns(xmls['isdr\\isdr-20100630.xml'], sys.stdout)

#Collection of facts and definitions that are all related and must be produced as xml
#interesting.

#<us-gaap:CashAndCashEquivalentsAtCarryingValue contextRef="i_2009-12-31" decimals="0" unitRef="USD">146043</us-gaap:CashAndCashEquivalentsAtCarryingValue>
fact = {
    'type': 'CashAndCashEquivalentsAtCarryingValue',
    'namespace': 'us-gaap',
    'context': 'i_2009-12-31', #or possibly the context object (probably not)
    'decimals': '0',
    'unitRef': 'USD',
    'value': '146043',
}

#heres an idea. take all the data in the test, and serialize it into some internal representation (dictionaries maybe)
#then reserialize it back out. check that the xml's are equivilant (mostly? define some metric)
#ok so find a way to convert elements into dictionaries, and back
#might not be too hard.

#lets figure out what data can be inferred. what's the minimal data set?
#obviously the facts. and the contexts. let's work off that.

#So we'll have a dict of facts, each as a dictionary
#facts = {
#    'type':{},
#}

#contexts = {
#    'name':{},
#}

#lets see if we can get that parsed out
#so load up the parsed data xml
for x in xmls['isdr\\isdr-20100630.xml'].getroot():
    print dict_tag(x.tag)['ns']