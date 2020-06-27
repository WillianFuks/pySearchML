import sys
import argparse
import pathlib
import gzip
import json
import requests
from typing import Dict, Any, NamedTuple
from urllib.parse import urljoin

from google.cloud import storage, bigquery


PATH = pathlib.Path(__file__).parent


def process_feature_file(filename: str) -> Dict[str, Any]:
    """
    Each feature for RankLib is defined in a JSON file with its name and formula.

    Args
    ----
      filename: str
          Filename containing definition for a specific feature.

    Returns
    -------
      feature: str
          JSON feature processed.
    """
    feature = json.loads(open(filename).read())
    template = feature['query']
    name = feature['name']
    params = feature['params']
    feature_spec = {
        'name': name,
        'template': template,
        'params': params
    }
    return feature_spec


def create_feature_store(es_host: str) -> None:
    """
    RankLib uses the concept of "features store" where information about features is
    stored on Elasticsearch. Here, the store is just created but now features are
    defined yet.

    Args
    ----
      restart: bool
          If `True` then deletes feature store on Elasticsearch and create it again.
      es_host: str
          Hostname where to reach Elasticsearch.
    """
    host = f'http://{es_host}'
    feature_store_url = urljoin(host, '_ltr')
    requests.delete(feature_store_url)
    requests.put(feature_store_url)


def create_feature_set(es_host: str, model_name: str) -> None:
    """
    Defines each feature that should be used for the RankLib model. It's expected the
    features will be available at a specific path when this script runs (this is
    accomplished by running previous steps on Kubeflow that prepares this data).

    Args
    ----
      es_host: str
          Hostname of Elasticsearch.
      model_name: str
          Name that specificies current experiment in Kubeflow.
    """
    features_path = PATH / 'features' / f'{model_name}'
    feature_set = {
        'featureset': {
            'name': model_name,
            'features': [process_feature_file(str(filename)) for filename in
                         features_path.glob('*')]
        }
    }
    post_feature_set(feature_set, model_name, es_host)


def post_feature_set(
    feature_set: Dict[str, Any],
    model_name: str,
    es_host: str
) -> None:
    """
    POST feature definition to Elasticsearch under the name of `model_name`.

    Args
    ----
      feature_set: Dict[str, Any]
          Definition of features to be stored on Elasticsearch.
      model_name: str
          Defined for each Kubeflow experiment.
      es_host: str
          Hostname where Elasticsearch is located.
    """
    host = f'http://{es_host}'
    url = f'_ltr/_featureset/{model_name}'
    url = urljoin(host, url)
    header = {'Content-Type': 'application/json'}
    resp = requests.post(url, data=json.dumps(feature_set), headers=header)
    if not resp.ok:
        raise Exception(resp.content)


def main(args: NamedTuple):
    import json
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk

    es = Elasticsearch(hosts=[args.es_host])
    es_mapping_path = PATH / 'es_mapping.json'
    schema = json.loads(open(str(es_mapping_path)).read())
    index = schema.pop('index')

    def read_file(bucket):
        storage_client = storage.Client()
        bq_client = bigquery.Client()

        ds_ref = bq_client.dataset('pysearchml')
        bq_client.create_dataset(ds_ref, exists_ok=True)

        table_id = 'es_docs'
        table_ref = ds_ref.table(table_id)

        bucket_obj = storage_client.bucket(bucket.split('/')[0])
        if not bucket_obj.exists():
            bucket_obj.create()

        # # Query GA data
        query_path = PATH / 'ga_data.sql'
        query = open(str(query_path)).read()
        job_config = bigquery.QueryJobConfig()
        job_config.destination = f'{bq_client.project}.pysearchml.{table_id}'
        job_config.maximum_bytes_billed = 10 * (1024 ** 3)
        job_config.write_disposition = 'WRITE_TRUNCATE'
        job = bq_client.query(query, job_config=job_config)
        job.result()

        # export BigQuery table to GCS
        destination_uri = f'gs://{bucket}/es_docs.gz'

        extract_config = bigquery.ExtractJobConfig()
        extract_config.compression = 'GZIP'
        extract_config.destination_format = 'NEWLINE_DELIMITED_JSON'
        job = bq_client.extract_table(table_ref, destination_uri,
                                      job_config=extract_config)
        job.result()

        # Download data
        blob = bucket_obj.blob('es_docs.gz')
        file_obj = gzip.io.BytesIO()
        blob.download_to_file(file_obj)

        file_obj.seek(0)

        c = 0
        for row in gzip.GzipFile(fileobj=file_obj, mode='rb'):
            row = json.loads(row)
            yield {
                '_index': index,
                '_source': row,
                '_id': row['sku']
            }
            c += 1
            if not c % 1000:
                print(c)

        # Delete BQ Table
        bq_client.delete_table(table_ref)

    if args.force_restart or not es.indices.exists(index):
        es.indices.delete(index, ignore=[400, 404])
        print('deleted index')
        es.indices.create(index, **schema)
        print('schema created')
        bulk(es, read_file(args.bucket), request_timeout=30)
        create_feature_store(args.es_host)
        create_feature_set(args.es_host, args.model_name)
    print('Finished preparing environment.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--force_restart',
        dest='force_restart',
        type=lambda arg: arg.lower() == 'true',
        default=False
    )
    parser.add_argument(
        '--es_host',
        dest='es_host',
        type=str,
        default='localhost'
    )
    parser.add_argument(
        '--bucket',
        dest='bucket',
        type=str
    )
    parser.add_argument(
        '--model_name',
        dest='model_name',
        type=str,
        help=('Assigns a name for the RankLib model. Each experiment on Kubeflow '
              'should have a specific name in order to preserver their results.')
    )
    args, _ = parser.parse_known_args(sys.argv[1:])
    main(args)
