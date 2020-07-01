import os
import argparse
import gzip
import glob
import json
import sys
from typing import List, NamedTuple, Any, Dict
from elasticsearch import Elasticsearch
import numpy as np


"""
Script responsible for reading validation data and evaluating the performance of a
trained RankLib model stored on Elasticsearch.
"""


def parse_args(args: List) -> NamedTuple:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--path',
        dest='path',
        type=str,
        help='Path to files containing data of customers searches and their purchases'
    )
    parser.add_argument(
        '--es_query_path',
        dest='es_query_path',
        type=str,
        help=('When validating the trained RankLib model, several distinct queries can '
              'be evaluated. For instance, one query may be a straightforward usage of '
              'the BM25F algorithm whereas another query might use boost factors on '
              'specific fields. The input `es_query_path` lets a specific query be '
              'selected for the validation process.')
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


def validate_model(args: NamedTuple) -> None:
    """
    Reads through an input file of searches and customers purchases. For each search,
    sends the query against Elasticsearch to retrieve a list of documents. This list is
    then compared with what customers purchased for evaluating a rank metric.

    The rank formula is defined in this paper:

    http://yifanhu.net/PUB/cf.pdf

    And is expressed by:

    rank = \frac{\\sum_{u,i}r^t_{ui}rank_{ui}}{\\sum_{u,i}r^t_{ui}}

    `u` is an identification of a given customer, `i` represents items. `r_{ui}` is
    the score a given customer u gave to item i. This score is implicit and here we just
    consider it equal to 1.

    The rank formula is an average of what percentile the purchased item from customers
    are located in the retrieve list of documents from Elasticseasrch operating already
    with the trained RankLib model.

    Notice that we use this function in parallel with multiprocessing. That means that
    its input must be pickleable so Elasticsearch client is instantiated inside the
    function instead of being an input argument. It breaks Injection Dependecy principle
    but still works fine.

    Args
    ----
      args: namedtuple
          General input for running the script
    """
    counter = 1
    search_arr, purchase_arr = [], []
    # Defined as lists which works as pointers
    rank_num, rank_den = [0], [0]
    es_client = Elasticsearch(hosts=[args.es_host])

    files = glob.glob(os.path.join(args.path, '*.gz'))

    for file_ in files:
        for row in gzip.GzipFile(file_):
            row = json.loads(row)
            search_keys, docs = row['search_keys'], row['docs']
            purchase_arr.append(docs)

            search_arr.append(json.dumps({'index': args.index}))
            search_arr.append(json.dumps(get_es_query(search_keys, args)))

            if counter % args.es_batch == 0:
                compute_rank(search_arr, purchase_arr, rank_num, rank_den, es_client)
                search_arr, purchase_arr = [], []

            counter += 1

        if search_arr:
            compute_rank(search_arr, purchase_arr, rank_num, rank_den, es_client)

        # return rank=100% if no document was retrieved from Elasticsearch and purchased
        # by customers.
        return rank_num[0] / rank_den[0] if rank_den[0] else 1


def compute_rank(
    search_arr: List[str],
    purchase_arr: List[List[Dict[str, List[str]]]],
    rank_num: List[float],
    rank_den: List[float],
    es_client: Elasticsearch
) -> None:
    """
    Sends queries against Elasticsearch and compares results with what customers
    purchased. Computes the average rank position of where the purchased document falls
    within the retrieved items.

    Args
    ----
      search_arr: List[str]
          Searches made by customers as observed in validation data. We send those
          against Elasticsearch and compare results with purchased data
      purchase_arr: List[List[Dict[str, List[str]]]]
          List of documents that were purchased by customers
      rank_num: List[float]
          Numerator value of the rank equation. Defined as list to emulate a pointer
      rank_den: List[float]
      es_client: Elasticsearch
          Python Elasticsearch client
    """
    idx = 0
    if not search_arr:
        return

    request = os.linesep.join(search_arr)
    response = es_client.msearch(body=request, request_timeout=60)

    print('response: ', response)
    print('this is purchase_arr ', purchase_arr)

    for hit in response['responses']:
        docs = [doc['_id'] for doc in hit['hits'].get('hits', [])]

        print('this is docs: ', docs)

        if not docs or len(docs) < 2:
            continue

        purchased_docs = [
            docs for purch in purchase_arr[idx] for docs in purch['purchased']
        ]
        ranks = np.where(np.in1d(docs, purchased_docs))[0]
        idx += 1

        print('this is ranks: ', ranks)

        if ranks.size == 0:
            continue

        rank_num[0] += ranks.sum() / (len(docs) - 1)
        rank_den[0] += ranks.size


def get_es_query(
    search_keys: Dict[str, Any],
    args: NamedTuple
) -> str:
    """
    Builds the Elasticsearch query to be used when retrieving data.

    Args
    ----
      args: NamedTuple
        args.search_keys: Dict[str, Any]
            Search query sent by the customer as well as other variables that sets its
            context, such as region, favorite brand and so on.
        args.model_name: str
            Name of RankLib model saved on Elasticsearch
        args.index: str
            Index on Elasticsearch where to retrieve documents
        args.es_query_path: str
            Path where to locate the Elasticsearch query
        args.es_batch: int
            How many documents to retrieve

    Returns
    -------
      query: str
          String representation of final query
    """
    query = open(args.es_query_path).read()
    query = json.loads(query.replace('{query}', search_keys['query']))
    # We just want to retrieve the id of the document to evaluate the ranks between
    # customers purchases and the retrieve list result
    query['_source'] = '_id'
    query['size'] = args.es_batch
    query['rescore']['window_size'] = args.es_batch
    query['rescore']['query']['rescore_query']['sltr']['params'] = search_keys
    query['rescore']['query']['rescore_query']['sltr']['model'] = args.model_name
    return query


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    validate_model(args)
