import sys
import subprocess
import argparse
import gzip
import json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--restart',
        dest='restart',
        type=lambda arg: arg.lower() == 'true',
        default=False,
        help='If `true` then deletes index from ES and re-create it with data'
    )
    parser.add_argument(
        '--es_host',
        dest='es_host',
        type=str,
        help='Hostname where Elasticsearch is running'
    )
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args


def download_gcs_blob():
    subprocess.call(
        ['gsutil cp -R gs://pysearchml/es_docs.gz /tmp/'],
        stdout=subprocess.PIPE,
        shell=True
    )


def upload_data():
    es = Elasticsearch(hosts=[args.es_host])
    mapping = json.loads(open('pySearchML/es/mapping.json').read())
    index = mapping.pop('index')
    es.indices.delete(index, ignore=[400, 404])
    es.indices.create(index, body=mapping['body'])

    def read_file():
        for row in gzip.GzipFile('/tmp/es_docs.gz', 'r'):
            result = {}
            row = json.loads(row)
            result['_source'] = row
            result['_index'] = index
            yield result
    bulk(es, read_file(), request_timeout=30)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])

    if not args.restart:
        sys.exit()

    download_gcs_blob()
    upload_data()
