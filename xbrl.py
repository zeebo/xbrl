from glob import glob
from pprint import pprint
import xml.etree.ElementTree as etree
import re
import sys
import StringIO

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
    
    #Store the map for later
    elem.uri_map = uri_map

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

def grab_child(entity, name):
    for child in entity:
        if dict_tag(child.tag)['type'] == name:
            return child

class ImplementationError(Exception): pass
class Parser(object):
    def parse(self, entity):
        edict = dict_tag(entity.tag)
        try:
            return getattr(self, 'parse_%s' % edict['type'])(entity)
        except AttributeError:
            raise AttributeError('Parser for type %s not found' % edict['type'])
        except TypeError:
            raise ImplementationError('Parser implemented incorrectly')
    
    def parse_context(self, entity):
        parsed = {
                'type': 'context',
                'id': entity.attrib['id'],
            }

        identifier_parent = grab_child(entity, 'entity')
        #Just grab the first child out of identifier using a singleton tuple
        identifier, = identifier_parent
        parsed['identifier'] = {
                'scheme': identifier.attrib['scheme'],
                'value': identifier.text,
            }

        period = grab_child(entity, 'period')
        #determine the period type
        if len(period) == 1: #instant type
            instant, = period
            parsed['period'] = {
                    'type': 'instant',
                    'value': instant.text
                }
        elif len(period) == 2: #duration
            start, end = period
            parsed['period'] = {
                    'type': 'duration',
                    'value': (start.text, end.text)
                }
        
        return parsed

class Builder(object):
    def build(self, edict):
        try:
            return getattr(self, 'build_%s' % edict['type'])(edict)
        except KeyError:
            raise TypeError('Malformed build dictionary')
        except AttributeError:
            raise AttributeError('Builder for type %s not found' % edict['type'])
        except TypeError:
            raise ImplementationError('Builder implemented incorrectly')
    
    def build_context(self, edict):
        root = etree.Element('xbrli:context')
        root.set('id', edict['id'])
        entity = etree.SubElement(root, 'xbrli:entity')
        identifier = etree.SubElement(entity, 'xbrli:identifier')
        identifier.set('scheme',edict['identifier']['scheme'])
        identifier.text = edict['identifier']['value']
        period = etree.SubElement(root, 'xbrli:period')
        if edict['period']['type'] == 'instant':
            instant = etree.SubElement(period, 'xbrli:instant')
            instant.text = edict['period']['value']
        elif edict['period']['type'] == 'duration':
            start = etree.SubElement(period, 'xbrli:startDate')
            start.text = edict['period']['value'][0]
            end = etree.SubElement(period, 'xbrli:endDate')
            end.text = edict['period']['value'][1]
        return root
    
def parse(entity, p = Parser()):
    return p.parse(entity)

def build(entity, b = Builder()):
    return b.build(entity)


def as_string(element):
    buf = StringIO.StringIO()
    etree.ElementTree(element).write(buf)
    return buf.getvalue()

def one_line(lines):
    return ''.join([x.strip() for x in lines.splitlines()])

if __name__ == '__main__':
    xmls = parse_directory('isdr/*')
    
    for x in xmls['isdr\\isdr-20100630.xml'].getroot():
        try:
            parsed_data = parse(x)
            print one_line(as_string(x))
            print one_line(as_string(build(parsed_data)))
        except AttributeError:
            pass