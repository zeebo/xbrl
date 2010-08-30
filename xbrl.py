from glob import glob
from pprint import pprint
import xml.etree.ElementTree as etree

xmls = {}
for fname in glob("isdr/*"):
	with open(fname) as fobj:
		xmls[fname] = etree.parse(fobj).getroot()

xml = xmls['isdr/isdr-20100630.xsd']

def tree_print(element, indent=0):
	if indent == 0:
		print element.tag
	for child in element:
		print ' %s%s%s' % ('|  '*indent, '|-', child.tag)
		if len(child) > 0:
			tree_print(child, indent+1)

tree_print(xml)