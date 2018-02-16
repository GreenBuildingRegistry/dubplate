#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016-2017 Earth Advantage. All rights reserved.
..codeauthor::Paul Munday <paul@paulmunday.net>

Unit tests for dubplate.
"""
# Imports from Standard Library
import datetime
import json
import sys
import six
import unittest

# Imports from Third Party Modules
from frozendict import frozendict

# Local Imports
from dubplate import Record, empty_slot

PY3 = sys.version_info[0] == 3
if PY3:
    from unittest import mock
else:
    import mock

# Constants
NS = 'http://example.org/ns'
NAMESPACE = {'n': NS}


class TstRecord(Record):
    # pylint:disable=slots-on-old-class,too-few-public-methods
    __slots__ = ['service', 'test']

    def __init__(self, service, test, **kwargs):
        self.service = service
        self.test = test
        super(TstRecord, self).__init__(**kwargs)


class FieldRecord(TstRecord):
    # pylint:disable=slots-on-old-class,too-few-public-methods
    fields = ('a', 'b', 'c')
    non_null_fields = ('a', 'b')


class RequiredFieldRecord(TstRecord):
    # pylint:disable=slots-on-old-class,too-few-public-methods
    non_null_fields = ('a', 'b')


class RequireAllFieldsRecord(TstRecord):
    # pylint:disable=slots-on-old-class,too-few-public-methods
    fields = ('a', 'b', 'c')
    non_null_fields = ('a', 'b')
    require_all_fields = True


class HashIndexRecord(TstRecord):
    # pylint:disable=slots-on-old-class,too-few-public-methods
    hash_index_fields = ('a', 'b')


class HashIndexSlotsRecord(TstRecord):
    # pylint:disable=slots-on-old-class,too-few-public-methods
    hash_index_fields = ('test', 'a', 'b')


class RecordTests(unittest.TestCase):
    """Test base record class"""

    def setUp(self):
        self.rdict = {'color': 'red', 'number': 10}
        self.record = TstRecord('service', 'test', **self.rdict)

    def test_record_access(self):
        # test attributes and record data set
        self.assertEqual(self.record.test, 'test')
        self.assertEqual(self.record['color'], 'red')

        # test difference between attributes and record data
        with self.assertRaises(KeyError) as conm:
            # pylint:disable=pointless-statement
            self.record['test']
        self.assertEqual(str(conm.exception), "'test'")

        with self.assertRaises(AttributeError) as conm:
            # pylint:disable=pointless-statement,no-member
            self.record.color
        self.assertEqual(
            str(conm.exception), "'TstRecord' object has no attribute 'color'"
        )

    def test_is_immutable(self):
        with self.assertRaises(TypeError) as conm:
            self.record.test = 1
        self.assertEqual(
            str(conm.exception),
            "'TstRecord' object does not support attribute assignment"
        )

        with self.assertRaises(TypeError) as conm:
            self.record['number'] = 1
        self.assertEqual(
            str(conm.exception),
            "'TstRecord' object does not support item assignment"
        )

        with self.assertRaises(TypeError) as conm:
            del self.record.test
        self.assertEqual(
            str(conm.exception),
            "'TstRecord' object does not support attribute deletion"
        )

        with self.assertRaises(TypeError) as conm:
            del self.record['number']
        self.assertEqual(
            str(conm.exception),
            "'TstRecord' object does not support item deletion"
        )

    def test_repr(self):
        # TODO: the dict portion makes this test intermittently problematic
        # self.assertEqual(
        #     repr(self.record), "<TstRecord, {'color': 'red', 'number': 10}>"
        # )
        pass

    def test_dict_like(self):
        self.assertIn('color', self.record)
        self.assertNotIn('test', self.record)

        self.assertEqual(self.record, {'color': 'red', 'number': 10})
        self.assertNotEqual(self.record, {'color': 'red', 'number': 1})
        self.assertEqual(len(self.record), 2)

        # hash is hash of record
        fdt = frozendict({'color': 'red', 'number': 10})
        self.assertEqual(hash(self.record), hash(fdt))

        self.assertEqual(self.record.get('color', 'blue'), 'red')
        self.assertNotEqual(self.record.get('color', 'blue'), 'blue')

        self.assertEqual(self.record.get('other', 'blue'), 'blue')

        six.assertCountEqual(
            self,
            list(self.record.items()), [('color', 'red'), ('number', 10)]
        )

        self.assertDictEqual(
            {'color': 'red', 'number': 10},
            {key: val for key, val in self.record.items()}
        )

        six.assertCountEqual(
            self,
            ['color', 'number'], list(self.record.keys())
        )
        six.assertCountEqual(
            self,
            ['color', 'number'], [key for key in self.record.keys()]
        )

        six.assertCountEqual(
            self,
            ['red', 10], list(self.record.values())
        )
        six.assertCountEqual(
            self,
            ['red', 10], [value for value in self.record.values()]
        )

    def test_non_null_fields(self):
        # raises error if attribute not set
        with self.assertRaises(KeyError) as conm:
            RequiredFieldRecord('red', 1, a=2, c=3)
        self.assertEqual(
            str(conm.exception),
            "'The following field is required: b'"
        )

        with self.assertRaises(KeyError) as conm:
            RequiredFieldRecord('red', 1, d=2, c=3)
        self.assertEqual(
            str(conm.exception),
            "'The following fields are required: a, b'"
        )

        # raises errror if required field is None
        with self.assertRaises(KeyError) as conm:
            RequiredFieldRecord('red', 1, a=2, b=None)
        self.assertEqual(
            str(conm.exception),
            "'The following field can not be None: b'"
        )

        with self.assertRaises(KeyError) as conm:
            RequiredFieldRecord('red', 1, a=None, b=None)
        self.assertEqual(
            str(conm.exception),
            "'The following fields can not be None: a, b'"
        )

        # ok to set extra fields if fields not defined
        rec = RequiredFieldRecord('red', 1, a=1, b=2, c=3)

        # if we are here no error raised
        assert rec

    def test_fields(self):
        # test rejects extra fields
        with self.assertRaises(KeyError) as conm:
            FieldRecord('red', 1, a=2, b=3, c=4, d=5)
        self.assertEqual(
            str(conm.exception),
            "'Extra keys: d. "
            "Only the following keys can be used in the record: a, b, c'"
        )

        # test ok
        rec = FieldRecord('red', 1, a=2, b=3, c=4)
        assert rec

        # test ok for non-required fields to be None
        rec = FieldRecord('red', 1, a=2, b=3, c=None)
        assert rec

        # test required fields
        with self.assertRaises(KeyError) as conm:
            FieldRecord('red', 1, a=2, c=3)
        self.assertEqual(
            str(conm.exception),
            "'The following field is required: b'"
        )

        with self.assertRaises(KeyError) as conm:
            FieldRecord('red', 1, d=2, c=3)
        self.assertEqual(
            str(conm.exception),
            "'The following fields are required: a, b'"
        )

        # raises errror if required field is None
        with self.assertRaises(KeyError) as conm:
            FieldRecord('red', 1, a=2, b=None, c=None)
        self.assertEqual(
            str(conm.exception),
            "'The following field can not be None: b'"
        )

        # test ordering
        rec = FieldRecord('red', 1, a=2, c=4, b=3)
        expected = ['a', 'b', 'c']
        result = [key for key in rec.keys()]
        self.assertEqual(expected, result)

    def test_require_all_fields(self):
        # test requires all fields
        with self.assertRaises(KeyError) as conm:
            RequireAllFieldsRecord('red', 1, a=2, b=3)
        self.assertEqual(
            str(conm.exception),
            "'Missing keys: c. "
            "The following keys must be used in the record: a, b, c'"
        )

        # test rejects extra fields
        with self.assertRaises(KeyError) as conm:
            FieldRecord('red', 1, a=2, b=3, c=4, d=5)
        self.assertEqual(
            str(conm.exception),
            "'Extra keys: d. "
            "Only the following keys can be used in the record: a, b, c'"
        )

        # test ok
        rec = FieldRecord('red', 1, a=2, b=3, c=4)
        assert rec

        # test ok for non-required fields to be None
        rec = FieldRecord('red', 1, a=2, b=3, c=None)
        assert rec

        # test required fields
        with self.assertRaises(KeyError) as conm:
            FieldRecord('red', 1, a=2, c=3)
        self.assertEqual(
            str(conm.exception),
            "'The following field is required: b'"
        )

        with self.assertRaises(KeyError) as conm:
            FieldRecord('red', 1, d=2, c=3)
        self.assertEqual(
            str(conm.exception),
            "'The following fields are required: a, b'"
        )

        # raises errror if required field is None
        with self.assertRaises(KeyError) as conm:
            FieldRecord('red', 1, a=2, b=None, c=None)
        self.assertEqual(
            str(conm.exception),
            "'The following field can not be None: b'"
        )

        # test ordering
        rec = FieldRecord('red', 1, a=2, c=4, b=3)
        expected = ['a', 'b', 'c']
        result = [key for key in rec.keys()]
        self.assertEqual(expected, result)

    def test_copy_record(self):
        """Test copy_record method"""
        copy = self.record.copy_record()
        self.assertEqual(copy, self.rdict)
        copy = self.record.copy_record(color='green')
        self.assertEqual(copy, {'color': 'green', 'number': 10})

        # ensure extra/incorrect fields can't be set
        record = FieldRecord('red', 1, a=2, b=3, c=4)
        self.assertRaises(
            KeyError, record.copy_record, colorx='green'
        )

        # ensure non-null fields can't be set to None
        self.assertRaises(
            KeyError, record.copy_record, a=None
        )

    def test_json(self):
        """Test json() method"""
        dtime = datetime.datetime(2001, 1, 1, 1, 1, 1, 100)
        date = datetime.date(2001, 1, 1)
        json_record = TstRecord(
            service='service', test='test',
            string='test', integer=1,
            datetime=dtime, date=date,
            lst=[dtime, date],
            tpl=(dtime, date),
            dictionary=dict(datetime=dtime, date=date)
        )

        dtime_str = '2001-01-01T01:01:01'
        date_str = '2001-01-01'

        result = json_record.json()
        self.assertIsInstance(result, str)

        result = json.loads(result)
        self.assertNotIn('service', result)
        self.assertNotIn('test', result)

        self.assertEqual(result['string'], 'test')

        self.assertIsInstance(result['integer'], int)
        self.assertEqual(result['integer'], 1)

        self.assertEqual(result['datetime'], dtime_str)
        self.assertEqual(result['date'], date_str)

        self.assertEqual(result['lst'], [dtime_str, date_str])
        self.assertEqual(result['tpl'], [dtime_str, date_str])

        result = result['dictionary']
        self.assertIsInstance(result, dict)

        self.assertEqual(result['datetime'], dtime_str)
        self.assertEqual(result['date'], date_str)

        json_record2 = TstRecord(
            service='service', test='test',
            record=json_record
        )

        result = json_record2.json()
        self.assertIsInstance(result, str)

        result = json.loads(result)
        self.assertNotIn('service', result)
        self.assertNotIn('test', result)

        result = result['record']
        self.assertIsInstance(result, dict)

        self.assertNotIn('service', result)
        self.assertNotIn('test', result)

        self.assertEqual(result['string'], 'test')

        self.assertIsInstance(result['integer'], int)
        self.assertEqual(result['integer'], 1)

        self.assertEqual(result['datetime'], dtime_str)
        self.assertEqual(result['date'], date_str)

        self.assertEqual(result['lst'], [dtime_str, date_str])
        self.assertEqual(result['tpl'], [dtime_str, date_str])

        result = result['dictionary']
        self.assertIsInstance(result, dict)

        self.assertEqual(result['datetime'], dtime_str)
        self.assertEqual(result['date'], date_str)

    def test_empty_slot(self):
        """Test empty_slot"""
        service = getattr(TstRecord, 'service')
        self.assertTrue(isinstance(service, empty_slot))

    @mock.patch('dubplate.generate_hash_index_key')
    def test_get_hash_index_key(self, mock_hash_index_key):
        """Test get_hash_index_key"""
        mock_hash_index_key.return_value = ''
        rec = TstRecord('service', 'test', a=1, b=2)
        rec.get_hash_index_key()
        mock_hash_index_key.assert_called_with(
            rec.__class__.__name__, [], rec
        )

        fields_rec = FieldRecord('service', 'test', a=1, b=2)
        fields_rec.get_hash_index_key()
        mock_hash_index_key.assert_called_with(
            fields_rec.__class__.__name__, fields_rec.fields, fields_rec
        )

        hash_rec = HashIndexRecord('service', 'test', a=1, b=2)
        hash_rec.get_hash_index_key()
        mock_hash_index_key.assert_called_with(
            hash_rec.__class__.__name__, hash_rec.hash_index_fields, hash_rec
        )

        slot_rec = HashIndexSlotsRecord('service', 'test', a=1, b=2)
        slot_rec.get_hash_index_key()
        expected_val_dict = frozendict({'test': 'test', 'a': 1, 'b': 2})
        mock_hash_index_key.assert_called_with(
            slot_rec.__class__.__name__, slot_rec.hash_index_fields,
            expected_val_dict
        )
