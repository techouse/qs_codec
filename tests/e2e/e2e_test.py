import typing as t

import pytest

from qs_codec import EncodeOptions, decode, encode


class TestE2E:
    @pytest.mark.parametrize(
        "data, encoded",
        [
            ({}, ""),
            ({"a": "b"}, "a=b"),
            ({"a": "b", "c": "d"}, "a=b&c=d"),
            ({"a": "b", "c": "d", "e": "f"}, "a=b&c=d&e=f"),
            ({"a": "b", "c": "d", "e": ["f", "g", "h"]}, "a=b&c=d&e[0]=f&e[1]=g&e[2]=h"),
            (
                {"a": "b", "c": "d", "e": ["f", "g", "h"], "i": {"j": "k", "l": "m"}},
                "a=b&c=d&e[0]=f&e[1]=g&e[2]=h&i[j]=k&i[l]=m",
            ),
            (
                {
                    "filters": {
                        r"$or": [
                            {
                                "date": {
                                    r"$eq": "2020-01-01",
                                }
                            },
                            {
                                "date": {
                                    r"$eq": "2020-01-02",
                                }
                            },
                        ],
                        "author": {
                            "name": {
                                r"$eq": "John Doe",
                            },
                        },
                    }
                },
                r"filters[$or][0][date][$eq]=2020-01-01&filters[$or][1][date][$eq]=2020-01-02&filters[author][name][$eq]=John Doe",
            ),
            (
                # Adapted from https://github.com/luffynando/dart_api_query/blob/main/test/dummy/data/comments_embed_response.dart
                {
                    "commentsEmbedResponse": [
                        {
                            "id": "1",
                            "post_id": "1",
                            "someId": "ma018-9ha12",
                            "text": "Hello",
                            "replies": [
                                {"id": "3", "comment_id": "1", "someId": "ma020-9ha15", "text": "Hello"},
                            ],
                        },
                        {
                            "id": "2",
                            "post_id": "1",
                            "someId": "mw012-7ha19",
                            "text": "How are you?",
                            "replies": [
                                {"id": "4", "comment_id": "2", "someId": "mw023-9ha18", "text": "Hello"},
                                {"id": "5", "comment_id": "2", "someId": "mw035-0ha22", "text": "Hello"},
                            ],
                        },
                    ],
                },
                r"commentsEmbedResponse[0][id]=1&commentsEmbedResponse[0][post_id]=1&commentsEmbedResponse[0][someId]=ma018-9ha12&commentsEmbedResponse[0][text]=Hello&commentsEmbedResponse[0][replies][0][id]=3&commentsEmbedResponse[0][replies][0][comment_id]=1&commentsEmbedResponse[0][replies][0][someId]=ma020-9ha15&commentsEmbedResponse[0][replies][0][text]=Hello&commentsEmbedResponse[1][id]=2&commentsEmbedResponse[1][post_id]=1&commentsEmbedResponse[1][someId]=mw012-7ha19&commentsEmbedResponse[1][text]=How are you?&commentsEmbedResponse[1][replies][0][id]=4&commentsEmbedResponse[1][replies][0][comment_id]=2&commentsEmbedResponse[1][replies][0][someId]=mw023-9ha18&commentsEmbedResponse[1][replies][0][text]=Hello&commentsEmbedResponse[1][replies][1][id]=5&commentsEmbedResponse[1][replies][1][comment_id]=2&commentsEmbedResponse[1][replies][1][someId]=mw035-0ha22&commentsEmbedResponse[1][replies][1][text]=Hello",
            ),
            (
                # Adapted from https://github.com/luffynando/dart_api_query/blob/main/test/dummy/data/comments_response.dart
                {
                    "commentsResponse": [
                        {
                            "id": "1",
                            "post_id": "1",
                            "someId": "ma018-9ha12",
                            "text": "Hello",
                            "replies": [
                                {"id": "3", "comment_id": "1", "someId": "ma020-9ha15", "text": "Hello"},
                            ],
                        },
                        {
                            "id": "2",
                            "post_id": "1",
                            "someId": "mw012-7ha19",
                            "text": "How are you?",
                            "replies": [
                                {"id": "4", "comment_id": "2", "someId": "mw023-9ha18", "text": "Hello"},
                                {"id": "5", "comment_id": "2", "someId": "mw035-0ha22", "text": "Hello"},
                            ],
                        },
                    ],
                },
                r"commentsResponse[0][id]=1&commentsResponse[0][post_id]=1&commentsResponse[0][someId]=ma018-9ha12&commentsResponse[0][text]=Hello&commentsResponse[0][replies][0][id]=3&commentsResponse[0][replies][0][comment_id]=1&commentsResponse[0][replies][0][someId]=ma020-9ha15&commentsResponse[0][replies][0][text]=Hello&commentsResponse[1][id]=2&commentsResponse[1][post_id]=1&commentsResponse[1][someId]=mw012-7ha19&commentsResponse[1][text]=How are you?&commentsResponse[1][replies][0][id]=4&commentsResponse[1][replies][0][comment_id]=2&commentsResponse[1][replies][0][someId]=mw023-9ha18&commentsResponse[1][replies][0][text]=Hello&commentsResponse[1][replies][1][id]=5&commentsResponse[1][replies][1][comment_id]=2&commentsResponse[1][replies][1][someId]=mw035-0ha22&commentsResponse[1][replies][1][text]=Hello",
            ),
            (
                # Adapted from https://github.com/luffynando/dart_api_query/blob/main/test/dummy/data/post_embed_response.dart
                {
                    "data": {
                        "id": "1",
                        "someId": "af621-4aa41",
                        "text": "Lorem Ipsum Dolor",
                        "user": {"firstname": "John", "lastname": "Doe", "age": "25"},
                        "relationships": {
                            "tags": {
                                "data": [
                                    {"name": "super"},
                                    {"name": "awesome"},
                                ],
                            },
                        },
                    },
                },
                r"data[id]=1&data[someId]=af621-4aa41&data[text]=Lorem Ipsum Dolor&data[user][firstname]=John&data[user][lastname]=Doe&data[user][age]=25&data[relationships][tags][data][0][name]=super&data[relationships][tags][data][1][name]=awesome",
            ),
            (
                # Adapted from https://github.com/luffynando/dart_api_query/blob/main/test/dummy/data/post_response.dart
                {
                    "id": "1",
                    "someId": "af621-4aa41",
                    "text": "Lorem Ipsum Dolor",
                    "user": {"firstname": "John", "lastname": "Doe", "age": "25"},
                    "relationships": {
                        "tags": [
                            {"name": "super"},
                            {"name": "awesome"},
                        ],
                    },
                },
                r"id=1&someId=af621-4aa41&text=Lorem Ipsum Dolor&user[firstname]=John&user[lastname]=Doe&user[age]=25&relationships[tags][0][name]=super&relationships[tags][1][name]=awesome",
            ),
            (
                # Adapted from https://github.com/luffynando/dart_api_query/blob/main/test/dummy/data/posts_response.dart
                {
                    "postsResponse": [
                        {
                            "id": "1",
                            "someId": "du761-8bc98",
                            "text": "Lorem Ipsum Dolor",
                            "user": {"firstname": "John", "lastname": "Doe", "age": "25"},
                            "relationships": {
                                "tags": [
                                    {"name": "super"},
                                    {"name": "awesome"},
                                ],
                            },
                        },
                        {
                            "id": "1",
                            "someId": "pa813-7jx02",
                            "text": "Lorem Ipsum Dolor",
                            "user": {"firstname": "Mary", "lastname": "Doe", "age": "25"},
                            "relationships": {
                                "tags": [
                                    {"name": "super"},
                                    {"name": "awesome"},
                                ],
                            },
                        },
                    ],
                },
                r"postsResponse[0][id]=1&postsResponse[0][someId]=du761-8bc98&postsResponse[0][text]=Lorem Ipsum Dolor&postsResponse[0][user][firstname]=John&postsResponse[0][user][lastname]=Doe&postsResponse[0][user][age]=25&postsResponse[0][relationships][tags][0][name]=super&postsResponse[0][relationships][tags][1][name]=awesome&postsResponse[1][id]=1&postsResponse[1][someId]=pa813-7jx02&postsResponse[1][text]=Lorem Ipsum Dolor&postsResponse[1][user][firstname]=Mary&postsResponse[1][user][lastname]=Doe&postsResponse[1][user][age]=25&postsResponse[1][relationships][tags][0][name]=super&postsResponse[1][relationships][tags][1][name]=awesome",
            ),
            (
                # Adapted from https://github.com/luffynando/dart_api_query/blob/main/test/dummy/data/posts_response_paginate.dart
                {
                    "posts": [
                        {
                            "id": "1",
                            "someId": "du761-8bc98",
                            "text": "Lorem Ipsum Dolor",
                            "user": {"firstname": "John", "lastname": "Doe", "age": "25"},
                            "relationships": {
                                "tags": [
                                    {"name": "super"},
                                    {"name": "awesome"},
                                ],
                            },
                        },
                        {
                            "id": "1",
                            "someId": "pa813-7jx02",
                            "text": "Lorem Ipsum Dolor",
                            "user": {"firstname": "Mary", "lastname": "Doe", "age": "25"},
                            "relationships": {
                                "tags": [
                                    {"name": "super"},
                                    {"name": "awesome"},
                                ],
                            },
                        },
                    ],
                    "total": "2",
                },
                r"posts[0][id]=1&posts[0][someId]=du761-8bc98&posts[0][text]=Lorem Ipsum Dolor&posts[0][user][firstname]=John&posts[0][user][lastname]=Doe&posts[0][user][age]=25&posts[0][relationships][tags][0][name]=super&posts[0][relationships][tags][1][name]=awesome&posts[1][id]=1&posts[1][someId]=pa813-7jx02&posts[1][text]=Lorem Ipsum Dolor&posts[1][user][firstname]=Mary&posts[1][user][lastname]=Doe&posts[1][user][age]=25&posts[1][relationships][tags][0][name]=super&posts[1][relationships][tags][1][name]=awesome&total=2",
            ),
        ],
    )
    def test_e2e(self, data: t.Mapping, encoded: str):
        assert encode(data, EncodeOptions(encode=False)) == encoded
        assert decode(encoded) == data
