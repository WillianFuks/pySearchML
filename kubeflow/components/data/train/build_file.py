import argparse
import os
import json
import glob
import gzip
import sys
import pathlib
import uuid
from shutil import rmtree
from typing import List, NamedTuple, Dict, Any, Iterator, Tuple

import numpy as np
from elasticsearch import Elasticsearch
from google.cloud import storage, bigquery
from pyClickModels import DBN


"""
Module responsible for creating the final RankLib text file used as input for its
training process. For information is available at:

    https://sourceforge.net/p/lemur/wiki/RankLib%20How%20to%20use/

"""


PATH = pathlib.Path(__file__).parent


def build_judgment_files(model_name: str) -> None:
    """
    Uses DBN Models and the clickstream data to come up with the Judgmnets inferences.

    Args
    ----
      model_name: str
          Name of model that specifies experiment on Kubeflow.
    """
    model = DBN.DBNModel()

    clickstream_files_path = f'/tmp/pysearchml/{args.model_name}/clickstream/'

    model_path = f'/tmp/pysearchml/{args.model_name}/model/model.gz'
    rmtree(os.path.dirname(model_path), ignore_errors=True)
    os.makedirs(os.path.dirname(model_path))

    judgment_files_path = f'/tmp/pysearchml/{args.model_name}/judgments/judgments.gz'
    rmtree(os.path.dirname(judgment_files_path), ignore_errors=True)
    os.makedirs(os.path.dirname(judgment_files_path))

    model.fit(clickstream_files_path, iters=10)
    model.export_judgments(model_path)

    with gzip.GzipFile(judgment_files_path, 'wb') as f:
        for row in gzip.GzipFile(model_path):
            row = json.loads(row)
            result = []

            # search_keys is something like:
            # {"search_term:query|brand:brand_name|context:value}
            # Notice thatonly the `search_term` is always available. Other keys depends
            # on the chosen context when training the model, i.e., one can choose to
            # add the brand information or not and so on.
            search_keys = list(row.keys())[0]
            docs_judgments = row[search_keys]
            search_keys = dict(e.split(':') for e in search_keys.split('|'))

            judgments_list = [judge for doc, judge in docs_judgments.items()]

            # It means all judgments expectations are equal which is not desirable
            if all(x == judgments_list[0] for x in judgments_list):
                continue

            # We devire judgments based on percentiles from 20% up to 100%
            percentiles = np.percentile(judgments_list, [20, 40, 60, 80, 100])

            judgment_keys = [
                {
                    'doc': doc,
                    'judgment': process_judgment(percentiles, judgment)
                }
                for doc, judgment in docs_judgments.items()
            ]

            result = {
                'search_keys': search_keys,
                'judgment_keys': judgment_keys
            }
            f.write(json.dumps(result).encode() + '\n'.encode())


def process_judgment(percentiles: list, judgment: float) -> int:
    """
    Returns which quantile the current value of `judgment` belongs to. The result is
    already transformed to range between integers 0 and 4 inclusive.

    Args
    ----
      judgents_list: np.array
          All judgments computed for given query
      judgment: float
          Current judgment value being computed.

    Returns
    -------
      judgment: int
          Integer belonging to 0 and 4, inclusive. 0 means the current document is not
          appropriate for current query whereas 4 means it's a perfect fit.
    """
    if judgment <= percentiles[0]:
        return 0
    if judgment <= percentiles[1]:
        return 1
    if judgment <= percentiles[2]:
        return 2
    if judgment <= percentiles[3]:
        return 3
    if judgment <= percentiles[4]:
        return 4


def build_file(
    model_name: str,
    index: str,
    es_batch: int,
    es_client
) -> None:
    """
    After the input file has been updated with judgment data, logs features from
    Elasticsearch which results in the final text file used as input for RankLib.

    Args
    ----
      model_name: str
          Name to identify experiment in Kubeflow
      index: str
          Index to use from Elasticsearch
      es_batch: int
          Sets how many queries to aggregate when using multisearch API.
      es_client: Elasticsearch
          Python Elasticsearch client
    """
    counter = 1
    # works as a pointer
    queries_counter = [0]
    search_arr, judge_list = [], []

    for search_keys, docs, judgments in read_judgment_files(model_name):
        judge_list.append(judgments)

        search_arr.append(json.dumps({'index': index}))
        search_arr.append(json.dumps(get_logging_query(model_name, docs, search_keys)))

        if counter % es_batch == 0:
            write_features(model_name, search_arr, judge_list, queries_counter,
                           es_client)
            search_arr, judge_list = [], []

        counter += 1

    if search_arr:
        write_features(model_name, search_arr, judge_list, queries_counter,
                       es_client)


def write_features(
    model_name: str,
    search_arr: List[str],
    judge_list: List[List[str]],
    queries_counter: List[int],
    es_client: Elasticsearch
) -> None:
    """
    Sends the query to Elasticsearch and uses the result to write final RankLib training
    file.

    Args
    ----
      model_name: str
          Name that identifies experiment on Kubeflow
      search_arr: List[str]
          Array containing multiple queries to send against Elasticsearch
      judge_list: List[List[str]]
          Each index contains list of judgments associated to a respective search
      file_: io.TextIO
      queries_counter: List[int]
          Counter of how many queries were processed so far. It's used to build the
          RankLib file with appropriate values. It's a list so it works as a C pointer.
      es: Elasticsearch
          Python client for interacting with Elasticsearch
    """
    if not search_arr:
        return

    multi_request = os.linesep.join(search_arr)
    features_log = es_client.msearch(body=multi_request, request_timeout=60)

    rows = []
    for i in range(len(judge_list)):
        es_result = features_log['responses'][i].get('hits', {}).get('hits')

        if not es_result or len(es_result) == 1:
            continue

        for j in range(len(es_result)):
            logs = es_result[j]['fields']['_ltrlog'][0]['main']
            features = [
                f'{idx+1}:{logs[idx].get("value", 0)}' for idx in range(len(logs))
            ]
            features = '\t'.join(features)
            ranklib_entry = f'{judge_list[i][j]}\tqid:{queries_counter[0]}\t{features}'
            rows.append(ranklib_entry)
        queries_counter[0] += 1

    if rows:
        path = f'/tmp/pysearchml/{model_name}/data/train/ranklib_train.txt'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a') as f:
            f.write(os.linesep.join(rows) + os.linesep)


def get_logging_query(
    model_name: str,
    docs: List[str],
    search_keys: Dict[str, Any]
) -> Dict[str, Any]:
    """
    The process to extract features from Elasticsearch involves sending what is known
    as the "logging query". The result of the loggin query is the values, for a given
    search query, of each feature as defined in feature set.

    Args
    ----
      model_name: str
          Each Kubeflow run receives a model_name so it's possible to discern each
          experiment. This value is used to store different models on Elasticsearch.
      docs: List[str]
          List containing several documents (skus for instance) to be inserted in the
          query so it's possible to send several requests in just one request.
      search_keys: Dict[str, Any]
          Those are the keys that describe the search context. It can contain
          data such as the region of customers, their favorite brands, their average
          purchasing ticket and so on.

    Returns
    -------
      log_query: Dict[str, Any]
          Query to be sent against Elasticsearch in order to find the values of each
          feature as defined in featureset.
    """
    log_query = {
        "query": {
            "bool": {
                "filter": [
                    {
                        "terms": {
                            "_id": ""
                        }
                    }
                ],
                "should": [
                    {
                        "sltr": {
                            "_name": "logged_featureset",
                            "featureset": model_name,
                            "params": {}
                        }
                    }
                ]
            }
        },
        "_source": ['_id'],
        "ext": {
            "ltr_log": {
                "log_specs": {
                    "name": "main",
                    "named_query": "logged_featureset"
                }
            }
        }
    }
    log_query['query']['bool']['filter'][0]['terms']['_id'] = docs
    log_query['query']['bool']['should'][0]['sltr']['params'] = search_keys
    return log_query


def read_judgment_files(
    model_name: str
) -> Iterator[Tuple[Dict[str, Any], List[str], List[str]]]:
    """
    Reads resulting files of the judgments updating process.
    """
    files = glob.glob(f'/tmp/pysearchml/{model_name}/data/judgments/*.gz')
    for file_ in files:
        for row in gzip.GzipFile(file_):
            row = json.loads(row)
            search_keys = row['search_keys']
            judgment_keys = row['judgment_keys']
            docs = [e['doc'] for e in judgment_keys]
            judgments = [e['judgment'] for e in judgment_keys]
            yield search_keys, docs, judgments


def download_data(args: NamedTuple):
    """
    Queries over GA data for input training dataset creation. The table is first
    exported to GS and then downloaded to respective folder, as is.

    Args
    ----
      args: NamedTuple
        train_init_date: str
            Follows format %Y%M%D, represents from where the query should start
            retrieving data from.
        train_end_date: str
        model_name: str
            Name that uniquely identifies model on Kubeflow experiments.
    """
    path_to_download = f'/tmp/pysearchml/{args.model_name}/clickstream'
    rmtree(path_to_download, ignore_errors=True)
    os.makedirs(path_to_download, exist_ok=True)

    storage_client = storage.Client()
    bq_client = bigquery.Client()

    ds_ref = bq_client.dataset('pysearchml')
    table_id = str(uuid.uuid4()).replace('-', '')
    table_ref = ds_ref.table(table_id)

    # Query GA data
    query_path = PATH / 'train.sql'
    query = open(str(query_path)).read()
    query = query.format(train_init_date=args.train_init_date,
                         train_end_date=args.train_end_date)

    job_config = bigquery.QueryJobConfig()
    job_config.destination = f'{bq_client.project}.pysearchml.{table_id}'
    job_config.maximum_bytes_billed = 10 * (1024 ** 3)
    job_config.write_disposition = 'WRITE_TRUNCATE'
    job = bq_client.query(query, job_config=job_config)
    job.result()

    # export BigQuery table to GCS
    destination_uri = f'gs://{args.bucket}/{args.model_name}/train/*.gz'

    extract_config = bigquery.ExtractJobConfig()
    extract_config.compression = 'GZIP'
    extract_config.destination_format = 'NEWLINE_DELIMITED_JSON'
    job = bq_client.extract_table(table_ref, destination_uri, job_config=extract_config)
    job.result()

    # Download data
    bucket_obj = storage_client.bucket(args.bucket)
    blobs = bucket_obj.list_blobs(prefix=f'{args.model_name}/train/')
    for blob in blobs:
        blob.download_to_filename(
            f"{path_to_download}/judgments_{blob.name.split('/')[-1]}"
        )

    # Delete BQ Table
    bq_client.delete_table(table_ref)


def main(args: NamedTuple, es_client: Elasticsearch) -> None:
    """
    Uses as input data from Google Analytics containing customers clickstream for Search
    Result Pages. This data is processed with the Judgments model as described in
    [pyClickModels](https://github.com/WillianFuks/pyClickModels) and features are
    derived from Elasticsearch.

    The resulting text file is like:

    judgment    qid    feature_1 ...   feature_N
    4           qid:1  1:0.56    ...   2:1.3
    4           qid:1  1:2.90    ...   2:1.09
    3           qid:1  1:3.00    ...   2:5.51

    This text file is what we use as input for training models in RankLib.

    Args
    ----
      args: List
          List of input arguments from `sys.argv`
      es_client: Elasticsearch
          Python Elasticsearch client
    """
    # download_data(args)
    build_judgment_files(args.model_name)
    # build_file(args.model_name, args.index, args.es_batch, es_client)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--train_init_date',
        dest='train_init_date',
        type=str,
        help=('Value to replace in BigQuery SQL. Represents date from where to start '
              'quering from. Format follows %Y%M%D.')
    )
    parser.add_argument(
         '--train_end_date',
         dest='train_end_date',
         type=str,
         help=('Value to replace in BigQuery SQL. Represents date from where to start '
               'quering from. Format follows %Y%M%D.')
    )
    parser.add_argument(
        '--bucket',
        dest='bucket',
        type=str,
        default='pysearchml',
        help='Google Cloud Storage Bucket where all data will be stored.'
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
        help=('Assigns a name for the RankLib model. Each experiment on Kubeflow '
              'should have a specific name in order to preserver their results.')
    )
    parser.add_argument(
        '--es_batch',
        dest='es_batch',
        type=int,
        default=1000,
        help=('Determines how many items to send at once to Elasticsearch when using '
              'multisearch API.')
    )
    args, _ = parser.parse_known_args(sys.argv[1:])
    es_client = Elasticsearch(hosts=[args.es_host])
    main(args, es_client)