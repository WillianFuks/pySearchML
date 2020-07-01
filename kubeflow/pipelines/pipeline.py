import pathlib
from typing import Dict, List, Any

from kfp import components, dsl
from helper import update_op_project_id_img


PATH = pathlib.Path(__file__).parent


def get_ranker_parameters(ranker: str) -> List[Dict[str, Any]]:
    return {
        'lambdamart': [
            {
                "name": "--x",
                "parameterType": "double",
                "feasibleSpace": {
                    "min": "0.01",
                    "max": "3.03"
                }
            }
        ]
    }.get(ranker)


@dsl.pipeline(
    name='Train Lambda Mart Pipeline',
    description=('Responsible for generating all datasets and optimization process for'
                 ' the chosen Ranker algorithm.')
)
def build_lambdamart_pipeline(
    bucket='pysearchml',
    es_host='elasticsearch.elastic-system.svc.cluster.local:9200',
    force_restart=False,
    train_init_date='20170801',
    train_end_date='20170801',
    validation_init_date='20170802',
    validation_end_date='20170802',
    model_name='lambdamart0',
    ranker='lambdamart'
):

    components_path = PATH.parent / 'components'

#     component_path = main_path / 'gcs' / 'component.yaml'
    # gs_op_ = components.load_component_from_file(str(component_path))
    # gs_op_ = update_op_project_id_img(gs_op_)
#     gs_op = gs_op_('gs://pysearchml/requirements.txt', '.').set_display_name('GS')

    component_path = components_path / 'prepare_env' / 'component.yaml'
    prepare_op_ = components.load_component_from_file(str(component_path))
    prepare_op_ = update_op_project_id_img(prepare_op_)

    prepare_op = prepare_op_(
        bucket=bucket,
        es_host=es_host,
        force_restart=force_restart,
        model_name=model_name
    ).set_display_name('Preparing Environment')

    component_path = components_path / 'data' / 'validation' / 'component.yaml'
    validation_op_ = components.load_component_from_file(str(component_path))
    validation_op_ = update_op_project_id_img(validation_op_)

    val_reg_op = validation_op_(
        bucket=f'{bucket}/validation/regular',
        validation_init_date=validation_init_date,
        validation_end_date=validation_end_date
    ).set_display_name('Build Regular Validation Dataset.').after(prepare_op)

    val_train_op = validation_op_(
        bucket=f'{bucket}/validation/train',
        validation_init_date=train_init_date,
        validation_end_date=train_end_date
    ).set_display_name('Build Validation Dataset of Train Data.').after(prepare_op)

    data_component_path = components_path / 'data' / 'train' / 'component.yaml'
    train_op_ = components.load_component_from_file(str(data_component_path))
    train_op_ = update_op_project_id_img(train_op_)

    train_op = train_op_(
        bucket=bucket,
        train_init_date=train_init_date,
        train_end_date=train_end_date,
        es_host=es_host,
        model_name=model_name
    ).set_display_name('Build Train RankLib Dataset.').after(prepare_op)

    model_component_path = component_path / 'model' / 'component.yaml'
    model_op_ = components.load_component_from_file(str(model_component_path))

    model_op = model_op_(
        name='lambdamart',
        parameters=get_ranker_parameters(ranker),
        train_file_path=train_op.outputs['destination'],
        validation_files_path=val_reg_op.outputs['destination'],
        validation_train_files_path=val_train_op.outputs['destination'],
    ).set_display_name('Launch Katib Optimization').after(
        [val_reg_op, val_train_op, train_op]
    )

    _ = dsl.ContainerOp(
        name="my-out-cop",
        image="library/bash:4.4.23",
        command=["sh", "-c"],
        arguments=["echo hyperparameter: %s" % model_op.output],
    )
