Decoding
~~~~~~~~

dictionaries
^^^^^^^^^^^^

:py:attr:`decode <qs_codec.decode>` allows you to create nested ``dict``\ s within your query
strings, by surrounding the name of sub-keys with square brackets
``[]``. For example, the string ``'foo[bar]=baz'`` converts to:

.. code:: python

   import qs_codec as qs

   assert qs.decode('foo[bar]=baz') == {'foo': {'bar': 'baz'}}

URI encoded strings work too:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a%5Bb%5D=c') == {'a': {'b': 'c'}}

You can also nest your ``dict``\ s, like ``'foo[bar][baz]=foobarbaz'``:

.. code:: python

   import qs_codec as qs

   assert qs.decode('foo[bar][baz]=foobarbaz') == {'foo': {'bar': {'baz': 'foobarbaz'}}}

By default, when nesting ``dict``\ s qs will only decode up to 5
children deep. This means if you attempt to decode a string like
``'a[b][c][d][e][f][g][h][i]=j'`` your resulting ``dict`` will be:

.. code:: python

   import qs_codec as qs

   assert qs.decode("a[b][c][d][e][f][g][h][i]=j") == {
       "a": {"b": {"c": {"d": {"e": {"f": {"[g][h][i]": "j"}}}}}}
   }

This depth can be overridden by setting the :py:attr:`depth <qs_codec.models.decode_options.DecodeOptions.depth>`:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a[b][c][d][e][f][g][h][i]=j',
       qs.DecodeOptions(depth=1),
   ) == {'a': {'b': {'[c][d][e][f][g][h][i]': 'j'}}}


You can configure :py:attr:`decode <qs_codec.decode>` to throw an error
when parsing nested input beyond this depth using :py:attr:`strict_depth <qs_codec.models.decode_options.DecodeOptions.strict_depth>` (defaults to ``False``):

.. code:: python

   import qs_codec as qs

   try:
       qs.decode(
           'a[b][c][d][e][f][g][h][i]=j',
           qs.DecodeOptions(depth=1, strict_depth=True),
       )
   except IndexError as e:
       assert str(e) == 'Input depth exceeded depth option of 1 and strict_depth is True'

The depth limit helps mitigate abuse when :py:attr:`decode <qs_codec.decode>` is used to parse user input, and it is recommended
to keep it a reasonably small number. :py:attr:`strict_depth <qs_codec.models.decode_options.DecodeOptions.strict_depth>`
adds a layer of protection by throwing an ``IndexError`` when the limit is exceeded, allowing you to catch and handle such cases.

For similar reasons, by default :py:attr:`decode <qs_codec.decode>` will only parse up to 1000 parameters. This can be overridden by passing a
:py:attr:`parameter_limit <qs_codec.models.decode_options.DecodeOptions.parameter_limit>` option:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a=b&c=d',
       qs.DecodeOptions(parameter_limit=1),
   ) == {'a': 'b'}

To bypass the leading question mark, use
:py:attr:`ignore_query_prefix <qs_codec.models.decode_options.DecodeOptions.ignore_query_prefix>`:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       '?a=b&c=d',
       qs.DecodeOptions(ignore_query_prefix=True),
   ) == {'a': 'b', 'c': 'd'}

An optional :py:attr:`delimiter <qs_codec.models.decode_options.DecodeOptions.delimiter>` can also be passed:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a=b;c=d',
       qs.DecodeOptions(delimiter=';'),
   ) == {'a': 'b', 'c': 'd'}

:py:attr:`delimiter <qs_codec.models.decode_options.DecodeOptions.delimiter>` can be a regular expression too:

.. code:: python

   import qs_codec as qs
   import re

   assert qs.decode(
       'a=b;c=d',
       qs.DecodeOptions(delimiter=re.compile(r'[;,]')),
   ) == {'a': 'b', 'c': 'd'}

Option :py:attr:`allow_dots <qs_codec.models.decode_options.DecodeOptions.allow_dots>`
can be used to enable dot notation:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a.b=c',
       qs.DecodeOptions(allow_dots=True),
   ) == {'a': {'b': 'c'}}

Option :py:attr:`decode_dot_in_keys <qs_codec.models.decode_options.DecodeOptions.decode_dot_in_keys>`
can be used to decode dots in keys.

**Note:** it implies :py:attr:`allow_dots <qs_codec.models.decode_options.DecodeOptions.allow_dots>`, so
:py:attr:`decode <qs_codec.decode>` will error if you set :py:attr:`decode_dot_in_keys <qs_codec.models.decode_options.DecodeOptions.decode_dot_in_keys>`
to ``True``, and :py:attr:`allow_dots <qs_codec.models.decode_options.DecodeOptions.allow_dots>` to ``False``.

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'name%252Eobj.first=John&name%252Eobj.last=Doe',
       qs.DecodeOptions(decode_dot_in_keys=True),
   ) == {'name.obj': {'first': 'John', 'last': 'Doe'}}

Option :py:attr:`allow_empty_lists <qs_codec.models.decode_options.DecodeOptions.allow_empty_lists>` can
be used to allow empty ``list`` values in a ``dict``

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'foo[]&bar=baz',
       qs.DecodeOptions(allow_empty_lists=True),
   ) == {'foo': [], 'bar': 'baz'}

Option :py:attr:`duplicates <qs_codec.models.decode_options.DecodeOptions.duplicates>` can be used to
change the behavior when duplicate keys are encountered

.. code:: python

   import qs_codec as qs

   assert qs.decode('foo=bar&foo=baz') == {'foo': ['bar', 'baz']}

   assert qs.decode(
       'foo=bar&foo=baz',
       qs.DecodeOptions(duplicates=qs.Duplicates.COMBINE),
   ) == {'foo': ['bar', 'baz']}

   assert qs.decode(
       'foo=bar&foo=baz',
       qs.DecodeOptions(duplicates=qs.Duplicates.FIRST),
   ) == {'foo': 'bar'}

   assert qs.decode(
       'foo=bar&foo=baz',
       qs.DecodeOptions(duplicates=qs.Duplicates.LAST),
   ) == {'foo': 'baz'}

If you have to deal with legacy browsers or services, there’s also
support for decoding percent-encoded octets as :py:attr:`LATIN1 <qs_codec.enums.charset.Charset.LATIN1>`:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a=%A7',
       qs.DecodeOptions(charset=qs.Charset.LATIN1),
   ) == {'a': '§'}

Some services add an initial ``utf8=✓`` value to forms so that old
Internet Explorer versions are more likely to submit the form as utf-8.
Additionally, the server can check the value against wrong encodings of
the checkmark character and detect that a query string or
``application/x-www-form-urlencoded`` body was *not* sent as ``utf-8``,
e.g. if the form had an ``accept-charset`` parameter or the containing
page had a different character set.

:py:attr:`decode <qs_codec.decode>` supports this mechanism via the
:py:attr:`charset_sentinel <qs_codec.models.decode_options.DecodeOptions.charset_sentinel>` option.
If specified, the ``utf8`` parameter will be omitted from the returned
``dict``. It will be used to switch to :py:attr:`LATIN1 <qs_codec.enums.charset.Charset.LATIN1>` or
:py:attr:`UTF8 <qs_codec.enums.charset.Charset.UTF8>` mode depending on how the checkmark is encoded.

**Important**: When you specify both the :py:attr:`charset <qs_codec.models.decode_options.DecodeOptions.charset>`
option and the :py:attr:`charset_sentinel <qs_codec.models.decode_options.DecodeOptions.charset_sentinel>` option, the
:py:attr:`charset <qs_codec.models.decode_options.DecodeOptions.charset>` will be overridden when the request contains a
``utf8`` parameter from which the actual charset can be deduced. In that
sense the :py:attr:`charset <qs_codec.models.decode_options.DecodeOptions.charset>` will behave as the default charset
rather than the authoritative charset.

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'utf8=%E2%9C%93&a=%C3%B8',
       qs.DecodeOptions(
           charset=qs.Charset.LATIN1,
           charset_sentinel=True,
       ),
   ) == {'a': 'ø'}

   assert qs.decode(
       'utf8=%26%2310003%3B&a=%F8',
       qs.DecodeOptions(
           charset=qs.Charset.UTF8,
           charset_sentinel=True,
       ),
   ) == {'a': 'ø'}

If you want to decode the `&#...; <https://www.w3schools.com/html/html_entities.asp>`_ syntax to the actual character, you can specify the
:py:attr:`interpret_numeric_entities <qs_codec.models.decode_options.DecodeOptions.interpret_numeric_entities>`
option as well:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a=%26%239786%3B',
       qs.DecodeOptions(
           charset=qs.Charset.LATIN1,
           interpret_numeric_entities=True,
       ),
   ) == {'a': '☺'}

It also works when the charset has been detected in
:py:attr:`charset_sentinel <qs_codec.models.decode_options.DecodeOptions.charset_sentinel>` mode.

lists
^^^^^

:py:attr:`decode <qs_codec.decode>` can also decode ``list``\ s using a similar ``[]`` notation:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[]=b&a[]=c') == {'a': ['b', 'c']}

You may specify an index as well:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[1]=c&a[0]=b') == {'a': ['b', 'c']}

Note that the only difference between an index in a ``list`` and a key
in a ``dict`` is that the value between the brackets must be a number to
create a ``list``. When creating ``list``\ s with specific indices,
:py:attr:`decode <qs_codec.decode>` will compact a sparse ``list`` to
only the existing values preserving their order:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[1]=b&a[15]=c') == {'a': ['b', 'c']}

Note that an empty ``str``\ing is also a value and will be preserved:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[]=&a[]=b') == {'a': ['', 'b']}

   assert qs.decode('a[0]=b&a[1]=&a[2]=c') == {'a': ['b', '', 'c']}

:py:attr:`decode <qs_codec.decode>` will also limit specifying indices
in a ``list`` to a maximum index of ``20``. Any ``list`` members with an
index of greater than ``20`` will instead be converted to a ``dict`` with
the index as the key. This is needed to handle cases when someone sent,
for example, ``a[999999999]`` and it will take significant time to iterate
over this huge ``list``.

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[100]=b') == {'a': {'100': 'b'}}

This limit can be overridden by passing an :py:attr:`list_limit <qs_codec.models.decode_options.DecodeOptions.list_limit>`
option:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a[1]=b',
       qs.DecodeOptions(list_limit=0),
   ) == {'a': {'1': 'b'}}

To disable ``list`` parsing entirely, set :py:attr:`parse_lists <qs_codec.models.decode_options.DecodeOptions.parse_lists>`
to ``False``.

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a[]=b',
       qs.DecodeOptions(parse_lists=False),
   ) == {'a': {'0': 'b'}}

If you mix notations, :py:attr:`decode <qs_codec.decode>` will merge the two items into a ``dict``:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[0]=b&a[b]=c') == {'a': {'0': 'b', 'b': 'c'}}

You can also create ``list``\ s of ``dict``\ s:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[][b]=c') == {'a': [{'b': 'c'}]}

(:py:attr:`decode <qs_codec.decode>` *cannot convert nested ``dict``\ s, such as ``'a={b:1},{c:d}'``*)

primitive values (``int``, ``bool``, ``None``, etc.)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, all values are parsed as ``str``\ings.

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a=15&b=true&c=null',
   ) == {'a': '15', 'b': 'true', 'c': 'null'}

Encoding
~~~~~~~~

When encoding, :py:attr:`encode <qs_codec.encode>` by default URI encodes output. ``dict``\ s are
encoded as you would expect:

.. code:: python

   import qs_codec as qs

   assert qs.encode({'a': 'b'}) == 'a=b'
   assert qs.encode({'a': {'b': 'c'}}) == 'a%5Bb%5D=c'

This encoding can be disabled by setting the :py:attr:`encode <qs_codec.models.encode_options.EncodeOptions.encode>`
option to ``False``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': {'b': 'c'}},
       qs.EncodeOptions(encode=False),
   ) == 'a[b]=c'

Encoding can be disabled for keys by setting the
:py:attr:`encode_values_only <qs_codec.models.encode_options.EncodeOptions.encode_values_only>` option to ``True``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {
           'a': 'b',
           'c': ['d', 'e=f'],
           'f': [
               ['g'],
               ['h']
           ]
       },
       qs.EncodeOptions(encode_values_only=True)
   ) == 'a=b&c[0]=d&c[1]=e%3Df&f[0][0]=g&f[1][0]=h'

This encoding can also be replaced by a custom ``Callable`` in the
:py:attr:`encoder <qs_codec.models.encode_options.EncodeOptions.encoder>` option:

.. code:: python

   import qs_codec as qs
   import typing as t

   def custom_encoder(
       value: str,
       charset: t.Optional[qs.Charset],
       format: t.Optional[qs.Format],
   ) -> str:
       if value == 'č':
           return 'c'
       return value


   assert qs.encode(
       {'a': {'b': 'č'}},
       qs.EncodeOptions(encoder=custom_encoder),
   ) == 'a[b]=c'

(Note: the :py:attr:`encoder <qs_codec.models.encode_options.EncodeOptions.encoder>` option does not apply if
:py:attr:`encode <qs_codec.models.encode_options.EncodeOptions.encode>` is ``False``).

Similar to :py:attr:`encoder <qs_codec.models.encode_options.EncodeOptions.encoder>` there is a
:py:attr:`decoder <qs_codec.models.decode_options.DecodeOptions.decoder>` option for :py:attr:`decode <qs_codec.decode>`
to override decoding of properties and values:

.. code:: python

   import qs_codec as qs
   import typing as t

   def custom_decoder(
       value: t.Any,
       charset: t.Optional[qs.Charset],
   ) -> t.Union[int, str]:
       try:
           return int(value)
       except ValueError:
           return value

   assert qs.decode(
       'foo=123',
       qs.DecodeOptions(decoder=custom_decoder),
   ) == {'foo': 123}

Examples beyond this point will be shown as though the output is not URI
encoded for clarity. Please note that the return values in these cases
*will* be URI encoded during real usage.

When ``list``\s are encoded, they follow the
:py:attr:`list_format <qs_codec.models.encode_options.EncodeOptions.list_format>` option, which defaults to
:py:attr:`INDICES <qs_codec.enums.list_format.ListFormat.INDICES>`:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': ['b', 'c', 'd']},
       qs.EncodeOptions(encode=False)
   ) == 'a[0]=b&a[1]=c&a[2]=d'

You may override this by setting the :py:attr:`indices <qs_codec.models.encode_options.EncodeOptions.indices>` option to
``False``, or to be more explicit, the :py:attr:`list_format <qs_codec.models.encode_options.EncodeOptions.list_format>`
option to :py:attr:`REPEAT <qs_codec.enums.list_format.ListFormat.REPEAT>`:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': ['b', 'c', 'd']},
       qs.EncodeOptions(
           encode=False,
           indices=False,
       ),
   ) == 'a=b&a=c&a=d'

You may use the :py:attr:`list_format <qs_codec.models.encode_options.EncodeOptions.list_format>` option to specify the
format of the output ``list``:

.. code:: python

   import qs_codec as qs

   # ListFormat.INDICES
   assert qs.encode(
       {'a': ['b', 'c']},
       qs.EncodeOptions(
           encode=False,
           list_format=qs.ListFormat.INDICES,
       ),
   ) == 'a[0]=b&a[1]=c'

   # ListFormat.BRACKETS
   assert qs.encode(
       {'a': ['b', 'c']},
       qs.EncodeOptions(
           encode=False,
           list_format=qs.ListFormat.BRACKETS,
       ),
   ) == 'a[]=b&a[]=c'

   # ListFormat.REPEAT
   assert qs.encode(
       {'a': ['b', 'c']},
       qs.EncodeOptions(
           encode=False,
           list_format=qs.ListFormat.REPEAT,
       ),
   ) == 'a=b&a=c'

   # ListFormat.COMMA
   assert qs.encode(
       {'a': ['b', 'c']},
       qs.EncodeOptions(
           encode=False,
           list_format=qs.ListFormat.COMMA,
       ),
   ) == 'a=b,c'

**Note:** When using :py:attr:`list_format <qs_codec.models.encode_options.EncodeOptions.list_format>` set to
:py:attr:`COMMA <qs_codec.enums.list_format.ListFormat.COMMA>`, you can also pass the
:py:attr:`comma_round_trip <qs_codec.models.encode_options.EncodeOptions.comma_round_trip>` option set to ``True`` or
``False``, to append ``[]`` on single-item ``list``\ s so they can round-trip through a decoding.

:py:attr:`BRACKETS <qs_codec.enums.list_format.ListFormat.BRACKETS>` notation is used for encoding ``dict``\s by default:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': {'b': {'c': 'd', 'e': 'f'}}},
       qs.EncodeOptions(encode=False),
   ) == 'a[b][c]=d&a[b][e]=f'

You may override this to use dot notation by setting the
:py:attr:`allow_dots <qs_codec.models.encode_options.EncodeOptions.allow_dots>` option to ``True``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': {'b': {'c': 'd', 'e': 'f'}}},
       qs.EncodeOptions(encode=False, allow_dots=True),
   ) == 'a.b.c=d&a.b.e=f'

You may encode dots in keys of ``dict``\s by setting
:py:attr:`encode_dot_in_keys <qs_codec.models.encode_options.EncodeOptions.encode_dot_in_keys>` to ``True``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'name.obj': {'first': 'John', 'last': 'Doe'}},
       qs.EncodeOptions(
           allow_dots=True,
           encode_dot_in_keys=True,
       ),
   ) == 'name%252Eobj.first=John&name%252Eobj.last=Doe'

**Caveat:** When both :py:attr:`encode_values_only <qs_codec.models.encode_options.EncodeOptions.encode_values_only>`
and :py:attr:`encode_dot_in_keys <qs_codec.models.encode_options.EncodeOptions.encode_dot_in_keys>` are set to
``True``, only dots in keys and nothing else will be encoded!

You may allow empty ``list`` values by setting the
:py:attr:`allow_empty_lists <qs_codec.models.encode_options.EncodeOptions.allow_empty_lists>` option to ``True``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'foo': [], 'bar': 'baz', },
       qs.EncodeOptions(
           encode=False,
           allow_empty_lists=True,
       ),
   ) == 'foo[]&bar=baz'

Empty ``str``\ings and ``None`` values will be omitted, but the equals sign (``=``) remains in place:

.. code:: python

   import qs_codec as qs

   assert qs.encode({'a': ''}) == 'a='

Keys with no values (such as an empty ``dict`` or ``list``) will return nothing:

.. code:: python

   import qs_codec as qs

   assert qs.encode({'a': []}) == ''

   assert qs.encode({'a': {}}) == ''

   assert qs.encode({'a': [{}]}) == ''

   assert qs.encode({'a': {'b': []}}) == ''

   assert qs.encode({'a': {'b': {}}}) == ''

:py:attr:`Undefined <qs_codec.models.undefined.Undefined>` properties will be omitted entirely:

.. code:: python

   import qs_codec as qs

   assert qs.encode({'a': None, 'b': qs.Undefined()}) == 'a='

The query string may optionally be prepended with a question mark (``?``) by setting
:py:attr:`add_query_prefix <qs_codec.models.encode_options.EncodeOptions.add_query_prefix>` to ``True``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'b', 'c': 'd'},
       qs.EncodeOptions(add_query_prefix=True),
   ) == '?a=b&c=d'

The :py:attr:`delimiter <qs_codec.models.encode_options.EncodeOptions.delimiter>` may be overridden as well:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'b', 'c': 'd', },
       qs.EncodeOptions(delimiter=';')
   ) == 'a=b;c=d'

If you only want to override the serialization of `datetime <https://docs.python.org/3/library/datetime.html#datetime-objects>`_
objects, you can provide a ``Callable`` in the
:py:attr:`serialize_date <qs_codec.models.encode_options.EncodeOptions.serialize_date>` option:

.. code:: python

   import qs_codec as qs
   import datetime
   import sys

   # First case: encoding a datetime object to an ISO 8601 string
   assert (
       qs.encode(
           {
               "a": (
                   datetime.datetime.fromtimestamp(7, datetime.UTC)
                   if sys.version_info.major == 3 and sys.version_info.minor >= 11
                   else datetime.datetime.utcfromtimestamp(7)
               )
           },
           qs.EncodeOptions(encode=False),
       )
       == "a=1970-01-01T00:00:07+00:00"
       if sys.version_info.major == 3 and sys.version_info.minor >= 11
       else "a=1970-01-01T00:00:07"
   )

   # Second case: encoding a datetime object to a timestamp string
   assert (
       qs.encode(
           {
               "a": (
                   datetime.datetime.fromtimestamp(7, datetime.UTC)
                   if sys.version_info.major == 3 and sys.version_info.minor >= 11
                   else datetime.datetime.utcfromtimestamp(7)
               )
           },
           qs.EncodeOptions(encode=False, serialize_date=lambda date: str(int(date.timestamp()))),
       )
       == "a=7"
   )

To affect the order of parameter keys, you can set a ``Callable`` in the
:py:attr:`sort <qs_codec.models.encode_options.EncodeOptions.sort>` option:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'c', 'z': 'y', 'b': 'f'},
       qs.EncodeOptions(
           encode=False,
           sort=lambda a, b: (a > b) - (a < b)
       )
   ) == 'a=c&b=f&z=y'

Finally, you can use the :py:attr:`filter <qs_codec.models.encode_options.EncodeOptions.filter>` option to restrict
which keys will be included in the encoded output. If you pass a ``Callable``, it will be called for each key to obtain
the replacement value. Otherwise, if you pass a ``list``, it will be used to select properties and ``list`` indices to
be encoded:

.. code:: python

   import qs_codec as qs
   import datetime
   import sys

   # First case: using a Callable as filter
   assert (
       qs.encode(
           {
               "a": "b",
               "c": "d",
               "e": {
                   "f": (
                       datetime.datetime.fromtimestamp(123, datetime.UTC)
                       if sys.version_info.major == 3 and sys.version_info.minor >= 11
                       else datetime.datetime.utcfromtimestamp(123)
                   ),
                   "g": [2],
               },
           },
           qs.EncodeOptions(
               encode=False,
               filter=lambda prefix, value: {
                   "b": None,
                   "e[f]": int(value.timestamp()) if isinstance(value, datetime.datetime) else value,
                   "e[g][0]": value * 2 if isinstance(value, int) else value,
               }.get(prefix, value),
           ),
       )
       == "a=b&c=d&e[f]=123&e[g][0]=4"
   )

   # Second case: using a list as filter
   assert qs.encode(
       {'a': 'b', 'c': 'd', 'e': 'f'},
       qs.EncodeOptions(
           encode=False,
           filter=['a', 'e']
       )
   ) == 'a=b&e=f'

   # Third case: using a list as filter with indices
   assert qs.encode(
       {
           'a': ['b', 'c', 'd'],
           'e': 'f',
       },
       qs.EncodeOptions(
           encode=False,
           filter=['a', 0, 2]
       )
   ) == 'a[0]=b&a[2]=d'

Handling ``None`` values
~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, ``None`` values are treated like empty ``str``\ings:

.. code:: python

   import qs_codec as qs

   assert qs.encode({'a': None, 'b': ''}) == 'a=&b='

To distinguish between ``None`` values and empty ``str``\s use the
:py:attr:`strict_null_handling <qs_codec.models.encode_options.EncodeOptions.strict_null_handling>` flag.
In the result string the ``None`` values have no ``=`` sign:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': None, 'b': ''},
       qs.EncodeOptions(strict_null_handling=True),
   ) == 'a&b='

To decode values without ``=`` back to ``None`` use the
:py:attr:`strict_null_handling <qs_codec.models.decode_options.DecodeOptions.strict_null_handling>` flag:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a&b=',
       qs.DecodeOptions(strict_null_handling=True),
   ) == {'a': None, 'b': ''}

To completely skip rendering keys with ``None`` values, use the
:py:attr:`skip_nulls <qs_codec.models.encode_options.EncodeOptions.skip_nulls>` flag:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'b', 'c': None},
       qs.EncodeOptions(skip_nulls=True),
   ) == 'a=b'

If you’re communicating with legacy systems, you can switch to
:py:attr:`LATIN1 <qs_codec.enums.charset.Charset.LATIN1>` using the
:py:attr:`charset <qs_codec.models.encode_options.EncodeOptions.charset>` option:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'æ': 'æ'},
       qs.EncodeOptions(charset=qs.Charset.LATIN1)
   ) == '%E6=%E6'

Characters that don’t exist in :py:attr:`LATIN1 <qs_codec.enums.charset.Charset.LATIN1>`
will be converted to numeric entities, similar to what browsers do:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': '☺'},
       qs.EncodeOptions(charset=qs.Charset.LATIN1)
   ) == 'a=%26%239786%3B'

You can use the :py:attr:`charset_sentinel <qs_codec.models.encode_options.EncodeOptions.charset_sentinel>`
option to announce the character by including an ``utf8=✓`` parameter with the proper
encoding of the checkmark, similar to what Ruby on Rails and others do when submitting forms.

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': '☺'},
       qs.EncodeOptions(charset_sentinel=True)
   ) == 'utf8=%E2%9C%93&a=%E2%98%BA'

   assert qs.encode(
       {'a': 'æ'},
       qs.EncodeOptions(charset=qs.Charset.LATIN1, charset_sentinel=True)
   ) == 'utf8=%26%2310003%3B&a=%E6'

Dealing with special character sets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the encoding and decoding of characters is done in
:py:attr:`UTF8 <qs_codec.enums.charset.Charset.UTF8>`, and
:py:attr:`LATIN1 <qs_codec.enums.charset.Charset.LATIN1>` support is also built in via
the :py:attr:`charset <qs_codec.models.encode_options.EncodeOptions.charset>`
and :py:attr:`charset <qs_codec.models.decode_options.DecodeOptions.charset>` parameter,
respectively.

If you wish to encode query strings to a different character set (i.e.
`Shift JIS <https://en.wikipedia.org/wiki/Shift_JIS>`__)

.. code:: python

   import qs_codec as qs
   import codecs
   import typing as t

   def custom_encoder(
       string: str,
       charset: t.Optional[qs.Charset],
       format: t.Optional[qs.Format],
   ) -> str:
       if string:
           buf: bytes = codecs.encode(string, 'shift_jis')
           result: t.List[str] = ['{:02x}'.format(b) for b in buf]
           return '%' + '%'.join(result)
       return ''

   assert qs.encode(
       {'a': 'こんにちは！'},
       qs.EncodeOptions(encoder=custom_encoder)
   ) == '%61=%82%b1%82%f1%82%c9%82%bf%82%cd%81%49'

This also works for decoding of query strings:

.. code:: python

   import qs_codec as qs
   import re
   import codecs
   import typing as t

   def custom_decoder(
       string: str,
       charset: t.Optional[qs.Charset],
   ) -> t.Optional[str]:
       if string:
           result: t.List[int] = []
           while string:
               match: t.Optional[t.Match[str]] = re.search(r'%([0-9A-F]{2})', string, re.IGNORECASE)
               if match:
                   result.append(int(match.group(1), 16))
                   string = string[match.end():]
               else:
                   break
           buf: bytes = bytes(result)
           return codecs.decode(buf, 'shift_jis')
       return None

   assert qs.decode(
       '%61=%82%b1%82%f1%82%c9%82%bf%82%cd%81%49',
       qs.DecodeOptions(decoder=custom_decoder)
   ) == {'a': 'こんにちは！'}

RFC 3986 and RFC 1738 space encoding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The default :py:attr:`format <qs_codec.models.encode_options.EncodeOptions.format>` is
:py:attr:`RFC3986 <qs_codec.enums.format.Format.RFC3986>` which encodes
``' '`` to ``%20`` which is backward compatible. You can also set the
:py:attr:`format <qs_codec.models.encode_options.EncodeOptions.format>` to
:py:attr:`RFC1738 <qs_codec.enums.format.Format.RFC1738>` which encodes ``' '`` to ``+``.

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'b c'},
       qs.EncodeOptions(format=qs.Format.RFC3986)
   ) == 'a=b%20c'

   assert qs.encode(
       {'a': 'b c'},
       qs.EncodeOptions(format=qs.Format.RFC1738)
   ) == 'a=b+c'
