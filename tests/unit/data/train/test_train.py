import mock
import os
import subprocess
import shutil
import pytest
from collections import namedtuple

from pySearchML.data.train.ranklib import write_ranklib_file


@pytest.fixture
def py_path():
    return 'pySearchML.data.train.ranklib'


def test_write_ranklib_file(monkeypatch, py_path):
    shutil.rmtree('/tmp/pysearchml', ignore_errors=True)
    features_path = '/tmp/pysearchml/data/features'
    os.makedirs(features_path)

    subprocess.call(
        ['cp -r tests/unit/data/train/features/* /tmp/pysearchml/data/features/'],
        stdout=subprocess.PIPE,
        shell=True
    )

    args = namedtuple(
        'args',
        [
            'init_day_train',
            'end_day_train',
            'restart_ranklib',
            'gcp_project',
            'bq_dataset',
            'gcp_bucket',
            'index',
            'es_host',
            'model_name',
            'es_batch'
        ]
    )
    args.init_day_train = '20200101'
    args.end_day_train = '20200101'
    args.restart_ranklib = False
    args.gcp_project = 'gcp_project_test'
    args.bq_dataset = 'bq_dataset_test'
    args.gcp_bucket = 'gcp_bucket'
    args.index = 'index_test'
    args.es_host = 'es_host_test'
    args.model_name = 'model_name_test'
    args.es_batch = 2

    requests_mock = mock.Mock()
    es_client_mock = mock.Mock()
    monkeypatch.setattr(py_path + '.requests', requests_mock)

    write_ranklib_file(args, es_client_mock)
    assert False

    shutil.rmtree('/tmp/pysearchml', ignore_errors=True)
