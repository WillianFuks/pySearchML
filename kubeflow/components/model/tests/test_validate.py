import mock
from collections import namedtuple

from validate import validate_model


def test_validate_model(monkeypatch, es_response):
    print('this is es_response: ', es_response)
    1 / 0
    es_mock = mock.Mock()
    es_mock.return_value.msearch.side_effect = es_response
    monkeypatch.setattr('validate.Elasticsearch', es_mock)

    args = namedtuple(
        'args',
        [
            'files_path',
            'index',
            'es_host',
            'model_name',
            'es_batch'
        ]
    )
    args.files_path = 'tests/fixtures/'
    args.es_query_path = 'queries/unittest/es_query.json'
    args.index = 'index_test'
    args.es_host = 'es_host_test'
    args.model_name = 'unittest'
    args.es_batch = 2

    rank = validate_model(
        args.files_path,
        args.es_host,
        args.model_name,
        args.index,
        args.es_batch
    )
    assert rank == 0.6
