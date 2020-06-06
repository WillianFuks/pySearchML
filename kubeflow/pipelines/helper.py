import os
import kfp
import fire
from datetime import datetime


client = kfp.Client()


def update_op_project_id_img(op):
    project_id = os.getenv('PROJECT_ID')
    if not project_id:
        raise Exception('Please set an $PROJECT_ID env value.')
    img = op.component_spec.implementation.container.image
    img = img.format(PROJECT_ID=project_id)
    op.component_spec.implementation.container.image = img
    return op


def deploy_pipeline(ranker, version=None):
    name = f'pysearchml_{ranker}{"_" + version if version else ""}'

    pipeline = client.upload_pipeline(
        pipeline_package_path=f'kubeflow/pipelines/{ranker}_pipeline.tar.gz',
        pipeline_name=name
    )
    pipeline_id = pipeline.id


def run_experiment(experiment_name):
    run_id = f'experiment_{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    experiment = client.create_experiment(name=experiment_name)
    params = json.loads(open('params.json').read())
    client.run_pipeline(experiment.id, job_name=run_id, params=settings)


def main(action, ranker='lambdamart', **kwargs):
    """`ranker` is one of the algorithms available in RankLib."""
    if action == 'deploy-pipeline':
        version = args.get('version')
        deploy_pipeline(version, experiment_name)
    elif action == 'run-pipeline':
        experiment_name = args['experiment_name']
        run_experiment(experiment_name)
    else:
        raise ValueError(f'Invalid operation name: {function}.')


if __name__ == '__main__':
    fire.Fire(main)