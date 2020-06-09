import os
import kfp
import fire
from datetime import datetime


def update_op_project_id_img(op):
    project_id = os.getenv('PROJECT_ID')
    if not project_id:
        raise Exception('Please set an $PROJECT_ID env value.')
    img = op.component_spec.implementation.container.image
    img = img.format(PROJECT_ID=project_id)
    op.component_spec.implementation.container.image = img
    return op


def get_pipe_by_name(client, name):
    # Tries to read pipeline. If fails, assumes pipe doesnt exist.
    try:
        pipes = client.list_pipelines()
        pipeline = [pipe for pipe in pipes.pipelines if pipe.name == name]
    except:
        pipeline = None

    if pipeline:
        pipeline = pipeline[0]
    return pipeline


def deploy_pipeline(ranker, host, version):
    client = kfp.Client(host=host)
    name = f'pysearchml_{ranker}_{version}'
    # Supposed page_token is not necessary for this application

    pipeline = get_pipe_by_name(client, name)
    if not pipeline:
        pipeline = client.upload_pipeline(
            pipeline_package_path=f'{ranker}_pipeline.tar.gz',
            pipeline_name=name
        )


def run_experiment(ranker, host, version, experiment_name):
    client = kfp.Client(host=host)
    name = f'pysearchml_{ranker}_{version}'
    pipeline = get_pipe_by_name(client, name)
    if not pipeline:
        raise Exception('Please first create a pipeline before running')
    run_id = f'experiment_{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    experiment = client.create_experiment(name=experiment_name)
    params = json.loads(open('params.json').read())
    client.run_pipeline(experiment.id, job_name=run_id, params=params,
                        pipeline_id=pipeline.id)


def main(action, host, ranker='lambdamart', **kwargs):
    """`ranker` is one of the algorithms available in RankLib."""
    if action == 'deploy-pipeline':
        version = kwargs.get('version')
        deploy_pipeline(ranker, host, version)
    elif action == 'run-pipeline':
        experiment_name = kwargs['experiment_name']
        run_experiment(experiment_name)
    else:
        raise ValueError(f'Invalid operation name: {function}.')


if __name__ == '__main__':
    fire.Fire(main)
