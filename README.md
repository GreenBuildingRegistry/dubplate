# Dubplate

The Dubplate library provides the Record class . This  is an immutable,
dict-like structure for storing data, that may be defined with a fixed set of
keys.

In addition it can store additional meta-data like data as object attributes
that can be acessessed used dotted notation e.g. record.meta_attr.
These (or rather the names of) are predefined in __slots__ and can be used to
e.g. store the use associated with the record. They are often also defined
as class variables, for instance to store a reference to a particular api
endpoint on the Record that is used to store the data it returns.

The Record class is not intended to be used directly, rather it should be
subclassed to create a custom data structure, so for instance there is
an Address record to ensure addresses are stored in a commmon format.


## Example:
a record type MyRecord  has the fields 'a'& 'b', a compulsory
extra attribute 'c' and an optional attribute 'd'
```
>>> my_record = MyRecord('c', d='d', a='a', b='b')
>>> my_record['a']
a
>>> len(my_record)
2
>>> my_record.c     # not part of record so doesn't effect len etc
c
```
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

### Example:

Lets take a book as an example. A record for a book might have the
following fields:
* Author
* Title
*  ISBN
* Price
* Type

so we could represent a book like this
```python
book = {
    'author': 'Banana Yoshimoto',
    'title': 'Moshi Moshi',
    'isbn': '978-1-61902-786-2',
    'price': 25,
    'type': 'hardback',
}
```
If we are running a bookshop however there are a number of other things
we might care about, for instance the supplier so we can pay them once
sell a book. However merely adding a supplier field is not ideal

```python
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
```
```
>>> assert book1 == book2
AssertionError
```
Oops! they are same book (and our customers don't care who the supplier
is).
Lets solve this using Record

```python
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
```
```
>>> assert book1 == book2
```
it works!


Now lets see what else we can do:

```python
book3 = Book(
    'Acme Inc','978-1-59017-896-6', 14.95,
    author='Barbara Comyns',
    title='Our Spoons Came From Woolworths',
)

# (its a paperback)

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
```
Do you have a copy of 'Moshi Moshi' by Banana Yoshimoto in hardback?
```
>>> books = checkstock(
  stock, 'Moshi Moshi', type='hardback', author="Banana Yoshimoto"
)
>>> len(books)
2
```
Yes we have two copies in stock
```
>>> sell_book(
customer, stock, 'Moshi Moshi', type='hardback', author="Banana Yoshimoto"
)
```
Congratulations you just brought Banana Yoshimoto, Moshi, Moshi, hardback!

### Dubplate?
Wikipedia:

*"A dubplate is an acetate disc – usually 10 inches in diameter – used in
mastering studios for quality control and test recordings before proceeding
with the final master, and subsequent pressing of the record to be
mass-produced on vinyl."*

Dubplates play an important part in Jamaican Reggae soundsystem culture, and
other musical genres influenced by it. The term is used to refer to the acetate
discs or tracks that a limited number of people such as DJ's have the clout to
get hold of.

As there is already a Python package called Vinyl we went with dubplate as a
tribute to some of our favourite sounds.
