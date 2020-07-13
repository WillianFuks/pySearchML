import mock
import json
import gzip
import os
import subprocess
import shutil
from collections import namedtuple

from run import main


def test_main(monkeypatch, es_log_features):
    shutil.rmtree('/tmp/pysearchml/unittest', ignore_errors=True)
    # features_path = '/tmp/pysearchml/unittest/data/features'
    clickmodel_path = '/tmp/pysearchml/unittest/clickmodel'
    # os.makedirs(features_path)
    os.makedirs(clickmodel_path)

#     subprocess.call(
        # [f'cp -r tests/unit/data/train/fixtures/features/* {features_path}'],
        # stdout=subprocess.PIPE,
        # shell=True
#     )

    subprocess.call(
        [f'cp -r tests/fixtures/model.gz {clickmodel_path}'],
        stdout=subprocess.PIPE,
        shell=True
    )

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

    requests_mock = mock.Mock()
    es_client_mock = mock.Mock()

    monkeypatch.setattr(py_path + '.requests', requests_mock)
    es_client_mock.msearch.side_effect = es_log_features

    write_ranklib_file(args, es_client_mock)

    request_data = (
        '{"featureset": {"name": "model_name_test", "features": [{"name": '
        '"test1", "template": {"match": {"field1": "{{test}}"}}, "params": '
        '["test"]}, {"name": "test2", "template": {"match": {"f2": "{{test}}"}}, '
        '"params": ["test"]}]}}'
    )
    requests_mock.post.assert_called_once_with(
        '_ltr/_featureset/model_name_test',
        data=request_data,
        headers={'Content-Type': 'application/json'}
    )

    f = gzip.GzipFile(
        '/tmp/pysearchml/model_name_test/data/judgments/judgments.gz'
    )

    judgments = json.loads(f.readline())

    expected = {
        'judgment_keys': [
            {'doc': 'doc0', 'judgment': 0},
            {'doc': 'doc1', 'judgment': 2},
            {'doc': 'doc2', 'judgment': 4},
        ],
        'search_keys': 'keyword0'
    }

    assert judgments == expected

    body1 = ('{"index": "index_test"}\n{"query": {"bool": {"filter": [{"terms": {"_id":'
             ' ["doc0", "doc1", "doc2"]}}], "should": [{"sltr": {"_name": '
             '"logged_featureset", "featureset": "model_name_test", "params": '
             '"keyword0"}}]}}, "_source": ["_id"], "ext": {"ltr_log": {"log_specs": '
             '{"name": "main", "named_query": "logged_featureset"}}}}\n{"index": '
             '"index_test"}\n{"query": {"bool": {"filter": [{"terms": {"_id": ["doc1", '
             '"doc2"]}}], "should": [{"sltr": {"_name": "logged_featureset", '
             '"featureset": "model_name_test", "params": "keyword1"}}]}}, "_source": '
             '["_id"], "ext": {"ltr_log": {"log_specs": {"name": "main", "named_query": '
             '"logged_featureset"}}}}')
    body2 = ('{"index": "index_test"}\n{"query": {"bool": {"filter": [{"terms": {"_id": '
             '["doc3", "doc4"]}}], "should": [{"sltr": {"_name": "logged_featureset", '
             '"featureset": "model_name_test", "params": "keyword2"}}]}}, "_source": '
             '["_id"], "ext": {"ltr_log": {"log_specs": {"name": "main", "named_query": '
             '"logged_featureset"}}}}')
    es_client_mock.msearch.assert_any_call(body=body1, request_timeout=60)
    es_client_mock.msearch.assert_any_call(body=body2, request_timeout=60)

    rank_data = open(
        '/tmp/pysearchml/model_name_test/data/train/ranklib_train.txt'
    ).read()

    expected = ('0\tqid:0\t1:0.01\t2:0.02\n2\tqid:0\t1:0.03\t2:0.04\n4\tqid:0\t1:0.05\t'
                '2:0.06\n0\tqid:1\t1:0.03\t2:0.04\n4\tqid:1\t1:0.05\t2:0\n')
    assert rank_data == expected

    shutil.rmtree('/tmp/pysearchml', ignore_errors=True)
