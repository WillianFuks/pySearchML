import sys
import argparse
import gzip

from google.cloud import storage, bigquery


def upload_data(bucket, es_host, force_restart: bool=False):
    import json
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk


    es = Elasticsearch(hosts=[es_host])
    schema = json.loads(open('pySearchML/es/mapping.json').read())
    index = schema.pop('index')

    def read_file(bucket):
        storage_client = storage.Client()
        bq_client = bigquery.Client()

        ds_ref = bq_client.dataset('pysearchml')
        ds = bq_client.get_dataset(ds_ref)
        bq_client.create_dataset(ds, exists_ok=True)

        bucket_obj = storage_client.bucket(bucket)
        if not bucket_obj.exists():
            bucket_obj.create()

        # Query GA data
        query = open('pySearchML/utils/extract_ga_data.sql').read()
        job_config = bigquery.QueryJobConfig()
        job_config.destination = f'{bq_client.project}.pysearchml.tmp'
        job_config.maximum_bytes_billed = 10 * (1024 ** 3)
        job = bq_client.query(query, job_config=job_config)
        job.result()

        # export BigQuery table to GCS
        destination_uri = f'gs://{bucket}/es_docs.gz'
        table_id = 'es_docs'
        table_ref = ds_ref.table(table_id)

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
            row['_index'] = index
            yield row
            c += 1
            if not c % 1000:
                print(c)

    if force_restart or not es.indices.exists(index):
        es.indices.delete(index, ignore=[400, 404])
        print('deleted index')
        es.indices.create(index, **schema)
        print('schema created')
        bulk(es, read_file(bucket), request_timeout=30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--force_restart',
        dest='force_restart',
        type=bool,
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

    args, _ = parser.parse_known_args(sys.argv[1:])
    upload_data(args.bucket, args.es_host, args.force_restart)
