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
    bucket='pysearchml',
    es_host='elasticsearch.elastic-system.svc.cluster.local',
    force_restart='false'
):

    main_path = PATH.parent.parent / 'components'

#     component_path = main_path / 'gcs' / 'component.yaml'
    # gs_op_ = components.load_component_from_file(str(component_path))
    # gs_op_ = update_op_project_id_img(gs_op_)
#     gs_op = gs_op_('gs://pysearchml/requirements.txt', '.').set_display_name('GS')

    component_path =  main_path / 'prepare_env' / 'component.yaml'
    prepare_op_ = components.load_component_from_file(str(component_path))
    prepare_op_ = update_op_project_id_img(prepare_op_)

    prepare_op = prepare_op_(
        bucket=bucket,
        es_host=es_host,
        force_restart=force_restart
    ).set_display_name('Preparing Environment')
