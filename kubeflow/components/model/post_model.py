import sys
import argparse

from train import post_model_to_elasticsearch


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--es_host',
        dest='es_host',
        type=str,
        help='Host address to reach Elasticsearch.'
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
    args, _ = parser.parse_known_args(sys.argv[1:])
    post_model_to_elasticsearch(args.es_host, args.model_name,
                                f'{args.destination}')
