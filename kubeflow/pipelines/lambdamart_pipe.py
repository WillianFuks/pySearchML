import subprocess

import kfp
from kfp import components, dsl


@dsl.pipeline(
    name='Train Lambda Mart Pipeline',
    description='Responsible for generating all datasets and optimization of the Lambda Mart Algorithm from RankLib'
)
def build_lambdamart_pipeline(
    bucket,
    es_host,
    force_restart='false'
):
    prepare_op_ = components.load_component_from_file(
        './kubeflow/components/prepare_env/component.yaml'
    )

    prepare_op = prepare_op_(bucket, es_host, force_restart).\
        set_display_name('Preparing Environment')
