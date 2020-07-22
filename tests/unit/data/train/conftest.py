import pytest


@pytest.fixture
def es_log_features():
    return [
        {
            'responses': [
                {
                    'hits': {
                        'hits': [
                            {
                                '_id': 'doc0',
                                'fields': {
                                    '_ltrlog': [
                                        {
                                            'main': [
                                                {
                                                    'value': 0.01
                                                },
                                                {
                                                    'value': 0.02
                                                }
                                            ]
                                        }
                                    ]
                                }
                            },
                            {
                                '_id': 'doc1',
                                'fields': {
                                    '_ltrlog': [
                                        {
                                            'main': [
                                                {
                                                    'value': 0.03
                                                },
                                                {
                                                    'value': 0.04
                                                }
                                            ]
                                        }
                                    ]
                                }
                            },
                            {
                                '_id': 'doc2',
                                'fields': {
                                    '_ltrlog': [
                                        {
                                            'main': [
                                                {
                                                    'value': 0.05
                                                },
                                                {
                                                    'value': 0.06
                                                }
                                            ]
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                },
                {
                    'hits': {
                        'hits': [
                            {
                                '_id': 'doc1',
                                'fields': {
                                    '_ltrlog': [
                                        {
                                            'main': [
                                                {
                                                    'value': 0.03
                                                },
                                                {
                                                    'value': 0.04
                                                }
                                            ]
                                        }
                                    ]
                                }
                            },
                            {
                                '_id': 'doc2',
                                'fields': {
                                    '_ltrlog': [
                                        {
                                            'main': [
                                                {
                                                    'value': 0.05
                                                },
                                                {}
                                            ]
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        },
        {
            'responses': [
                {
                    'hits': {
                        'hits': [
                            {
                                '_id': 'doc3',
                                'fields': {
                                    '_ltrlog': [
                                        {
                                            'main': [
                                                {
                                                    'value': 0.06
                                                },
                                                {
                                                    'value': 0.07
                                                }
                                            ]
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        },
        {}
    ]
