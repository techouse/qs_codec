qs-codec
========

A query string encoding and decoding library for Python.

Ported from `qs <https://www.npmjs.com/package/qs>`__ for JavaScript.

|PyPI - Version| |PyPI - Downloads| |PyPI - Status| |PyPI - Python Version| |PyPI - Format| |Black|
|Test| |CodeQL| |Publish| |Docs| |codecov| |Codacy| |Black| |flake8| |mypy| |pylint| |isort| |bandit|
|License| |Contributor Covenant| |GitHub Sponsors| |GitHub Repo stars|

Usage
-----

A simple usage example:

.. code:: python

   import qs_codec as qs

   # Encoding
   assert qs.encode({'a': 'b'}) == 'a=b'

   # Decoding
   assert qs.decode('a=b') == {'a': 'b'}

Decoding
~~~~~~~~

dictionaries
^^^^^^^^^^^^

.. code:: python

   import qs_codec as qs
   import typing as t

   def decode(
       value: t.Optional[t.Union[str, t.Dict[str, t.Any]]],
       options: qs.DecodeOptions = qs.DecodeOptions(),
   ) -> t.Dict[str, t.Any]:
       """Decodes a query string into a Dict[str, Any].
       
       Providing custom DecodeOptions will override the default behavior."""
       pass

`decode <https://techouse.github.io/qs_codec/qs_codec.html#module-qs_codec.decode>`__ allows you to create nested ``dict``\ s within your query
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

This depth can be overridden by setting the `depth <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.depth>`_:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a[b][c][d][e][f][g][h][i]=j',
       qs.DecodeOptions(depth=1),
   ) == {'a': {'b': {'[c][d][e][f][g][h][i]': 'j'}}}

You can configure `decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ to throw an error
when parsing nested input beyond this depth using `strict_depth <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.strict_depth>`__ (defaults to ``False``):

.. code:: python

   import qs_codec as qs

   try:
       qs.decode(
           'a[b][c][d][e][f][g][h][i]=j',
           qs.DecodeOptions(depth=1, strict_depth=True),
       )
   except IndexError as e:
       assert str(e) == 'Input depth exceeded depth option of 1 and strict_depth is True'

The depth limit helps mitigate abuse when `decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ is used to parse user
input, and it is recommended to keep it a reasonably small number. `strict_depth <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.strict_depth>`__
adds a layer of protection by throwing a ``IndexError`` when the limit is exceeded, allowing you to catch and handle such cases.

For similar reasons, by default `decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ will only parse up to 1000 parameters. This can be overridden by passing a
`parameter_limit <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.parameter_limit>`__ option:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a=b&c=d',
       qs.DecodeOptions(parameter_limit=1),
   ) == {'a': 'b'}

To bypass the leading question mark, use `ignore_query_prefix <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.ignore_query_prefix>`__:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       '?a=b&c=d',
       qs.DecodeOptions(ignore_query_prefix=True),
   ) == {'a': 'b', 'c': 'd'}

An optional `delimiter <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.delimiter>`__ can also be passed:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a=b;c=d',
       qs.DecodeOptions(delimiter=';'),
   ) == {'a': 'b', 'c': 'd'}

`delimiter <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.delimiter>`__ can be a regular expression too:

.. code:: python

   import qs_codec as qs
   import re

   assert qs.decode(
       'a=b;c=d',
       qs.DecodeOptions(delimiter=re.compile(r'[;,]')),
   ) == {'a': 'b', 'c': 'd'}

Option `allow_dots <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.allow_dots>`__
can be used to enable dot notation:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a.b=c',
       qs.DecodeOptions(allow_dots=True),
   ) == {'a': {'b': 'c'}}

Option `decode_dot_in_keys <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.decode_dot_in_keys>`__
can be used to decode dots in keys.

**Note:** it implies `allow_dots <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.allow_dots>`__, so
`decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ will error if you set `decode_dot_in_keys <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.decode_dot_in_keys>`__
to ``True``, and `allow_dots <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.allow_dots>`__ to ``False``.

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'name%252Eobj.first=John&name%252Eobj.last=Doe',
       qs.DecodeOptions(decode_dot_in_keys=True),
   ) == {'name.obj': {'first': 'John', 'last': 'Doe'}}

Option `allow_empty_lists <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.allow_empty_lists>`__ can
be used to allowing empty ``list`` values in a ``dict``

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'foo[]&bar=baz',
       qs.DecodeOptions(allow_empty_lists=True),
   ) == {'foo': [], 'bar': 'baz'}

Option `duplicates <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.duplicates>`__ can be used to
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
support for decoding percent-encoded octets as `LATIN1 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.charset.Charset.LATIN1>`__:

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

`decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ supports this mechanism via the
`charset_sentinel <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.charset_sentinel>`__ option.
If specified, the ``utf8`` parameter will be omitted from the returned
``dict``. It will be used to switch to `LATIN1 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.charset.Charset.LATIN1>`__ or
`UTF8 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.charset.Charset.UTF8>`__ mode depending on how the checkmark is encoded.

**Important**: When you specify both the `charset <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.charset>`__
option and the `charset_sentinel <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.charset_sentinel>`__ option, the
`charset <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.charset>`__ will be overridden when the request contains a
``utf8`` parameter from which the actual charset can be deduced. In that
sense the `charset <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.charset>`__ will behave as the default charset
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

If you want to decode the `&#...; <https://www.w3schools.com/html/html_entities.asp>`__ syntax to the actual character, you can specify the
`interpret_numeric_entities <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.interpret_numeric_entities>`__
option as well:

.. code:: python

   import qs_codec qs qs

   assert qs.decode(
       'a=%26%239786%3B',
       qs.DecodeOptions(
           charset=qs.Charset.LATIN1,
           interpret_numeric_entities=True,
       ),
   ) == {'a': '☺'}

It also works when the charset has been detected in
`charset_sentinel <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.charset_sentinel>`__ mode.

lists
^^^^^

`decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ can also decode ``list``\ s using a similar ``[]`` notation:

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
`decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ will compact a sparse ``list`` to
only the existing values preserving their order:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[1]=b&a[15]=c') == {'a': ['b', 'c']}

Note that an empty ``str``\ing is also a value, and will be preserved:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[]=&a[]=b') == {'a': ['', 'b']}

   assert qs.decode('a[0]=b&a[1]=&a[2]=c') == {'a': ['b', '', 'c']}

`decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ will also limit specifying indices
in a ``list`` to a maximum index of ``20``. Any ``list`` members with an
index of greater than ``20`` will instead be converted to a ``dict`` with
the index as the key. This is needed to handle cases when someone sent,
for example, ``a[999999999]`` and it will take significant time to iterate
over this huge ``list``.

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[100]=b') == {'a': {'100': 'b'}}

This limit can be overridden by passing an `list_limit <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.list_limit>`__
option:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a[1]=b',
       qs.DecodeOptions(list_limit=0),
   ) == {'a': {'1': 'b'}}

To disable ``list`` parsing entirely, set `parse_lists <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.parse_lists>`__
to ``False``.

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a[]=b',
       qs.DecodeOptions(parse_lists=False),
   ) == {'a': {'0': 'b'}}

If you mix notations, `decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ will merge the two items into a ``dict``:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[0]=b&a[b]=c') == {'a': {'0': 'b', 'b': 'c'}}

You can also create ``list``\ s of ``dict``\ s:

.. code:: python

   import qs_codec as qs

   assert qs.decode('a[][b]=c') == {'a': [{'b': 'c'}]}

(`decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__ *cannot convert nested ``dict``\ s, such as ``'a={b:1},{c:d}'``*)

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

.. code:: python

   import qs_codec as qs
   import typing as t

   def encode(
       value: t.Any,
       options: qs.EncodeOptions = qs.EncodeOptions()
   ) -> str:
       """Encodes an object into a query string.
       
       Providing custom EncodeOptions will override the default behavior."""
       pass

When encoding, `encode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.encode>`__ by default URI encodes output. ``dict``\ s are
encoded as you would expect:

.. code:: python

   import qs_codec as qs

   assert qs.encode({'a': 'b'}) == 'a=b'
   assert qs.encode({'a': {'b': 'c'}}) == 'a%5Bb%5D=c'

This encoding can be disabled by setting the `encode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encode>`__
option to ``False``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': {'b': 'c'}},
       qs.EncodeOptions(encode=False),
   ) == 'a[b]=c'

Encoding can be disabled for keys by setting the
`encode_values_only <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encode_values_only>`__ option to ``True``:

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
`encoder <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encoder>`__ option:

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

(Note: the `encoder <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encoder>`__ option does not apply if
`encode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encode>`__ is ``False``).

Similar to `encoder <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encoder>`__ there is a
`decoder <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.decoder>`__ option for `decode <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.decode>`__
to override decoding of properties and values:

.. code:: python

   import qs_codec as qs,
   typing as t

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
`list_format <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.list_format>`__ option, which defaults to
`INDICES <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.list_format.ListFormat.INDICES>`__:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': ['b', 'c', 'd']},
       qs.EncodeOptions(encode=False)
   ) == 'a[0]=b&a[1]=c&a[2]=d'

You may override this by setting the `indices <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.indices>`__ option to
``False``, or to be more explicit, the `list_format <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.list_format>`__
option to `REPEAT <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.list_format.ListFormat.REPEAT>`__:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': ['b', 'c', 'd']},
       qs.EncodeOptions(
           encode=False,
           indices=False,
       ),
   ) == 'a=b&a=c&a=d'

You may use the `list_format <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.list_format>`__ option to specify the
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

**Note:** When using `list_format <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.list_format>`__ set to
`COMMA <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.list_format.ListFormat.COMMA>`_, you can also pass the
`comma_round_trip <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.comma_round_trip>`__ option set to ``True`` or
``False``, to append ``[]`` on single-item ``list``\ s, so that they can round trip through a decoding.

`BRACKETS <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.list_format.ListFormat.BRACKETS>`__ notation is used for encoding ``dict``\s by default:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': {'b': {'c': 'd', 'e': 'f'}}},
       qs.EncodeOptions(encode=False),
   ) == 'a[b][c]=d&a[b][e]=f'

You may override this to use dot notation by setting the
`allow_dots <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.allow_dots>`__ option to ``True``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': {'b': {'c': 'd', 'e': 'f'}}},
       qs.EncodeOptions(encode=False, allow_dots=True),
   ) == 'a.b.c=d&a.b.e=f'

You may encode dots in keys of ``dict``\s by setting
`encode_dot_in_keys <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encode_dot_in_keys>`__ to ``True``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'name.obj': {'first': 'John', 'last': 'Doe'}},
       qs.EncodeOptions(
           allow_dots=True,
           encode_dot_in_keys=True,
       ),
   ) == 'name%252Eobj.first=John&name%252Eobj.last=Doe'

**Caveat:** When both `encode_values_only <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encode_values_only>`__
and `encode_dot_in_keys <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.encode_dot_in_keys>`__ are set to
``True``, only dots in keys and nothing else will be encoded!

You may allow empty ``list`` values by setting the
`allow_empty_lists <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.allow_empty_lists>`__ option to ``True``:

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

`Undefined <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.undefined.Undefined>`__ properties will be omitted entirely:

.. code:: python

   import qs_codec as qs

   assert qs.encode({'a': None, 'b': qs.Undefined()}) == 'a='

The query string may optionally be prepended with a question mark (``?``) by setting
`add_query_prefix <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.add_query_prefix>`__ to ``True``:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'b', 'c': 'd'},
       qs.EncodeOptions(add_query_prefix=True),
   ) == '?a=b&c=d'

The `delimiter <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.delimiter>`__ may be overridden as well:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'b', 'c': 'd', },
       qs.EncodeOptions(delimiter=';')
   ) == 'a=b;c=d'

If you only want to override the serialization of `datetime <https://docs.python.org/3/library/datetime.html#datetime-objects>`__
objects, you can provide a ``Callable`` in the
`serialize_date <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.serialize_date>`__ option:

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
`sort <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.sort>`__ option:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'c', 'z': 'y', 'b': 'f'},
       qs.EncodeOptions(
           encode=False,
           sort=lambda a, b: (a > b) - (a < b)
       )
   ) == 'a=c&b=f&z=y'

Finally, you can use the `filter <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.filter>`__ option to restrict
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
`strict_null_handling <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.strict_null_handling>`__ flag.
In the result string the ``None`` values have no ``=`` sign:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': None, 'b': ''},
       qs.EncodeOptions(strict_null_handling=True),
   ) == 'a&b='

To decode values without ``=`` back to ``None`` use the
`strict_null_handling <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.strict_null_handling>`__ flag:

.. code:: python

   import qs_codec as qs

   assert qs.decode(
       'a&b=',
       qs.DecodeOptions(strict_null_handling=True),
   ) == {'a': None, 'b': ''}

To completely skip rendering keys with ``None`` values, use the
`skip_nulls <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.skip_nulls>`__ flag:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'b', 'c': None},
       qs.EncodeOptions(skip_nulls=True),
   ) == 'a=b'

If you’re communicating with legacy systems, you can switch to
`LATIN1 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.charset.Charset.LATIN1>`__ using the
`charset <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.charset>`__ option:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'æ': 'æ'},
       qs.EncodeOptions(charset=qs.Charset.LATIN1)
   ) == '%E6=%E6'

Characters that don’t exist in `LATIN1 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.charset.Charset.LATIN1>`__
will be converted to numeric entities, similar to what browsers do:

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': '☺'},
       qs.EncodeOptions(charset=qs.Charset.LATIN1)
   ) == 'a=%26%239786%3B'

You can use the `charset_sentinel <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.charset_sentinel>`__
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
`UTF8 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.charset.Charset.UTF8>`__, and
`LATIN1 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.charset.Charset.LATIN1>`__ support is also built in via
the `charset <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.charset>`__
and `charset <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.decode_options.DecodeOptions.charset>`__ parameter,
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

The default `format <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.format>`__ is
`RFC3986 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.format.Format.RFC3986>`__ which encodes
``' '`` to ``%20`` which is backward compatible. You can also set the
`format <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.models.encode_options.EncodeOptions.format>`__ to
`RFC1738 <https://techouse.github.io/qs_codec/qs_codec.models.html#qs_codec.enums.format.Format.RFC1738>`__ which encodes ``' '`` to ``+``.

.. code:: python

   import qs_codec as qs

   assert qs.encode(
       {'a': 'b c'},
       qs.EncodeOptions(format=qs.Format.RFC3986)
   ) == 'a=b%20c'

   assert qs.encode(
       {'a': 'b c'},
       qs.EncodeOptions(format=qs.Format.RFC3986)
   ) == 'a=b%20c'

   assert qs.encode(
       {'a': 'b c'},
       qs.EncodeOptions(format=qs.Format.RFC1738)
   ) == 'a=b+c'

--------------

Special thanks to the authors of
`qs <https://www.npmjs.com/package/qs>`__ for JavaScript: - `Jordan
Harband <https://github.com/ljharb>`__ - `TJ
Holowaychuk <https://github.com/visionmedia/node-querystring>`__

.. |PyPI - Version| image:: https://img.shields.io/pypi/v/qs_codec
   :target: https://pypi.org/project/qs-codec/
.. |PyPI - Downloads| image:: https://img.shields.io/pypi/dm/qs_codec
   :target: https://pypistats.org/packages/qs-codec
.. |PyPI - Status| image:: https://img.shields.io/pypi/status/qs_codec
.. |PyPI - Python Version| image:: https://img.shields.io/pypi/pyversions/qs_codec
.. |PyPI - Format| image:: https://img.shields.io/pypi/format/qs_codec
.. |Test| image:: https://github.com/techouse/qs_codec/actions/workflows/test.yml/badge.svg
   :target: https://github.com/techouse/qs_codec/actions/workflows/test.yml
.. |CodeQL| image:: https://github.com/techouse/qs_codec/actions/workflows/github-code-scanning/codeql/badge.svg
   :target: https://github.com/techouse/qs_codec/actions/workflows/github-code-scanning/codeql
.. |Publish| image:: https://github.com/techouse/qs_codec/actions/workflows/publish.yml/badge.svg
   :target: https://github.com/techouse/qs_codec/actions/workflows/publish.yml
.. |Docs| image:: https://github.com/techouse/qs_codec/actions/workflows/docs.yml/badge.svg
   :target: https://github.com/techouse/qs_codec/actions/workflows/docs.yml
.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
.. |codecov| image:: https://codecov.io/gh/techouse/qs_codec/graph/badge.svg?token=Vp0z05yj2l
   :target: https://codecov.io/gh/techouse/qs_codec
.. |Codacy| image:: https://app.codacy.com/project/badge/Grade/7ead208221ae4f6785631043064647e4
   :target: https://app.codacy.com/gh/techouse/qs_codec/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade
.. |License| image:: https://img.shields.io/github/license/techouse/qs_codec
   :target: LICENSE
.. |GitHub Sponsors| image:: https://img.shields.io/github/sponsors/techouse
   :target: https://github.com/sponsors/techouse
.. |GitHub Repo stars| image:: https://img.shields.io/github/stars/techouse/qs_codec
   :target: https://github.com/techouse/qs_codec/stargazers
.. |Contributor Covenant| image:: https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg
   :target: CODE-OF-CONDUCT.md
.. |flake8| image:: https://img.shields.io/badge/flake8-checked-blueviolet.svg
   :target: https://flake8.pycqa.org/en/latest/
.. |mypy| image:: https://img.shields.io/badge/mypy-checked-blue.svg
   :target: https://mypy.readthedocs.io/en/stable/
.. |pylint| image:: https://img.shields.io/badge/linting-pylint-yellowgreen.svg
   :target: https://github.com/pylint-dev/pylint
.. |isort| image:: https://img.shields.io/badge/imports-isort-blue.svg
   :target: https://pycqa.github.io/isort/
.. |bandit| image:: https://img.shields.io/badge/security-bandit-blue.svg
   :target: https://github.com/PyCQA/bandit
   :alt: Security Status