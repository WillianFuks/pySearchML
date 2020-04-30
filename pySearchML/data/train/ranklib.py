import argparse
import os
import json
import glob
import random
import gzip
import sys
# import subprocess
import requests
from urllib.parse import urljoin
from collections import defaultdict
import numpy as np
from typing import List, NamedTuple, Dict, io, Any, Iterator, Tuple
from elasticsearch import Elasticsearch


"""
Module responsible for creating the final RankLib text file used as input for its
training process.
"""


def parse_args(args: List) -> NamedTuple:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--init_day_train',
        dest='init_day_train',
        type=str,
        help=('Value to replace in BigQuery SQL. Represents date from where to start '
              'quering from. Format follows %YYYY%MM%DD.')
    )
    parser.add_argument(
        '--end_day_train',
        dest='end_day_train',
        type=str,
        help=('Value to replace in BigQuery SQL. Represents date from where to stop '
              'quering. Format follows %YYYY%MM%DD.')
    )
    parser.add_argument(
        '--restart_ranklib',
        dest='restart_ranklib',
        type=lambda arg: arg.lower() == 'true',
        help=('If `"true"` then deletes any Ranklib feature store saved on '
              'Elasticsearch and re-create it.')
    )
    parser.add_argument(
        '--gcp_project',
        dest='gcp_project',
        type=str,
        default='bigquery-public-data',
        help='project id that should be used when interacting with Google Cloud.'
    )
    parser.add_argument(
        '--bq_dataset',
        dest='bq_dataset',
        type=str,
        help='BigQuery Dataset refering to the Google Analytics input data.'
    )
    parser.add_argument(
        '--gcp_bucket',
        dest='bucket',
        type=str,
        default='pysearchml',
        help='Google Cloud Storage Bucket where all data will be stored.'
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
        help='Determines how many items to send at once to Elasticsearch when using '
             'multisearch API.'
    )


def get_file_obj(model_name: str) -> io.TextIO:
    """
    Creates a text file buffer ready for writing.

    Args
    ----
      model_name: str
          Specifices the name of the experiment running on Kubeflow.
    """
    filename = f'/tmp/pysearchml/{model_name}/data/train/ranklib_input.txt'
    fileobj = open(filename, 'w')
    return fileobj


def create_feature_store(es_host: str, restart_ranklib: bool = False) -> None:
    """
    RankLib uses the concept of "features store" where information about features is
    stored on Elasticsearch. Here, the store is just created but now features are
    defined yet.

    Args
    ----
      restart_ranklib: bool
          If `True` then deletes feature store on Elasticsearch and create it again.
      es_host: str
          Hostname where to reach Elasticsearch.
    """
    feature_store_url = urljoin(es_host, '_ltr')
    if restart_ranklib:
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
    features_path = f'/tmp/pysearchml/{model_name}/data/features/'
    pattern = os.path.join(features_path, '*')
    features_files = glob.glob(os.path.join(features_path, pattern))

    feature_set = {
            'featureset': {
                'name': model_name,
                'features': [process_feature_file(filename) for filename in
                             features_files]
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
    url = f'_ltr/_featureset/{model_name}'
    url = urljoin(es_host, url)
    header = {'Content-Type': 'application/json'}
    resp = requests.post(url, data=json.dumps(feature_set), headers=header)
    if not resp.ok:
        raise Exception(resp.content)


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


def compute_judgments(model_name: str) -> None:
    """
    Uses as input a judgment model to write a new file from previous clickstream, this
    time containing judgment values.

    Args
    ----
      model_name: str
          Name of model that specifies experiment of Kubeflow.
    """
    # filename = f'/tmp/pysearchml/{model_name}/judgments/params.gz'
    # params = json.loads(gzip.GzipFile(filename).read())
    judge_params = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: random.random() / 10))
    )

    filenames = glob.glob(f'/tmp/pysearchml/{model_name}/data/train/clickstream/*.gz')

    for file_ in filenames:
        new_file_ = f'/tmp/pysearchml/{model_name}/data/train/judgments/{file_}'

        with gzip.GzipFile(new_file_, 'wb') as f:
            for row in gzip.GzipFile(file_):
                result = []

                row = json.loads(row)

                search_keys_str = '-'.join(
                    [str(e) for e in sorted(row['search_keys'].values())]
                )

                params = judge_params[search_keys_str]
                judgments = {
                    sku: pars['alpha'] * pars['sigma'] for sku, pars in params.items()
                }

                judgments_list = [j for sku, j in judgments.items()]

                # It means all judgments expectations are equal which is not desirable
                if judgments_list[0] == judgments_list[-1]:
                    continue

                judgment_keys = [
                    {
                        'doc': doc,
                        'judgment': process_judgment(judgments_list, judgment)
                    }
                    for doc, judgment in judgments.items()
                ]
                result = {
                    'search_keys': row['search_keys'],
                    'judgment_keys': judgment_keys
                }
                f.write(json.dumps(result).encode() + '\n'.encode())


def process_judgment(judgments_list: list, judgment: float) -> int:
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
    quantile = np.quantile(judgments_list, judgment)
    if quantile <= 0.2:
        return 0
    if quantile <= 0.4:
        return 1
    if quantile <= 0.6:
        return 2
    if quantile <= 0.8:
        return 3
    if quantile <= 1:
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

    queries_counter = [0]
    search_arr, judge_list = [], []

    for search_keys, docs, judgments in read_judgment_files(model_name):
        judge_list.append(judgments)

        search_arr.append(json.dumps({'index': index}))
        search_arr.append(json.dumps(get_logging_query(model_name, docs, search_keys)))

        if counter % es_batch == 0:
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
        es_result = features_log['response'][i].get('hits', {}).get('hits')

        if not es_result or len(es_result) == 1:
            continue

        for j in range(len(es_result)):
            logs = es_result[j]['fields']['_ltrlog'][0]['main']
            features = [
                f'{idx+1}:logs[idx].get("value", 0)' for idx in range(len(logs))
            ]
            features = '\t'.join(features)
            ranklib_entry = f'{judge_list[i][j]}\tqid:{queries_counter[0]}\t{features}'
            rows.append(ranklib_entry)
        queries_counter[0] += 1

    if rows:
        path = f'/tmp/pysearchml/{model_name}/data/train/ranklib_input.txt'
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
    files = glob.glob(f'/tmp/pysearchml/{model_name}/data/train/judgments/*.gz')
    for file_ in files:
        for row in gzip.GzipFile(file_):
            row = json.loads(row)
            search_keys = row['search_keys']
            judgment_keys = row['judgment_keys']
            docs = [e['doc'] for e in judgment_keys]
            judgments = [e['judgment'] for e in judgment_keys]
            yield search_keys, docs, judgments


def write_ranklib_file(args: List, es_client: Elasticsearch) -> None:
    """
    Uses as input data from Google Analytics containing customers clickstream for Search
    Result Pages. This data is processed with the Judgments model as described in
    pyClickModels and features are derived from Elasticsearch.

    The resulting text file contains information like the following:
    judgment    qid    feature_1    feature_N
    4           qid:1  1:0.56       2:1.3
    4           qid:1  1:2.90       2:1.09
    3           qid:1  1:3.00       2:5.51

    This text file is what we use as input for training models in RankLib.

    Args
    ---------
      args: List
          List of input arguments from `sys.argv`
      es_client: Elasticsearch
          Python Elasticsearch client
    """
    create_feature_set(args.es_host, args.model_name)
    compute_judgments(model_name)
    build_file(model_name, args.index, args.es_batch, es_client)


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    es_client = Elasticsearch(hosts=[args.es_host])
    write_ranklib_file(args, es_client)
