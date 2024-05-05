.. qs-codec documentation master file, created by
   sphinx-quickstart on Sun Apr 28 13:58:45 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

qs-codec
========

A query string encoding and decoding library for Python.

Ported from `qs <https://www.npmjs.com/package/qs>`__ for JavaScript.

|PyPI - Version| |PyPI - Downloads| |PyPI - Status| |PyPI - Python Version|
|PyPI - Format| |Black| |Test| |CodeQL| |Publish| |Docs| |codecov| |Codacy| |License|
|Contributor Covenant| |GitHub Sponsors| |GitHub Repo stars|

Usage
-----

A simple usage example:

.. code:: python

   import qs_codec

   # Encoding
   assert qs_codec.encode({'a': 'b'}) == 'a=b'

   # Decoding
   assert qs_codec.decode('a=b') == {'a': 'b'}

.. toctree::
   :maxdepth: 4
   :caption: Contents:

   README
   qs_codec

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

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