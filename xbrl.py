from glob import glob
from pprint import pprint
import xml.etree.ElementTree as etree
import re
import sys
import cStringIO

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
        elem.tag = name.lstrip(':')
    
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
        if tag.count(':') == 0:
            return ('', tag)
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
            pass
        except TypeError:
            raise ImplementationError('Parser implemented incorrectly')
        
        return self.parse_ns(entity, edict['ns'])
    
    def parse_labelLink(self, entity):
        def parse_loc(entity):
            #<link:loc xlink:type="locator" xlink:href="http://taxonomies.xbrl.us/us-gaap/2009/non-gaap/dei-2009-01-31.xsd#dei_DocumentType" xlink:label="DocumentType" xlink:title="DocumentType"/>
            return {
                'type': 'loc',
                'href': entity.attrib['xlink:href'],
                'label': entity.attrib['xlink:label'],
                'title': entity.attrib['xlink:title'],
            }
        
        def parse_label(entity):
            #<link:label xlink:type="resource" xlink:label="label_DocumentType" xlink:role="http://www.xbrl.org/2003/role/label" xlink:title="label_DocumentType" xml:lang="en" id="label_DocumentType">Document Type</link:label>
            return {
                'type': 'label',
                'label': entity.attrib['xlink:label'],
                'role': entity.attrib['xlink:role'],
                'title': entity.attrib['xlink:title'],
                'lang': entity.attrib['{http://www.w3.org/XML/1998/namespace}lang'],
                'id': entity.attrib['id'],
                'text': entity.text,
            }    
        
        def parse_labelArc(entity):
            #<link:labelArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label" xlink:from="DocumentType" xlink:to="label_DocumentType" xlink:title="label: DocumentType to label_DocumentType"/>
            return {
                'type': 'labelArc',
                'arcrole': entity.attrib['xlink:arcrole'],
                'from': entity.attrib['xlink:from'],
                'to': entity.attrib['xlink:to'],
                'title': entity.attrib['xlink:title'],
            }
        
        p_funcs = {
            'loc': parse_loc,
            'label': parse_label,
            'labelArc': parse_labelArc,
        }

        parsed = {
            'type': 'labelLink',
            'labelLink_type': entity.attrib['xlink:type'],
            'role': entity.attrib['xlink:role'],
            'locs': [],
            'labels': [],
            'labelArcs': [],
        }
        for child in entity:
            tags = dict_tag(child.tag)
            key = '%ss' % tags['type']
            parsed[key].append(p_funcs[tags['type']](child))

        return parsed

    def parse_ns(self, entity, ns):
        good_ns = ['us-gaap', 'dei']

        if ns not in good_ns:
            raise AttributeError('Unable to parse %s' % entity)
        
        tags = dict_tag(entity.tag)
        parsed = {
            'type': 'general',
            'element_type': tags['type'],
            'namespace': ns,
            'text': entity.text,
        }
        for attrib in entity.attrib:
            if attrib in parsed:
                raise ImplementationError('Unexpected edge case')
            
            parsed[attrib] = entity.attrib[attrib]
        return parsed

    def parse_schemaRef(self, entity):
        parsed = {
            'type': 'schemaRef',
            'link_type': entity.attrib['xlink:type'],
            'href': entity.attrib['xlink:href'],
        }
        return parsed
    
    def parse_unit(self, entity):
        parsed = {
            'type': 'unit',
            'id': entity.attrib['id'],
            'measure': grab_child(entity, 'measure').text
        }
        return parsed
    
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
        if type(edict) != dict:
            raise TypeError('Malformed build dictionary')
        try:
            return getattr(self, 'build_%s' % edict['type'])(edict)
        except KeyError:
            raise TypeError('Malformed build dictionary')
        except AttributeError:
            raise AttributeError('Builder for type %s not found' % edict['type'])
        except TypeError,e:
            raise ImplementationError('Builder implemented incorrectly')
    
    def build_general(self, edict):
        exclude = ['type', 'element_type', 'namespace', 'text']
        root = etree.Element('%s:%s' % (edict['namespace'], edict['element_type']))
        for attrib in edict:
            if attrib not in exclude:
                root.set(attrib, edict[attrib])
        root.text = edict['text']
        return root
    
    def build_labelLink(self, edict):
        #<link:labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
        root = etree.Element('link:labelLink')
        return root
    
    def build_unit(self, edict):
        root = etree.Element('xbrli:unit')
        root.set('id', edict['id'])
        measure = etree.SubElement(root, 'xbrli:measure')
        measure.text = edict['measure']
        return root
    
    def build_schemaRef(self, edict):
        root = etree.Element('link:schemaRef')
        root.set('xlink:type', edict['link_type'])
        root.set('xlink:href', edict['href'])
        return root
    
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
    buf = cStringIO.StringIO()
    etree.ElementTree(element).write(buf)
    return buf.getvalue()

def one_line(lines):
    return ''.join([x.strip() for x in lines.splitlines()])

if __name__ == '__main__':
    xmls = parse_directory('isdr/*')
    
    for f in xmls:
        for x in xmls[f].getroot():
            #for x in xmls['isdr\\isdr-20100630.xml'].getroot():
            try:
                parsed_data = parse(x)
                if one_line(as_string(x)) != one_line(as_string(build(parsed_data))):
                    print '[%s] problem on %s' % (f, x)
            except AttributeError:
                print 'INVALID:', f, x