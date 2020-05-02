import pytest


@pytest.fixture
def es_response():
    return [
        {
            'responses': [
                {
                    'hits': {
                        'hits': [
                            {
                                '_id': 'doc3',
                            },
                            {
                                '_id': 'doc2',
                            },
                            {
                                '_id': 'doc1',
                            },
                            {
                                '_id': 'doc0',
                            }
                        ]
                    }
                },
                {
                    'hits': {
                        'hits': [
                            {
                                '_id': 'doc3',
                            },
                            {
                                '_id': 'doc2',
                            },
                            {
                                '_id': 'doc1',
                            },
                            {
                                '_id': 'doc0',
                            }
                        ]
                    }
                },
            ]
        },
        {
            'responses': [
                {
                    'hits': {
                        'hits': [
                            {
                                '_id': 'doc3',
                            },
                            {
                                '_id': 'doc2',
                            },
                            {
                                '_id': 'doc1',
                            },
                            {
                                '_id': 'doc0',
                            }
                        ]
                    }
                }
            ]
        },
    ]
