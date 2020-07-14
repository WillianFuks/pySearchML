import mock
import json
import gzip
import os
import subprocess
import shutil
from collections import namedtuple

from run import main


def test_main(monkeypatch, es_log_features, tmpdir_factory):
    shutil.rmtree('/tmp/pysearchml/unittest', ignore_errors=True)
    clickmodel_path = '/tmp/pysearchml/unittest/model'
    os.makedirs(clickmodel_path)
    tmp_dir = tmpdir_factory.mktemp('unittest')

    args = namedtuple(
        'args',
        [
            'train_init_date',
            'train_end_date',
            'bucket',
            'es_host',
            'es_batch',
            'destination',
            'model_name',
            'index'
        ]
    )
    args.init_day_train = '20200101'
    args.end_day_train = '20200101'
    args.bucket = 'gcp_bucket'
    args.index = 'index_test'
    args.es_host = 'es_host_test'
    args.model_name = 'unittest'
    args.es_batch = 2
    args.destination = str(tmp_dir)

    download_mock = mock.Mock()

    class MockModel:
        def fit(self, *args, **kwargs):
            return self

        def export_judgments(self, model_path: str):
            subprocess.call(
                [f'cp -r tests/fixtures/model.gz {model_path}'],
                stdout=subprocess.PIPE,
                shell=True
            )

    dbn_mock = mock.Mock()
    dbn_mock.DBNModel.return_value = MockModel()
    es_client_mock = mock.Mock()

    monkeypatch.setattr('run.download_data', download_mock)
    monkeypatch.setattr('run.DBN', dbn_mock)
    monkeypatch.setattr('run.Elasticsearch', es_client_mock)
    es_client_mock.msearch.side_effect = es_log_features

    main(args, es_client_mock)
    download_mock.assert_called_with(args)
    data_reader = gzip.GzipFile('/tmp/pysearchml/unittest/judgments/judgments.gz', 'rb')
    data = json.loads(data_reader.readline())
    expected = {
        "search_keys": {"search_term": "keyword0", "var1": "val1"},
        "judgment_keys": [
            {"doc": "doc0", "judgment": 0},
            {"doc": "doc1", "judgment": 4},
            {"doc": "doc2", "judgment": 2}
        ]
    }
    assert expected == data

    data = json.loads(data_reader.readline())
    expected = {
        "search_keys": {"search_term": "keyword1", "var1": "val1"},
        "judgment_keys": [
            {"doc": "doc1", "judgment": 0},
            {"doc": "doc2", "judgment": 4}
        ]
    }
    assert expected == data

    data = json.loads(data_reader.readline())
    expected = {
        "search_keys": {"search_term": "keyword2", "var1": "val1"},
        "judgment_keys": [
            {"doc": "doc3", "judgment": 0},
            {"doc": "doc4", "judgment": 4}
        ]
    }
    assert expected == data

    body1 = (
        '{"index": "index_test"}\n{"query": {"bool": {"filter": [{"terms": {"_id": '
        '["doc0", "doc1", "doc2"]}}], "should": [{"sltr": {"_name": "logged_featureset"'
        ', "featureset": "unittest", "params": {"search_term": "keyword0", "var1": '
        '"val1"}}}]}}, "_source": ["_id"], "ext": {"ltr_log": {"log_specs": {"name": '
        '"main", "named_query": "logged_featureset"}}}}\n{"index": "index_test"}\n{"'
        'query": {"bool": {"filter": [{"terms": {"_id": ["doc1", "doc2"]}}], "should": '
        '[{"sltr": {"_name": "logged_featureset", "featureset": "unittest", "params": '
        '{"search_term": "keyword1", "var1": "val1"}}}]}}, "_source": ["_id"], "ext": '
        '{"ltr_log": {"log_specs": {"name": "main", "named_query": "logged_featureset"}'
        '}}}'
    )
    body2 = (
        '{"index": "index_test"}\n{"query": {"bool": {"filter": [{"terms": {"_id": ["'
        'doc3", "doc4"]}}], "should": [{"sltr": {"_name": "logged_featureset", "'
        'featureset": "unittest", "params": {"search_term": "keyword2", "var1": "val1"'
        '}}}]}}, "_source": ["_id"], "ext": {"ltr_log": {"log_specs": {"name": "main", '
        '"named_query": "logged_featureset"}}}}'
    )
    es_client_mock.msearch.assert_any_call(body=body1, request_timeout=60)
    es_client_mock.msearch.assert_any_call(body=body2, request_timeout=60)

    rank_data = open(f'{str(tmp_dir)}/train_dataset.txt').read()

    expected = (
        '0\tqid:0\t1:0.01\t2:0.02\n4\tqid:0\t1:0.03\t2:0.04\n2\tqid:0\t1:0.05\t'
        '2:0.06\n0\tqid:1\t1:0.03\t2:0.04\n4\tqid:1\t1:0.05\t2:0\n'
    )

    assert rank_data == expected
    shutil.rmtree('/tmp/pysearchml/unittest', ignore_errors=True)
