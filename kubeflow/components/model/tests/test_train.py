import mock
import os
# from shutil import rmtree
from collections import namedtuple

from train import main


def test_train_model(monkeypatch, tmpdir_factory):
    post_mock = mock.Mock()
    os_system_mock = mock.Mock()

    tmp_folder = tmpdir_factory.mktemp('unittest')

    def write_file(tmp_folder: str, context: int):
        os.makedirs(str(tmp_folder), exist_ok=True)
        with open(f'{tmp_folder}/model.txt', 'w') as f:
            f.write(f'model definition: {context}')

    os_system_mock.return_value = write_file(str(tmp_folder), 1)

    datetime_mock = mock.Mock()
    datetime_mock.today.return_value.strftime.return_value = 'todays date'

    partial_mock = mock.Mock()
    partial_mock.return_value = 'partial function'

    pool_mock = mock.Mock()
    pool_mock.return_value.map.side_effect = [
        [0.3, 0.2],
        [0.2, 0.1],
        [0.4, 0.3]
    ]

    monkeypatch.setattr('train.post_model_to_elasticsearch', post_mock)
    monkeypatch.setattr('train.os.system', os_system_mock)
    monkeypatch.setattr('train.get_partiated_validator', partial_mock)
    monkeypatch.setattr('train.Pool', pool_mock)
    monkeypatch.setattr('train.datetime', datetime_mock)

    args = namedtuple(
        'args',
        [
            'train_file_path',
            'validation_files_path',
            'validation_train_files_path',
            'es_host',
            'model_name',
            'es_batch'
            'destination',
            'ranker',
            'index'
        ]
    )
    args.train_file_path = '/test/train_dataset.txt'
    args.validation_files_path = '/validation/regular'
    args.validation_train_files_path = '/validation/train'
    args.es_host = 'es_host_test'
    args.model_name = 'unittest'
    args.es_batch = 2
    args.destination = str(tmp_folder)
    args.ranker = 'lambdamart'
    args.index = 'index_test'

    X = ['--var1 val1 --var2 val2']

    main(args, X)
    expected_call = (
        'java -jar ranklib/RankLib-2.14.jar -ranker 6 -train '
        f'/test/train_dataset.txt -norm sum -save {str(tmp_folder)}/model.txt '
        '-var1 val1 -var2 val2 -metric2t ERR'
    )
    os_system_mock.assert_any_call(expected_call)
    post_mock.assert_any_call('es_host_test', 'unittest',
                              f'{args.destination}/model.txt')
    partial_mock.assert_any_call('es_host_test', 'index_test', 'unittest', 2)
    data = open(f'{args.destination}/results.txt').read()
    assert data == 'todays date,--var1 val1 --var2 val2,rank_train=0.2,rank_val=0.3\n'
    data = open(f'{args.destination}/best_rank.txt').read()
    assert data == '0.3'
    data = open(f'{args.destination}/best_model.txt').read()
    assert data == 'model definition: 1'

    # Test if new best model gets replaced
    os_system_mock.return_value = write_file(str(tmp_folder), 2)
    main(args, X)
    data = open(f'{args.destination}/results.txt').read()
    assert data == (
        'todays date,--var1 val1 --var2 val2,rank_train=0.2,rank_val=0.3\n'
        'todays date,--var1 val1 --var2 val2,rank_train=0.1,rank_val=0.2\n'
    )
    data = open(f'{args.destination}/best_rank.txt').read()
    assert data == '0.2'
    data = open(f'{args.destination}/best_model.txt').read()
    assert data == 'model definition: 2'

    # Test if new worse model is ignored
    os_system_mock.return_value = write_file(str(tmp_folder), 3)
    main(args, X)
    data = open(f'{args.destination}/results.txt').read()
    assert data == (
        'todays date,--var1 val1 --var2 val2,rank_train=0.2,rank_val=0.3\n'
        'todays date,--var1 val1 --var2 val2,rank_train=0.1,rank_val=0.2\n'
        'todays date,--var1 val1 --var2 val2,rank_train=0.3,rank_val=0.4\n'
    )
    data = open(f'{args.destination}/best_rank.txt').read()
    assert data == '0.2'
    data = open(f'{args.destination}/best_model.txt').read()
    assert data == 'model definition: 2'
