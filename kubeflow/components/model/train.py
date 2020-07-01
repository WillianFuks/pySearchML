import sys
import argparse
from typing import NamedTuple

import numpy as np


def ltr_f_x(x: float) -> float:
    # e ^ -(x - 2) ^ 2 + e ^ -((x - 6) ^ 2 / 10) + 1 / (x ^ 2 + 1)
    (0, np.exp(-(x - 2) ** 2) + np.exp(-(x - 6) ** 2 / 10) + 1 / (x ** 2 + 1))


def main(args: NamedTuple):
    y = ltr_f_x(args.x)
    print(f'rank={y}')


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
        dest='model_name',
        type=str,
        help='Name of featureset store as saved in Elasticsearch.'
    )

    print(sys.argv[1:])
    args, _ = parser.parse_known_args(sys.argv[1:])
    main(args)
