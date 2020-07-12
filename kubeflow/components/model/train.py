import sys
import os
import argparse
import pathlib
from datetime import datetime
from typing import NamedTuple, Any, Sequence
from functools import partial
from multiprocessing import Pool
from shutil import copyfile

import requests

from validate import validate_model


def main(args: NamedTuple, X: Sequence[Any]) -> None:
    """
    X contains a list of input arguments, such as `[--var1=val1]`. These args are sent
    to RankLib to setup a training run specification.

    Args
    ----
      args: NamedTuple
        ranker: str
            Name of which ranker to use available in RankLib
        train_file_path: str
            Path where RankLib training file is located.
        validation_files_path: str
            Path where regular validation files are located.
        validation_train_files_path: str
            Path where validation files of training period are located.
        es_host: str
            Hostname where Elasticsearch is located.
        model_name: str
            RankLib featureset Model Name as saved in Elasticsearch.
        destination: str
            File name where to save results.

      X: Sequence[Any]
          Values for input of RankLib parameters.
    """
    ranker = get_ranker_index(args.ranker)
    if not ranker:
        raise ValueError(f'Invalid value for ranker: "{args.ranker}"')

    cmd = ('java -jar ranklib/RankLib-2.14.jar -ranker '
           f'{ranker} -train {args.train_file_path} -norm sum -save '
           f'/tmp/pysearchml/model.txt {(" ".join(X)).replace("--", "-")} -metric2t ERR')

    # /tmp/pysearchml/model.txt contains the specification of the final trained model
    os.system(cmd)
    print('posting model to es')
    post_model_to_elasticsearch(args.es_host, args.model_name)
    partiated_validator = get_partiated_validator(args.es_host, args.index,
                                                  args.model_name, args.es_batch)
    pool = Pool()
    rank_val, rank_train = pool.map(partiated_validator, [args.validation_files_path,
                                    args.validation_train_files_path])

    write_results(X, rank_train, rank_val, args.destination)


def get_ranker_index(ranker: str) -> str:
    return {
        'mart': '0',
        'ranknet': '1',
        'rankboost': '2',
        'adarank': '3',
        'coordinate ascent': '4',
        'lambdamart': '6',
        'listnet': '7',
        'random forest': '8'
    }.get(ranker)


def write_results(X: Sequence[Any], rank_train: float, rank_val: float,
                  destination: str):
    """
    Write results in persistent disk. Uses the folder of `destination` as main reference

    Args
    ----
      X: Sequence[Any]
          Input arguments as suggested by Katib. It sets the hyperparameters of the
          models.
      rank_train: float
          Rank value of training data.
      rank_val: float
          Rank value for validation data.
      destination: str
          File path where to save results.
    """
    # Katib installs sidecars pods that keeps reading StdOut of the main pod searching
    # for the previously specified pattern. This print tells Katib that this is the
    # metric it should be aiming to optimize.
    print(f'Validation-rank={rank_val}')
    dir_ = pathlib.Path(destination)
    os.makedirs(str(dir_), exist_ok=True)
    with open(str(dir_ / 'results.txt'), 'a') as f:
        today_str = datetime.today().strftime('%Y%m%d %H:%M:%S')
        f.write(
            f'{today_str},{" ".join(X)},rank_train={rank_train},'
            f'rank_val={rank_val}{os.linesep}'
        )
    best_model_file = dir_ / 'best_model.txt'
    best_rank_file = dir_ / 'best_rank.txt'
    if os.path.isfile(str(best_rank_file)):
        best_rank = float(open(str(best_rank_file)).readline())
        if rank_val < best_rank:
            with open(str(best_rank_file), 'w') as f:
                f.write(str(rank_val))
            copyfile('/tmp/model.txt', str(best_model_file))
    else:
        with open(str(best_rank_file), 'w') as f:
            f.write(str(rank_val))
            copyfile('/tmp/model.txt', str(best_model_file))


def get_partiated_validator(
    es_host: str,
    index: str,
    model_name: str,
    es_batch: int = 1000
):
    return partial(validate_model, es_host=es_host, index=index, model_name=model_name,
                   es_batch=es_batch)


def post_model_to_elasticsearch(es_host, model_name) -> None:
    """
    Exports trained model to Elasticsearch
    """
    model_definition = open('/tmp/pysearchml/model.txt').read()
    model_request = {
        'model': {
            'name': model_name,
            'model': {
                'type': 'model/ranklib',
                'definition': model_definition
            }
        }
    }
    path = f'http://{es_host}/_ltr/_model/{model_name}'
    response = requests.delete(path)

    path = f'http://{es_host}/_ltr/_featureset/{model_name}/_createmodel'
    header = {'Content-Type': 'application/json'}
    response = requests.post(path, json=model_request, headers=header)
    if not response.ok:
        raise Exception(response.content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--train_file_path',
        dest='train_file_path',
        type=str,
        help='Path where RankLib training file data is located.'
    )
    parser.add_argument(
         '--validation_files_path',
         dest='validation_files_path',
         type=str,
         help='Path where validation data path is located.'
    )
    parser.add_argument(
         '--validation_train_files_path',
         dest='validation_train_files_path',
         type=str,
         help='Path where validation train data path is located.'
    )
    parser.add_argument(
        '--es_host',
        dest='es_host',
        type=str,
        help='Host address to reach Elasticsearch.'
    )
    parser.add_argument(
        '--es_batch',
        dest='es_batch',
        type=int,
        default=1000,
        help=('Determines how many items to send at once to Elasticsearch when using '
              'multisearch API.')
    )
    parser.add_argument(
        '--destination',
        dest='destination',
        type=str,
        help='Path where validation score is should be saved to.'
    )
    parser.add_argument(
        '--model_name',
        dest='model_name',
        type=str,
        help='Name of featureset store as saved in Elasticsearch.'
    )
    parser.add_argument(
        '--ranker',
        dest='ranker',
        type=str,
        help='Name of ranker algorithm to be used from RankLib.'
    )
    parser.add_argument(
        '--index',
        dest='index',
        default='pysearchml',
        type=str,
        help='ES Index name to use.'
    )

    print(sys.argv[1:])
    args, unknown = parser.parse_known_args(sys.argv[1:])
    print('this is uknown: ', unknown)
    main(args, unknown)
