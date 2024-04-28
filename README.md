# qs_codec

A query string encoding and decoding library for Python.

Ported from [qs](https://www.npmjs.com/package/qs) for JavaScript.

[![PyPI - Version](https://img.shields.io/pypi/v/qs_codec)](https://pypi.org/project/qs-codec/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/qs_codec)](https://pypistats.org/packages/qs-codec)
![PyPI - Status](https://img.shields.io/pypi/status/qs_codec)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/qs_codec)
![PyPI - Format](https://img.shields.io/pypi/format/qs_codec)
[![Test](https://github.com/techouse/qs_codec/actions/workflows/test.yml/badge.svg)](https://github.com/techouse/qs_codec/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/techouse/qs_codec/graph/badge.svg?token=Vp0z05yj2l)](https://codecov.io/gh/techouse/qs_codec)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/7ead208221ae4f6785631043064647e4)](https://app.codacy.com/gh/techouse/qs_codec/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![GitHub](https://img.shields.io/github/license/techouse/qs_codec)](LICENSE)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/techouse)](https://github.com/sponsors/techouse)
[![GitHub Repo stars](https://img.shields.io/github/stars/techouse/qs_codec)](https://github.com/techouse/qs_codec/stargazers)

## Usage

A simple usage example:

```python
import qs_codec

# Encoding
assert qs_codec.encode({'a': 'b'}) == 'a=b'

# Decoding
assert qs_codec.decode('a=b') == {'a': 'b'}
```

### Decoding dictionaries

```python
import qs_codec, typing as t


def decode(
    value: t.Optional[t.Union[str, t.Mapping]],
    options: qs_codec.DecodeOptions = qs_codec.DecodeOptions(),
) -> dict:
    """Decodes a str or Mapping into a Dict. 
    
    Providing custom DecodeOptions will override the default behavior."""
    pass
```

**qs_codec** allows you to create nested `dict`s within your query strings, by surrounding the name of sub-keys with 
square brackets `[]`. For example, the string `'foo[bar]=baz'` converts to:

```python
import qs_codec

assert qs_codec.decode('foo[bar]=baz') == {'foo': {'bar': 'baz'}}
```

URI encoded strings work too:

```python
import qs_codec

assert qs_codec.decode('a%5Bb%5D=c') == {'a': {'b': 'c'}}
```

You can also nest your `dict`s, like 'foo[bar][baz]=foobarbaz':

```python
import qs_codec

assert qs_codec.decode('foo[bar][baz]=foobarbaz') == {'foo': {'bar': {'baz': 'foobarbaz'}}}
```

By default, when nesting `dict`s qs will only decode up to 5 children deep. This means if you attempt to decode a string 
like `'a[b][c][d][e][f][g][h][i]=j'` your resulting `dict` will be:

```python
import qs_codec

assert qs_codec.decode("a[b][c][d][e][f][g][h][i]=j") == {
    "a": {"b": {"c": {"d": {"e": {"f": {"[g][h][i]": "j"}}}}}}
}
```

This depth can be overridden by passing a depth option to `DecodeOptions.depth`:

```python
import qs_codec

assert qs_codec.decode(
    'a[b][c][d][e][f][g][h][i]=j',
    qs_codec.DecodeOptions(depth=1),
) == {'a': {'b': {'[c][d][e][f][g][h][i]': 'j'}}}
```

The depth limit helps mitigate abuse when **qs_codec** is used to parse user input, and it is recommended to keep it a
reasonably small number.

For similar reasons, by default **qs_codec** will only parse up to 1000 parameters. This can be overridden by passing 
a `DecodeOptions.parameter_limit` option:

```python
import qs_codec

assert qs_codec.decode(
    'a=b&c=d',
    qs_codec.DecodeOptions(parameter_limit=1),
) == {'a': 'b'}
```

To bypass the leading question mark, use `DecodeOptions.ignore_query_prefix`:

```python
import qs_codec

assert qs_codec.decode(
    '?a=b&c=d',
    qs_codec.DecodeOptions(ignore_query_prefix=True),
) == {'a': 'b', 'c': 'd'}
```

An optional `DecodeOptions.delimiter` can also be passed:

```python
import qs_codec

assert qs_codec.decode(
    'a=b;c=d',
    qs_codec.DecodeOptions(delimiter=';'),
) == {'a': 'b', 'c': 'd'}
```

`DecodeOptions.delimiter` can be a regular expression too:

```python
import re, qs_codec

assert qs_codec.decode(
    'a=b;c=d',
    qs_codec.DecodeOptions(delimiter=re.compile(r'[;,]')),
) == {'a': 'b', 'c': 'd'}
```

Option `DecodeOptions.allow_dots` can be used to enable dot notation:

```python
import qs_codec

assert qs_codec.decode(
    'a.b=c',
    qs_codec.DecodeOptions(allow_dots=True),
) == {'a': {'b': 'c'}}
```

Option `DecodeOptions.decode_dot_in_keys` can be used to decode dots in keys.

**Note:** it implies `DecodeOptions.allow_dots`, so `decode` will error if you set `DecodeOptions.decode_dot_in_keys` 
to `True`, and `DecodeOptions.allow_dots` to `False`.

```python
import qs_codec

assert qs_codec.decode(
    'name%252Eobj.first=John&name%252Eobj.last=Doe',
    qs_codec.DecodeOptions(decode_dot_in_keys=True),
) == {'name.obj': {'first': 'John', 'last': 'Doe'}}
```

Option `DecodeOptions.allow_empty_lists` can be used to allowing empty `list` values in `dict`

```python
import qs_codec

assert qs_codec.decode(
    'foo[]&bar=baz',
    qs_codec.DecodeOptions(allow_empty_lists=True),
) == {'foo': [], 'bar': 'baz'}
```

Option `DecodeOptions.duplicates` can be used to change the behavior when duplicate keys are encountered

```python
import qs_codec

assert qs_codec.decode('foo=bar&foo=baz') == {'foo': ['bar', 'baz']}

assert qs_codec.decode(
    'foo=bar&foo=baz',
    qs_codec.DecodeOptions(duplicates=qs_codec.Duplicates.COMBINE),
) == {'foo': ['bar', 'baz']}

assert qs_codec.decode(
    'foo=bar&foo=baz',
    qs_codec.DecodeOptions(duplicates=qs_codec.Duplicates.FIRST),
) == {'foo': 'bar'}

assert qs_codec.decode(
    'foo=bar&foo=baz',
    qs_codec.DecodeOptions(duplicates=qs_codec.Duplicates.LAST),
) == {'foo': 'baz'}
```

If you have to deal with legacy browsers or services, there's also support for decoding percent-encoded octets as
`Charset.LATIN1`:

```python
import qs_codec

assert qs_codec.decode(
    'a=%A7',
    qs_codec.DecodeOptions(charset=qs_codec.Charset.LATIN1),
) == {'a': '§'}
```

Some services add an initial `utf8=✓` value to forms so that old Internet Explorer versions are more likely to submit the
form as utf-8. Additionally, the server can check the value against wrong encodings of the checkmark character and detect 
that a query string or `application/x-www-form-urlencoded` body was *not* sent as utf-8, eg. if the form had an 
`accept-charset` parameter or the containing page had a different character set.

**qs_codec** supports this mechanism via the `DecodeOptions.charset_sentinel` option.
If specified, the `utf8` parameter will be omitted from the returned `dict`.
It will be used to switch to `Charset.LATIN1`/`Charset.UTF8` mode depending on how the checkmark is encoded.

**Important**: When you specify both the `DecodeOptions.charset` option and the `DecodeOptions.charset_sentinel` option, 
the `DecodeOptions.charset` will be overridden when the request contains a `utf8` parameter from which the actual charset 
can be deduced. In that sense the `DecodeOptions.charset` will behave as the default charset rather than the authoritative 
charset.

```python
import qs_codec

assert qs_codec.decode(
    'utf8=%E2%9C%93&a=%C3%B8',
    qs_codec.DecodeOptions(
        charset=qs_codec.Charset.LATIN1,
        charset_sentinel=True,
    ),
) == {'a': 'ø'}

assert qs_codec.decode(
    'utf8=%26%2310003%3B&a=%F8',
    qs_codec.DecodeOptions(
        charset=qs_codec.Charset.UTF8,
        charset_sentinel=True,
    ),
) == {'a': 'ø'}
```

If you want to decode the `&#...;` syntax to the actual character, you can specify the
`DecodeOptions.interpret_numeric_entities` option as well:

```python
import qs_codec

assert qs_codec.decode(
    'a=%26%239786%3B',
    qs_codec.DecodeOptions(
        charset=qs_codec.Charset.LATIN1,
        interpret_numeric_entities=True,
    ),
) == {'a': '☺'}
```

It also works when the charset has been detected in `DecodeOptions.charset_sentinel` mode.

### Decoding `list`s

**qs_codec** can also decode `list`s using a similar `[]` notation:

```python
import qs_codec

assert qs_codec.decode('a[]=b&a[]=c') == {'a': ['b', 'c']}
```

You may specify an index as well:

```python
import qs_codec

assert qs_codec.decode('a[1]=c&a[0]=b') == {'a': ['b', 'c']}
```

Note that the only difference between an index in a `list` and a key in a `dict` is that the value between the brackets
must be a number to create a `list`. When creating `list`s with specific indices, **qs_codec** will compact a sparse 
`list` to only the existing values preserving their order:

```python
import qs_codec

assert qs_codec.decode('a[1]=b&a[15]=c') == {'a': ['b', 'c']}
```

Note that an empty string is also a value, and will be preserved:

```python
import qs_codec

assert qs_codec.decode('a[]=&a[]=b') == {'a': ['', 'b']}

assert qs_codec.decode('a[0]=b&a[1]=&a[2]=c') == {'a': ['b', '', 'c']}
```

**qs_codec** will also limit specifying indices in a `list` to a maximum index of `20`.
Any `list` members with an index of greater than `20` will instead be converted to a `dict` with the index as the key.
This is needed to handle cases when someone sent, for example, `a[999999999]` and it will take significant time to iterate 
over this huge `list`.

```python
import qs_codec

assert qs_codec.decode('a[100]=b') == {'a': {100: 'b'}}
```

This limit can be overridden by passing an `DecodeOptions.list_limit` option:

```python
import qs_codec

assert qs_codec.decode('a[1]=b', qs_codec.DecodeOptions(list_limit=0)) == {'a': {1: 'b'}}
```

To disable List parsing entirely, set `DecodeOptions.parse_lists` to `False`.

```python
import qs_codec

assert qs_codec.decode('a[]=b', qs_codec.DecodeOptions(parse_lists=False)) == {'a': {0: 'b'}}
```

If you mix notations, **qs_codec** will merge the two items into a `dict`:

```python
import qs_codec

assert qs_codec.decode('a[0]=b&a[b]=c') == {'a': {0: 'b', 'b': 'c'}}
```

You can also create `list`s of `dict`s:

```python
import qs_codec

assert qs_codec.decode('a[][b]=c') == {'a': [{'b': 'c'}]}
```

(_**qs_codec** cannot convert nested `dict`s, such as `'a={b:1},{c:d}'`_)

### Decoding primitive/scalar values (`int`, `float`, `bool`, `None`, etc.)

By default, all values are parsed as `str`ings.

```python
import qs_codec

assert qs_codec.decode('a=15&b=true&c=null') == {'a': '15', 'b': 'true', 'c': 'null'}
```

### Encoding

```python
import qs_codec, typing as t


def encode(
    value: t.Any,
    options: qs_codec.EncodeOptions = qs_codec.EncodeOptions()
) -> str:
    """Encodes an object into a query string.
    
    Providing custom EncodeOptions will override the default behavior."""
    pass
```

When encoding, **qs_codec** by default URI encodes output. `dict`s are encoded as you would expect:

```python
import qs_codec

assert qs_codec.encode({'a': 'b'}) == 'a=b'
assert qs_codec.encode({'a': {'b': 'c'}}) == 'a%5Bb%5D=c'
```

This encoding can be disabled by setting the `EncodeOptions.encode` option to `False`:

```python
import qs_codec

assert qs_codec.encode(
    {'a': {'b': 'c'}},
    qs_codec.EncodeOptions(encode=False),
) == 'a[b]=c'
```

Encoding can be disabled for keys by setting the `EncodeOptions.encode_values_only` option to `True`:

```python
import qs_codec

assert qs_codec.encode(
    {
        'a': 'b',
        'c': ['d', 'e=f'],
        'f': [
            ['g'],
            ['h']
        ]
    },
    qs_codec.EncodeOptions(encode_values_only=True)
) == 'a=b&c[0]=d&c[1]=e%3Df&f[0][0]=g&f[1][0]=h'
```

This encoding can also be replaced by a custom `Callable` set in the `EncodeOptions.encoder` option:

```python
import qs_codec, typing as t


def custom_encoder(
    value: str,
    charset: t.Optional[qs_codec.Charset],
    format: t.Optional[qs_codec.Format],
) -> str:
    if value == 'č':
        return 'c'
    return value


assert qs_codec.encode(
    {'a': {'b': 'č'}},
    qs_codec.EncodeOptions(encoder=custom_encoder),
) == 'a[b]=c'
```

_(Note: the `EncodeOptions.encoder` option does not apply if `EncodeOptions.encode` is `False`)_

Similar to `EncodeOptions.encoder` there is a `DecodeOptions.decoder` option for `decode` to override decoding of 
properties and values:

```python
import qs_codec, typing as t

def custom_decoder(
    value: t.Any,
    charset: t.Optional[qs_codec.Charset],
) -> t.Union[int, str]:
    try:
        return int(value)
    except ValueError:
        return value

assert qs_codec.decode(
    'foo=123',
    qs_codec.DecodeOptions(decoder=custom_decoder),
) == {'foo': 123}
```

Examples beyond this point will be shown as though the output is not URI encoded for clarity.
Please note that the return values in these cases *will* be URI encoded during real usage.

When `list`s are encoded, they follow the `EncodeOptions.list_format` option, which defaults to `ListFormat.INDICES`:

```python
import qs_codec

assert qs_codec.encode(
    {'a': ['b', 'c', 'd']},
    qs_codec.EncodeOptions(encode=False)
) == 'a[0]=b&a[1]=c&a[2]=d'
```

You may override this by setting the `EncodeOptions.indices` option to `False`, or to be more explicit, the
`EncodeOptions.list_format` option to `ListFormat.REPEAT`:

```python
import qs_codec

assert qs_codec.encode(
    {'a': ['b', 'c', 'd']},
    qs_codec.EncodeOptions(
        encode=False,
        indices=False,
    ),
) == 'a=b&a=c&a=d'
```

You may use the `EncodeOptions.list_format` option to specify the format of the output `list`:

```python
import qs_codec

# ListFormat.INDICES
assert qs_codec.encode(
    {'a': ['b', 'c']},
    qs_codec.EncodeOptions(
        encode=False,
        list_format=qs_codec.ListFormat.INDICES,
    ),
) == 'a[0]=b&a[1]=c'

# ListFormat.BRACKETS
assert qs_codec.encode(
    {'a': ['b', 'c']},
    qs_codec.EncodeOptions(
        encode=False,
        list_format=qs_codec.ListFormat.BRACKETS,
    ),
) == 'a[]=b&a[]=c'

# ListFormat.REPEAT
assert qs_codec.encode(
    {'a': ['b', 'c']},
    qs_codec.EncodeOptions(
        encode=False,
        list_format=qs_codec.ListFormat.REPEAT,
    ),
) == 'a=b&a=c'

# ListFormat.COMMA
assert qs_codec.encode(
    {'a': ['b', 'c']},
    qs_codec.EncodeOptions(
        encode=False,
        list_format=qs_codec.ListFormat.COMMA,
    ),
) == 'a=b,c'
```

**Note:** When using `EncodeOptions.list_format` set to `ListFormat.COMMA`, you can also pass the `EncodeOptions.comma_round_trip`
option set to `True` or `False`, to append `[]` on single-item `list`s, so that they can round trip through a parse.

`ListFormat.BRACKETS` notation is used for encoding `dict`s by default:

```python
import qs_codec

assert qs_codec.encode(
    {'a': {'b': {'c': 'd', 'e': 'f'}}},
    qs_codec.EncodeOptions(encode=False),
) == 'a[b][c]=d&a[b][e]=f'
```

You may override this to use dot notation by setting the `EncodeOptions.allow_dots` option to `True`:

```python
import qs_codec

assert qs_codec.encode(
    {'a': {'b': {'c': 'd', 'e': 'f'}}},
    qs_codec.EncodeOptions(encode=False, allow_dots=True),
) == 'a.b.c=d&a.b.e=f'
```

You may encode dots in keys of `dict`s by setting `EncodeOptions.encode_dot_in_keys` to `True`:

```python
import qs_codec

assert qs_codec.encode(
    {'name.obj': {'first': 'John', 'last': 'Doe'}},
    qs_codec.EncodeOptions(
        allow_dots=True,
        encode_dot_in_keys=True,
    ),
) == 'name%252Eobj.first=John&name%252Eobj.last=Doe'
```

**Caveat:** When both `EncodeOptions.encode_values_only` and `EncodeOptions.encode_dot_in_keys` are set to `True`, only
dots in keys and nothing else will be encoded!

You may allow empty `list` values by setting the `EncodeOptions.allow_empty_lists` option to `True`:

```python
import qs_codec

assert qs_codec.encode(
    {'foo': [], 'bar': 'baz', },
    qs_codec.EncodeOptions(
        encode=False,
        allow_empty_lists=True,
    ),
) == 'foo[]&bar=baz'
```

Empty `str`ings and `None` values will be omitted, but the equals sign (`=`) remains in place:

```python
import qs_codec

assert qs_codec.encode({'a': ''}) == 'a='
```

Keys with no values (such as an empty `dict` or `list`) will return nothing:

```python
import qs_codec

assert qs_codec.encode({'a': []}) == ''

assert qs_codec.encode({'a': {}}) == ''

assert qs_codec.encode({'a': [{}]}) == ''

assert qs_codec.encode({'a': {'b': []}}) == ''

assert qs_codec.encode({'a': {'b': {}}}) == ''
```

`Undefined` properties will be omitted entirely:

```python
import qs_codec

assert qs_codec.encode({'a': None, 'b': qs_codec.Undefined()}) == 'a='
```

The query string may optionally be prepended with a question mark (`?`):

```python
import qs_codec

assert qs_codec.encode(
    {'a': 'b', 'c': 'd'},
    qs_codec.EncodeOptions(add_query_prefix=True),
) == '?a=b&c=d'
```

The delimiter may be overridden as well:

```python
import qs_codec

assert qs_codec.encode(
    {'a': 'b', 'c': 'd', },
    qs_codec.EncodeOptions(delimiter=';')
) == 'a=b;c=d'
```

If you only want to override the serialization of `datetime` objects, you can provide a custom `DateSerializer`
in the `EncodeOptions.serialize_date` option:

```python
import qs_codec, datetime, sys

# First case: encoding a datetime object to an ISO 8601 string
assert (
    qs_codec.encode(
        {
            "a": (
                datetime.datetime.fromtimestamp(7, datetime.UTC)
                if sys.version_info.major == 3 and sys.version_info.minor >= 11
                else datetime.datetime.utcfromtimestamp(7)
            )
        },
        qs_codec.EncodeOptions(encode=False),
    )
    == "a=1970-01-01T00:00:07+00:00"
    if sys.version_info.major == 3 and sys.version_info.minor >= 11
    else "a=1970-01-01T00:00:07"
)

# Second case: encoding a datetime object to a timestamp string
assert (
    qs_codec.encode(
        {
            "a": (
                datetime.datetime.fromtimestamp(7, datetime.UTC)
                if sys.version_info.major == 3 and sys.version_info.minor >= 11
                else datetime.datetime.utcfromtimestamp(7)
            )
        },
        qs_codec.EncodeOptions(encode=False, serialize_date=lambda date: str(int(date.timestamp()))),
    )
    == "a=7"
)
```

To affect the order of parameter keys, you can set a `Callable` in the `EncodeOptions.sort` option:

```python
import qs_codec

assert qs_codec.encode(
    {'a': 'c', 'z': 'y', 'b': 'f'},
    qs_codec.EncodeOptions(
        encode=False,
        sort=lambda a, b: (a > b) - (a < b)
    )
) == 'a=c&b=f&z=y'
```

Finally, you can use the `EncodeOptions.filter` option to restrict which keys will be included in the encoded output.
If you pass a `Callable`, it will be called for each key to obtain the replacement value.
Otherwise, if you pass a `list`, it will be used to select properties and `list` indices to be encoded:

```python
import qs_codec, datetime, sys

# First case: using a Callable as filter
assert (
    qs_codec.encode(
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
        qs_codec.EncodeOptions(
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
assert qs_codec.encode(
    {'a': 'b', 'c': 'd', 'e': 'f'},
    qs_codec.EncodeOptions(
        encode=False,
        filter=['a', 'e']
    )
) == 'a=b&e=f'

# Third case: using a list as filter with indices
assert qs_codec.encode(
    {
        'a': ['b', 'c', 'd'],
        'e': 'f',
    },
    qs_codec.EncodeOptions(
        encode=False,
        filter=['a', 0, 2]
    )
) == 'a[0]=b&a[2]=d'
```

### Handling `None` values

By default, `None` values are treated like empty `str`ings:

```python
import qs_codec

assert qs_codec.encode({'a': None, 'b': ''}) == 'a=&b='
```

To distinguish between `None` values and empty `str`s use the `EncodeOptions.strict_null_handling` flag. 
In the result string the `None` values have no `=` sign:

```python
import qs_codec

assert qs_codec.encode(
    {'a': None, 'b': ''},
    qs_codec.EncodeOptions(strict_null_handling=True),
) == 'a&b='
```

To decode values without `=` back to `None` use the `DecodeOptions.strict_null_handling` flag:

```python
import qs_codec

assert qs_codec.decode(
    'a&b=',
    qs_codec.DecodeOptions(strict_null_handling=True),
) == {'a': None, 'b': ''}
```

To completely skip rendering keys with `None` values, use the `EncodeOptions.skip_nulls` flag:

```python
import qs_codec

assert qs_codec.encode(
    {'a': 'b', 'c': None},
    qs_codec.EncodeOptions(skip_nulls=True),
) == 'a=b'
```

If you're communicating with legacy systems, you can switch to `Charset.LATIN1` using the `charset` option:

```python
import qs_codec

assert qs_codec.encode(
    {'æ': 'æ'},
    qs_codec.EncodeOptions(charset=qs_codec.Charset.LATIN1)
) == '%E6=%E6'
```

Characters that don't exist in `Charset.LATIN1` will be converted to numeric entities, similar to what browsers do:

```python
import qs_codec

assert qs_codec.encode(
    {'a': '☺'},
    qs_codec.EncodeOptions(charset=qs_codec.Charset.LATIN1)
) == 'a=%26%239786%3B'
```

You can use the `EncodeOptions.charset_sentinel` option to announce the character by including an `utf8=✓` parameter with
the proper encoding of the checkmark, similar to what Ruby on Rails and others do when submitting forms.

```python
import qs_codec

assert qs_codec.encode(
    {'a': '☺'},
    qs_codec.EncodeOptions(charset_sentinel=True)
) == 'utf8=%E2%9C%93&a=%E2%98%BA'

assert qs_codec.encode(
    {'a': 'æ'},
    qs_codec.EncodeOptions(charset=qs_codec.Charset.LATIN1, charset_sentinel=True)
) == 'utf8=%26%2310003%3B&a=%E6'
```

### Dealing with special character sets

By default, the encoding and decoding of characters is done in `Charset.UTF8`, and `Charset.LATIN1` support is also 
built in via the `EncodeOptions.charset` and `DecodeOptions.charset` parameter, respectively.

If you wish to encode query strings to a different character set (i.e.
[Shift JIS](https://en.wikipedia.org/wiki/Shift_JIS))

```python
import qs_codec, codecs, typing as t


def custom_encoder(
    string: str,
    charset: t.Optional[qs_codec.Charset],
    format: t.Optional[qs_codec.Format],
) -> str:
    if string:
        buf: bytes = codecs.encode(string, 'shift_jis')
        result: t.List[str] = ['{:02x}'.format(b) for b in buf]
        return '%' + '%'.join(result)
    return ''

assert qs_codec.encode(
    {'a': 'こんにちは！'},
    qs_codec.EncodeOptions(encoder=custom_encoder)
) == '%61=%82%b1%82%f1%82%c9%82%bf%82%cd%81%49'
```

This also works for decoding of query strings:

```python
import qs_codec, re, codecs, typing as t


def custom_decoder(
    string: str,
    charset: t.Optional[qs_codec.Charset],
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

assert qs_codec.decode(
    '%61=%82%b1%82%f1%82%c9%82%bf%82%cd%81%49',
    qs_codec.DecodeOptions(decoder=custom_decoder)
) == {'a': 'こんにちは！'}
```

### RFC 3986 and RFC 1738 space encoding

The default `EncodeOptions.format` is `Format.RFC3986` which encodes `' '` to `%20` which is backward compatible.
You can also set the `EncodeOptions.format` to `Format.RFC1738` which encodes `' '` to `+`.

```python
import qs_codec

assert qs_codec.encode(
    {'a': 'b c'},
    qs_codec.EncodeOptions(format=qs_codec.Format.RFC3986)
) == 'a=b%20c'

assert qs_codec.encode(
    {'a': 'b c'},
    qs_codec.EncodeOptions(format=qs_codec.Format.RFC3986)
) == 'a=b%20c'

assert qs_codec.encode(
    {'a': 'b c'},
    qs_codec.EncodeOptions(format=qs_codec.Format.RFC1738)
) == 'a=b+c'
```

---

Special thanks to the authors of [qs](https://www.npmjs.com/package/qs) for JavaScript:
- [Jordan Harband](https://github.com/ljharb)
- [TJ Holowaychuk](https://github.com/visionmedia/node-querystring)
