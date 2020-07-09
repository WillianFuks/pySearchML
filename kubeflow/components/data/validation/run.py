import sys
import os
import argparse
import pathlib
import uuid
from shutil import rmtree

from google.cloud import storage, bigquery


PATH = pathlib.Path(__file__).parent


def main(validation_init_date, validation_end_date, bucket, destination):
    # Remove everything and deletes destination folder to receive new files.
    rmtree(destination, ignore_errors=True)
    os.makedirs(destination, exist_ok=True)

    storage_client = storage.Client()
    bq_client = bigquery.Client()

    ds_ref = bq_client.dataset('pysearchml')

    table_id = str(uuid.uuid4().hex)
    table_ref = ds_ref.table(table_id)

    # Query GA data
    query_path = PATH / 'validation.sql'
    query = open(str(query_path)).read()
    query = query.format(validation_init_date=validation_init_date,
                         validation_end_date=validation_end_date)

    job_config = bigquery.QueryJobConfig()
    job_config.destination = f'{bq_client.project}.pysearchml.{table_id}'
    job_config.maximum_bytes_billed = 10 * (1024 ** 3)
    job_config.write_disposition = 'WRITE_TRUNCATE'
    job = bq_client.query(query, job_config=job_config)
    job.result()

    # export BigQuery table to GCS
    # bucket will be set in accordance to which validation dataset is referenced, i.e.,
    # whether regular validation or validation for the training dataset.
    destination_uri = f"gs://{bucket}/validation*.gz"

    extract_config = bigquery.ExtractJobConfig()
    extract_config.compression = 'GZIP'
    extract_config.destination_format = 'NEWLINE_DELIMITED_JSON'
    job = bq_client.extract_table(table_ref, destination_uri, job_config=extract_config)
    job.result()

    # Download data
    bucket_obj = storage_client.bucket(bucket.split('/')[0])
    blobs = bucket_obj.list_blobs(prefix=bucket.partition('/')[-1])
    for blob in blobs:
        blob.download_to_filename(f"{destination}/{blob.name.split('/')[-1]}")
        blob.delete()

    # delete BQ table
    bq_client.delete_table(table_ref)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--validation_init_date',
        dest='validation_init_date',
        type=str,
        help='Date in format %Y%M%D from when to start querying GA data'
    )
    parser.add_argument(
        '--validation_end_date',
        dest='validation_end_date',
        type=str,
        help='Date in format %Y%M%D from when to stop querying GA data'
    )
    parser.add_argument(
        '--bucket',
        dest='bucket',
        type=str
    )
    parser.add_argument(
        '--destination',
        dest='destination',
        type=str,
        help='Path where validation dataset gzipped files will be stored.'
    )

    args, _ = parser.parse_known_args(sys.argv[1:])
    main(
        args.validation_init_date,
        args.validation_end_date,
        args.bucket,
        args.destination
    )
