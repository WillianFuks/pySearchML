import os
import pathlib
import subprocess

import kfp
from kfp import components, dsl
from helper import update_op_project_id_img


PATH = pathlib.Path(__file__)


@dsl.pipeline(
    name='Train Lambda Mart Pipeline',
    description=('Responsible for generating all datasets and optimization of the '
                 'Lambda Mart Algorithm from RankLib')
)
def build_lambdamart_pipeline(
    bucket,
    es_host,
    force_restart='false'
):
    component = PATH.parent.parent / 'components' / 'prepare_env' / 'component.yaml'
    prepare_op_ = components.load_component_from_file(str(component))
    prepare_op_ = update_op_project_id_img(prepare_op_)

    prepare_op = prepare_op_(bucket, es_host, force_restart).set_display_name(
        'Preparing Environment'
    )
