import argparse
import sys
from typing import List, NamedTuple

from validate import validate_model


def parse_args(args: List) -> NamedTuple:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--files_path',
        dest='files_path',
        type=str,
        help='Path to files containing data of customers searches and their purchases'
    )
    parser.add_argument(
        '--index',
        dest='index',
        type=str,
        default='pysearchml',
        help='Name of Index where documents are stored in Elasticsearch.'
    )
    parser.add_argument(
        '--es_host',
        dest='es_host',
        type=str,
        help='Host address to reach Elasticsearch.'
    )
    parser.add_argument(
        '--model_name',
        dest='model_name',
        type=str,
        help='Assigns a name for the RankLib model. Each experiment on Kubeflow should '
             'have a specific name in order to preserver their results.'
    )
    parser.add_argument(
        '--es_batch',
        dest='es_batch',
        type=int,
        default=1000,
        help='Determines how many items to send at once to Elasticsearch when using '
             'multisearch API.'
    )


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    test_rank = validate_model(
        args.files_path,
        args.es_host,
        args.model_name,
        args.index,
        args.es_batch
    )
    print(f'Test-rank={test_rank}')
