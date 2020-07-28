import json

from flask import Flask, request, jsonify
from jinja2 import Environment, FileSystemLoader
from elasticsearch import Elasticsearch


es = Elasticsearch('localhost:9200')
app = Flask(__name__)
env = Environment(loader=FileSystemLoader('/front/templates'))


@app.route("/", methods=['GET', 'POST'])
def index():
    index_html = env.get_template('index.html').render()
    return index_html


@app.route("/searchresults", methods=['POST'])
def search():
    try:
        args = request.form.to_dict()
        es_query = open('/front/es_query.json').read()
        print(args)
        input_query = args['search_term']
        size = args.pop('size')
        model_name = args.pop('model_name')

        es_query = es_query.replace('{query}', input_query)
        es_query = json.loads(es_query)
        es_query['size'] = size
        es_query['_source'] = []

        es_query['rescore']['window_size'] = 500
        es_query['rescore']['query']['rescore_query']['sltr']['params'] = args
        es_query['rescore']['query']['rescore_query']['sltr']['model'] = model_name

        if 'ltr_flag' not in args:
            es_query.pop('rescore')

        r = es.search(index='pysearchml', body=es_query).get('hits', {}).get('hits')
        r = [(e['_id'], e['_score']) for e in r]
        return jsonify(r)
        # return env.get_template('documents.j2').render(product_list=r)
    except Exception as e:
        return str(e)
