import os
import kfp
import fire
from datetime import datetime


client = kfp.Client()


def deploy_pipeline(ranker, version=None):
    name = f'pysearchml_{ranker}{"_" + version if version else ""}'

    pipeline = client.upload_pipeline(
        pipeline_package_path=f'kubeflow/pipelines/{ranker}_pipeline.tar.gz',
        pipeline_name=name
    )
    pipeline_id = pipeline.id

def run_experiment(experiment_name):
    run_id = f'experiment_run_{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    experiment = client.create_experiment(name=experiment_name)
    params = json.loads(open('kubeflow/pipelines/params.json').read())
    client.run_pipeline(experiment.id, job_name=run_id, pipeline_id=pipeline_id,
                        params=settings)



def main(action, ranker='lambdamart', **kwargs):
    """ranker is one of the algorithms available in RankLib."""
    if action == 'deploy-pipeline':
        version = args['version']
        run = 'run' in args
        deploy_pipeline(version, experiment_name, run)
    elif action == 'run-pipeline':
        experiment_name = args['experiment_name']
        run_experiment(experiment_name)
    else:
        raise ValueError(f'Invalid operation name: {function}.')


if __name__ == '__main__':
    fire.Fire(main)
