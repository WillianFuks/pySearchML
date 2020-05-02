import mock
import pytest
from collections import namedtuple

from pySearchML.model.validate import validate_model


@pytest.fixture
def py_path():
    return 'pySearchML.model.validate'


def test_validate_model(monkeypatch, py_path, es_response):
    es_mock = mock.Mock()
    es_mock.return_value.msearch.side_effect = es_response
    monkeypatch.setattr(py_path + '.Elasticsearch', es_mock)

    args = namedtuple(
        'args',
        [
            'path',
            'es_query_path',
            'index',
            'es_host',
            'model_name',
            'es_batch'
        ]
    )
    args.path = 'tests/unit/model/fixtures/validation'
    args.es_query_path = 'tests/unit/model/fixtures/es_query.json'
    args.index = 'index_test'
    args.es_host = 'es_host_test'
    args.model_name = 'model_name_test'
    args.es_batch = 2

    rank = validate_model(args)
    assert rank == 0.6
