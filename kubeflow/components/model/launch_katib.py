import os
import argparse
import json
import uuid
import pathlib

import launch_crd
from kubernetes import client as k8s_client
from kubernetes import config


PATH = pathlib.Path(__file__).parent


class Experiment(launch_crd.K8sCR):
    def __init__(self, client=None):
        super().__init__('kubeflow.org', 'experiments', 'v1alpha3', client)

    def is_expected_conditions(self, instance, expected_conditions):
        conditions = instance.get('status', {}).get('conditions')
        if not conditions:
            return False, ''
        if conditions[-1]['type'] in expected_conditions:
            return True, conditions[-1]['type']
        else:
            return False, conditions[-1]['type']


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--name',
        dest='name',
        type=str,
        help='Experiment name.'
    )
    parser.add_argument(
        '--destination',
        dest='destination',
        type=str,
        help='The file which stores the best trial of the experiment.'
    )
    parser.add_argument(
        '--parameters',
        dest='parameters',
        type=list,
        help=('List of Dict containing the definition of each parameter to be '
              'used for each Ranker.')
    )
    parser.add_argument(
        '--train_file_path',
        dest='train_file_path',
        type=str,
        help='Location where training data is located.'
    )
    parser.add_argument(
        '--validation_files_path',
        dest='validation_files_path',
        type=str,
        help='Location where validation data is located.'
    )
    parser.add_argument(
        '--validation_train_files_path',
        dest='validation_train_files_path',
        type=str,
        help='Location where validation of training data is located.'
    )
    parser.add_argument(
        '--es_host',
        dest='es_host',
        type=str,
        help='Name host of Elasticsearch.'
    )
    parser.add_argument(
        '--model_name',
        dest='model_name',
        type=str,
        help='Name of feature set saved in Elasticsearch.'
    )
    parser.add_argument(
        '--ranker',
        dest='ranker',
        type=str,
        help='RankLib algorith to use.'
    )

    args = parser.parse_args()

    exp_json_file = PATH / 'experiment.json'
    exp_def = json.loads(open(str(exp_json_file).read()))

    raw_template = exp_def['spec']['trialTemplate']['goTemplate']['rawTemplate']
    raw_template = raw_template.format(
        PROJECT_ID=os.getenv('PROJECT_ID'),
        train_file_path=args.train_file_path,
        validation_files_path=args.validation_files_path,
        validation_train_files_path=args.validation_train_files_path,
        es_host=args.es_host,
        destination=args.destination,
        model_name=args.model_name,
        ranker=args.ranker
    )

    print('raw template: ', raw_template)

    exp_def['spec']['trialTemplate']['goTemplate']['rawTemplate'] = raw_template
    exp_def['spec']['parameters'] = args.parameters

    config.load_incluster_config()
    api_client = k8s_client.ApiClient()
    experiment = Experiment(client=api_client)
    exp_name = f'{args.name}-{uuid.uuid4().hex}'

    create_response = experiment.create(exp_def)

    print('create response: ', create_response)

    expected_conditions = ["Succeeded", "Failed"]
    current_exp = experiment.wait_for_condition(exp_name, expected_conditions)
    expected, conditon = experiment.is_expected_conditions(current_exp, ["Succeeded"])

    if expected:
        params = current_exp["status"]["currentOptimalTrial"]["parameterAssignments"]
        print(params)
        # if not os.path.exists(os.path.dirname(args.outputFile)):
        #    # os.makedirs(os.path.dirname(args.outputFile))
        # with open(args.outputFile, 'w') as f:
        #     f.write(json.dumps(paramAssignments))


if __name__ == "__main__":
    main()
