import random
import unittest
import xbrl

class TestParser(unittest.TestCase):
	def setUp(self):
		self.xmls = xbrl.parse_directory('isdr/*')
	
	def test_contexts(self):
		contexts = []
		for entity in self.xmls['isdr\\isdr-20100630.xml'].getroot():
			try:
				parsed_data = xbrl.parse(entity)
				if parsed_data['type'] == 'context':
					contexts.append(parsed_data)
			except AttributeError:
				pass
		correct_contexts = [{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'i_2010-06-30', 'period': {'type': 'instant', 'value': '2010-06-30'}},					
							{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'i_2009-12-31', 'period': {'type': 'instant', 'value': '2009-12-31'}},
							{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'd_2010-04-01_2010-06-30', 'period': {'type': 'duration', 'value': ('2010-04-01', '2010-06-30')}},
							{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'd_2009-04-01_2009-06-30', 'period': {'type': 'duration', 'value': ('2009-04-01', '2009-06-30')}},
							{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'd_2010-01-01_2010-06-30', 'period': {'type': 'duration', 'value': ('2010-01-01', '2010-06-30')}},
							{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'd_2009-01-01_2009-06-30', 'period': {'type': 'duration', 'value': ('2009-01-01', '2009-06-30')}},
							{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'i_2009-06-30', 'period': {'type': 'instant', 'value': '2009-06-30'}},
							{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'i_2008-12-31', 'period': {'type': 'instant', 'value': '2008-12-31'}},
							{'identifier': {'scheme': 'http://www.sec.gov/CIK', 'value': '0000843006'}, 'type': 'context', 'id': 'i_2010-08-11', 'period': {'type': 'instant', 'value': '2010-08-11'}}]
		for context in contexts:
			self.assertTrue(context in correct_contexts)
		
if __name__ == '__main__':
	unittest.main()