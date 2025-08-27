.. qs-codec documentation master file, created by
   sphinx-quickstart on Sun Apr 28 13:58:45 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

qs-codec
========

.. image:: https://raw.githubusercontent.com/techouse/qs_codec/main/logo.png
   :alt: qs-codec
   :width: 256
   :align: center

A query string encoding and decoding library for Python.

Ported from `qs <https://www.npmjs.com/package/qs>`__ for JavaScript.

|PyPI - Version| |PyPI - Downloads| |PyPI - Status| |PyPI - Python Version| |PyPI - Format| |Black|
|Test| |CodeQL| |Publish| |Docs| |codecov| |Codacy| |flake8| |mypy| |pylint| |isort| |bandit|
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

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   README
   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

--------------

Other ports
-----------

+----------------------------+---------------------------------------------------------------+-----------------+
| Port                       | Repository                                                    | Package         |
+============================+===============================================================+=================+
| Dart                       | `techouse/qs <https://github.com/techouse/qs>`__              | |pubdev|        |
+----------------------------+---------------------------------------------------------------+-----------------+
| Kotlin / JVM + Android AAR | `techouse/qs-kotlin <https://github.com/techouse/qs-kotlin>`__| |maven-central| |
+----------------------------+---------------------------------------------------------------+-----------------+
| Swift / Objective-C        | `techouse/qs-swift <https://github.com/techouse/qs-swift>`__  | |spm|           |
+----------------------------+---------------------------------------------------------------+-----------------+
| .NET / C#                  | `techouse/qs-net <https://github.com/techouse/qs-net>`__      | |nuget|         |
+----------------------------+---------------------------------------------------------------+-----------------+
| Node.js (original)         | `ljharb/qs <https://github.com/ljharb/qs>`__                  | |npm|           |
+----------------------------+---------------------------------------------------------------+-----------------+

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
.. |pubdev| image:: https://img.shields.io/pub/v/qs_dart?logo=dart&label=pub.dev
   :target: https://pub.dev/packages/qs_dart
   :alt: pub.dev version
.. |maven-central| image:: https://img.shields.io/maven-central/v/io.github.techouse/qs-kotlin?logo=kotlin&label=Maven%20Central
   :target: https://central.sonatype.com/artifact/io.github.techouse/qs-kotlin
   :alt: Maven Central version
.. |spm| image:: https://img.shields.io/github/v/release/techouse/qs-swift?logo=swift&label=SwiftPM
   :target: https://swiftpackageindex.com/techouse/qs-swift
   :alt: Swift Package Manager version
.. |nuget| image:: https://img.shields.io/nuget/v/QsNet?logo=dotnet&label=NuGet
   :target: https://www.nuget.org/packages/QsNet
   :alt: NuGet version
.. |npm| image:: https://img.shields.io/npm/v/qs?logo=javascript&label=npm
   :target: https://www.npmjs.com/package/qs
   :alt: npm version
