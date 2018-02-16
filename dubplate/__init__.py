#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016 Earth Advantage. All rights reserved.
..codeauthor::Paul Munday <paul@paulmunday.net>
"""

# Imports from Standard Library
try:
    from typing import Sequence, Mapping, Optional
except ImportError:
    pass

import datetime
import json

# Imports from Third Party Modules
from frozendict import FrozenOrderedDict, frozendict

# Local Imports

# Constants


# Private Functions
def _convert_datetime(val):
    """Convert date/times to string"""
    if isinstance(val, datetime.datetime):
        val = val.replace(microsecond=0).isoformat()
    elif isinstance(val, datetime.date):
        val = val.isoformat()
    return val


def _convert_list_datetime(lst):
    """Convert  date/times to string in a list"""
    return [_convert_datetime(val) for val in lst]


def _convert_dict_datetime(inputdict):
    """Recursively convert  dat/times to string in a dict-like"""
    rdict = dict()
    for key, val in inputdict.items():
        if isinstance(val, list):
            rdict[key] = _convert_list_datetime(val)
        elif isinstance(val, tuple):
            rdict[key] = _convert_list_datetime(list(val))
        elif isinstance(val, dict):
            rdict[key] = _convert_dict_datetime(val)
        elif isinstance(val, Record):
            rdict[key] = _convert_dict_datetime(val.copy_record())
        else:
            rdict[key] = _convert_datetime(val)
    return rdict


# Public Classes
def generate_hash_index_key(obj_type, fields, values_dict, obj_id=None):
    # type: (str, Sequence[str], Mapping[str, str], Optional[int]) -> str
    """Generate key suitable for use in hash indexes.

    fields should contain the minimum fields necessary to create unique
    key/value combinations to insure uniqueness of hash index keys.

    Only non-null field/value pairs will be included in key string.
    Fields that resolve to unordered value types will raise ValueError.

    example return value: "ObjectType:1:field1:value1:field2:value2"

    :param obj_type: str name representing object to be hashed (ie class name)
    :type obj_type: str
    :param fields: sequence of field names to be used in key string
    :type fields: Sequence
    :param values_dict: dict like object that is expected to have one or more
        values mapping to supplied fields.
    :type values_dict: Mapping
    :param obj_id: optional. int representing id number of relevant object
    :type obj_id: int
    :return: hash key suitable string
    :rtype: str
    """
    hash_index_key = None
    if fields and values_dict:
        field_values = []
        for field in fields:
            value = values_dict.get(field)
            if not value:
                continue
            elif not isinstance(value, (Sequence, int)):
                msg = (
                    "Fields that return unordered value types cannot be used "
                    "to create hash keys. field: {}".format(field)
                )
                raise ValueError(msg)
            else:
                field_values.append('{}:{}'.format(field, value))
        if field_values:
            obj_str = '{}:{}'.format(obj_type, obj_id) if obj_id else obj_type
            hash_index_key = '{}:{}'.format(obj_str, ':'.join(field_values))
    return hash_index_key


class RecordJSONEncoder(json.JSONEncoder):
    """
    Encodes Record data to JSON, converting date & datetime objects.

    N.B. Encodes only record data (i.e. data accessible via dict like methods),
    not attributes (meta) data.
    """
    # pylint:disable=method-hidden
    def default(self, record):
        rdict = record.copy_record()
        return _convert_dict_datetime(rdict)


class Record(object):
    """
    An immutable dict-like structure, that stores extra attributes that are
    needed to process the data but are not part of the data itself.
    This can be used to e.g. store ownership alongside data.

    The data itself is known as the record as is supplied as keyword
    arguments after any other parameters. They are never defined as named
    parameters on init.

    Example:
    a record type MyRecord  has the fields 'a'& 'b', a compulsory
    extra attribute 'c' and an optional attribute 'd'

    >>> my_record = MyRecord('c', d='d', a='a', b='b')
    >>> my_record['a']
    a
    >>> len(my_record)
    2
    >>> my_record.c     # not part of record so doesn't effect len etc
    c

    This class is not intended for use directly, it should be subclassed, to
    correspond to the particular use case.

    This class implements dict like methods (aside for ones that would mutate
    the record). So record values can be accessed with eg record['fieldname']

    These are implemented for record values(i.e. the actual data) only.
    They are stored internally and used in any dict-like operation.

    There are three special attributes used that can be set as class variables
    on a subclass. All are optional. The first two should be supplied as
    tuples.

    'fields' defines the names of fields in the record. If a record
    key=value is supplied and key is not in fields a KeyError
    is raised. In addition the record will be ordered so iterating over
    it will always produce results in the order of fields.

    If a field in fields is not supplied it is set to None. No error
    is raised. This allows for representing things like optional database
    fields. This behaviour can be changed by setting 'require_all_fields'.

    If you set 'require_all_fields' to True on a subclass, it means that
    all fields in 'fields' must be explicitly supplied on initialization,
    Omitting a field will cause a KeyError to be raised, rather that setting
    the field to None.

    'non_null_fields' are fields that must not be null. Hence they
    must be supplied to __init__ and cannot be none. This is used
    to represent things like database fields that cannot be null.
    An error will be raised if they are not supplied.


    For most use cases it is a good idea to set fields, since this
    class is intended for data structures with fixed members, e.g. for
    representing a database record accessed via an api, though its
    not strictly necessary. It does however make it much clearer what
    fields the record does/should contain, and errors will surface much
    quicker if e.g. if an inbound data source starts supplying extra fields
    that we don't handle yet, so its best to treat 'fields' as if it was
    required, though this is not enforced. In addition if fields is used
    the record is represented by a FrozenOrderedDict so field will always
    be returned in order.

    If you wish fields to have a different default value, overide init
    to add them (setdefault(kwargs, 'myfield', default_value)).

    It is possible to use 'non_null_fields' (without fields) to require
    a minimum set of fields that must be  present and non null, while allowing
    arbitrary other fields.

    'dotted' access gives you access  to normal instance attributes that are
    *not* part of the data record itself. These are intended to be used
    by functions that process the data, so they can be kept distinct.
    These are also immutable once set.

    N.B. Since this class is immutable, we can  __slots__ to store
    attributes for performance and efficiency gains.

    However the nature of __slots__ is such that they are fixed once defined.
    Therefore __slots__ must be present  on any subclass if you want to
    add attributes on your subclass (not record values).

    You will also need to add an __init__ method to set any attributes.
    Super must be called at the end of your __init__, once it has been
    called you cannot add or alter attributes or record values.

    IMPORTANT: if you have an __init__ method you should at least have *args,
    even if you throw them away as functions calling records should pass on
    *args in case where they are expected to handle mutiple record types.
    In order to ensure records are interchangeable you **must** do this even
    if you have no intention of using your record this way.

    Note: Attributes defined in __slots__ in the base class are automatically
    included as subclasses inherit __slots__ from the parent class.

    Note: You can define a subclass with __slots__ and then inherit from
    that to predefine some of the attributes as class variables to create
    more specific sub types without adding __slots__ as long as the
    attributes are the same. These subtypes can however contain
    differing records.

    Note: Multiple inheritance can cause issues with slots.
    Therefore if you inherit from more than one class, every class must
    have __slots__ set but it should be empty except for one class
    (this class or a class that inherits it), you are unlikely to need to
    do this in normal use and the issue only applies to classes that have
    more than 1 direct parent.

    Note: Accessing class variables outside of a class can cause dificulties.
    getattr(MyRecord, var, None) will return the value of MyRecord.var if it
    is defined as a class variable. If it is not it will not return default.
    Instead it returns an object of the type member_descriptor, since this is
    not a type defined in Python in the way e.g. int is. To get around this
    we define empty_slot below, which is an equivalent type so you can check
    a return value with isinstance(var, empty_slot)
    if you import it.

    :Example:

    Lets take a book as an example. A record for a book might have the
    following fields:
    Author
    Title
    ISBN
    Price
    Type
    so we could represent a book like this

    book = {
    'author': 'Banana Yoshimoto',
    'title': 'Moshi Moshi',
    'isbn': '978-1-61902-786-2',
    'price': $25,
    'type': 'hardback',
    }

    If we are running a bookshop however there are a number of other things
    we might care about, for instance the supplier so we can pay them once
    sell a book. However merely adding a supplier field is not ideal

    book1 = {
    'author': 'Banana Yoshimoto',
    'title': 'Moshi Moshi',
    'isbn': '978-1-61902-786-2',
    'price': 25,
    'type': 'hardback',
    'supplier': 'Acme inc',
    }

    book2 = {
    'author': 'Banana Yoshimoto',
    'title': 'Moshi Moshi',
    'isbn': '978-1-61902-786-2',
    'price': 25,
    'type': 'hardback',
    'supplier': 'Bob's Books',
    }

    >>> assert book1 == book2
    AssertionError

    Oops! they are same book (and our customers don't care who the supplier
    is).
    Lets solve this using Record

    class Book(Record):
        __slots__ = ['supplier', 'price', 'isbn']
        fields = ['author, 'title',  'type']
        non_null_fields = ['title']

        def __init__(supplier,price, isbn, **kwargs):
            self.supplier = supplier
            self.price = price
            self.isbn = isbn
            # set type to paperback by default
            kwargs.setdefault('type', 'paperback')
            super(Book, self).__init__(**kwargs)

    book1 = Book(
        'Acme Inc','978-1-61902-786-2', 25,
        author='Banana Yoshimoto', title='Moshi Moshi',
        isbn=, type='hardback'
    )

    book2 = Book(
        'Bob's Books','978-1-61902-786-2', 20,
        author='Banana Yoshimoto', title='Moshi Moshi', type='hardback'
    )

    >>> assert book1 == book2
    it works!

    Now lets see what else we can do:

    book3 = Book(
        'Acme Inc','978-1-59017-896-6', 14.95,
        author='Barbara Comyns',
        title='Our Spoons Came From Woolworths',
    )

    (its a paperback)

    stock = [book1, book2, book3]

    def checkstock(stock, title, type, author=None):
        book = {'author': author. 'title': title, 'type':type}
        prices = []
        for item in stock:
            if book == item:
            books.append(book)
        return books

    def sell_book(customer, stock, title, type, author=None):
        in_stock = check_stock(stock, title, type, author=author)
        if in_stock:
            prices = [book.price for book in books]
            cheapest = prices.index(min(prices))
            book = books[cheapest]
            print "Congratulations you just brought {}!".format(
                ", ".join(book.values())
            )
            pay_invoice(book.supplier, book.isbn, book.price * 0.33)
            charge(customer, book.price)

    Do you have a copy of 'Moshi Moshi' by Banana Yoshimoto in hardback?
    >>> books = checkstock(
    stock, 'Moshi Moshi', type='hardback', author="Banana Yoshimoto"
    )
    >>> len(books)
    2
    Yes we have two copies in stock
    >>> sell_book(
    customer, stock, 'Moshi Moshi', type='hardback', author="Banana Yoshimoto"
    )
    Congratulations you just brought Banana Yoshimoto, Moshi, Moshi, hardback!
    """
    # pylint:disable=too-few-public-methods
    __slots__ = [
        '_initialized', '__record', 'fields', 'non_null_fields',
        'require_all_fields', 'hash_index_fields'
    ]

    def __init__(self, *args, **kwargs):
        # pylint: disable=unused-argument
        # N.B. we throw args away here. It's there to remind people
        # subclassing this, to also add it, even if they throw it away
        # default to not requiring fields to be set explicitly
        if not getattr(self, 'require_all_fields', None):
            self.require_all_fields = False
        # Set internal record values
        self.__record = self._set_record(kwargs)
        self._initialized = True

    def __repr__(self):
        # pylint:disable=protected-access
        return "<{}, {}>".format(self.__class__.__name__, self.__record._dict)

    def __contains__(self, name):
        """Does name exist in db record?"""
        return name in self.__record

    def __eq__(self, other):
        """Compare against db record"""
        return other == self.__record

    def __ne__(self, other):
        """Compare against db record"""
        return other != self.__record

    def __len__(self):
        """Length of db record"""
        return len(self.__record)

    def __hash__(self):
        """Hash of db record. Hashable because immutable."""
        return hash(self.__record)

    def __iter__(self):
        """Iter for record (obivates the need for __next__)"""
        return iter(self.__record)

    def __delattr__(self, name):
        """Prevent deleting  of attributes"""
        if self._initialized:
            msg = "'{}' object does not support attribute deletion".format(
                self.__class__.__name__
            )
            raise TypeError(msg)
        else:
            object.__delattr__(self, name)

    def __setattr__(self, name, value):
        """Prevent setting of attributes"""
        if getattr(self, '_initialized', None):
            msg = "'{}' object does not support attribute assignment".format(
                self.__class__.__name__
            )
            raise TypeError(msg)
        else:
            object.__setattr__(self, name, value)

    def __getitem__(self, name):
        """
        Return value from self.__record .
        """
        return self.__record[name]

    def __setitem__(self, name, value):
        """Prevent setting of items"""
        msg = "'{}' object does not support item assignment".format(
            self.__class__.__name__
        )
        raise TypeError(msg)

    def __delitem__(self, name):
        """Prevent deleting of items"""
        msg = "'{}' object does not support item deletion".format(
            self.__class__.__name__
        )
        raise TypeError(msg)

    def _set_record(self, record):
        """Set record values"""
        # pylint:disable=redefined-variable-type
        fields = getattr(self, 'fields', [])
        non_null_fields = set(getattr(self, 'non_null_fields', []))
        keys = set(record.keys())
        # Check non_null_fields are present and not null
        if non_null_fields:
            missing = ", ".join(sorted(non_null_fields - keys))
            if missing:
                msg = "The following field{} required: {}".format(
                    's are' if len(missing) > 1 else ' is',
                    missing
                )
                raise KeyError(msg)
            else:
                null_fields = [
                    field for field in non_null_fields
                    if record[field] is None
                ]
                if null_fields:
                    msg = "The following field{} can not be None: {}".format(
                        's' if len(null_fields) > 1 else '',
                        ", ".join(sorted(null_fields))
                    )
                    raise KeyError(msg)
        if fields:
            # check there aren't things present not in fields
            if keys > set(fields):
                msg = (
                    "Extra keys: {}. Only the following keys can "
                    "be used in the record: {}".format(
                        ", ".join(keys - set(fields)), ", ".join(fields)
                    )
                )
                raise KeyError(msg)
            elif keys < set(fields) and self.require_all_fields:
                msg = (
                    "Missing keys: {}. The following keys must "
                    "be used in the record: {}".format(
                        ", ".join(set(fields) - keys), ", ".join(fields)
                    )
                )
                raise KeyError(msg)

            # return FrozenOrderedDict
            record_dict = FrozenOrderedDict(
                [(field, record.get(field, None)) for field in fields]
            )
        else:
            record_dict = frozendict(record)
        return record_dict

    # public methods reflecting dict
    def get(self, key, default=None):
        """Provide get method"""
        return self.__record.get(key, default)

    def items(self):
        """Provide items """
        return self.__record.items()

    def keys(self):
        """Provide keys """
        return self.__record.keys()

    def values(self):
        """Provide values """
        return self.__record.values()

    def copy_record(self, **kwargs):
        """
        Return a copy of record, updated with values from kwargs.

        Will return a frozendict or FrozenOrderedDict
        """
        return self._set_record(self.__record.copy(**kwargs))

    def json(self):
        """Return record data as a json string"""
        return RecordJSONEncoder().encode(self)

    def get_hash_index_key(self):
        """
        Return str for hash key from hash_index_fields and associated values.

        Uses all fields in fields if hash_index_fields is not defined.
        Keys from slots can be included in hash_index_fields.
        """
        class_name = self.__class__.__name__
        fields = getattr(self, 'fields', None)
        key_fields = getattr(self, 'hash_index_fields', None) or fields or []
        slots_dict = {
            key: getattr(self, key, None)
            for key in key_fields if key in self.__slots__
        }
        value_dict = self.copy_record(**slots_dict)
        return generate_hash_index_key(class_name, key_fields, value_dict)



# calling getattr(Class, var, default) to read a class variable,
# on a class with __slots__defined i.e. Record can lead to unintended
# consequence is the slot member is not a class variable as it does not
# return None but returns an object of type 'member_descriptor'.
# Checking for this is difficult as isinstance(x, member_descriptor)
# can not be used, as member_descriptor is not defined.
# So we define a "type" empty_slot here, so isinstance(x, empty_slot)
# can be used if empty_slot is imported
# pylint:disable=no-member, invalid-name, protected-access
empty_slot = type(Record._initialized)
