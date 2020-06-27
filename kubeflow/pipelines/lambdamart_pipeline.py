import pathlib

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
    force_restart=False,
    train_init_date='20170801',
    train_end_date='20170801',
    validation_init_date='20170802',
    validation_end_date='20170802',
    model_name='lambdamart0'
):

    main_path = PATH.parent.parent / 'components'

#     component_path = main_path / 'gcs' / 'component.yaml'
    # gs_op_ = components.load_component_from_file(str(component_path))
    # gs_op_ = update_op_project_id_img(gs_op_)
#     gs_op = gs_op_('gs://pysearchml/requirements.txt', '.').set_display_name('GS')

    component_path = main_path / 'prepare_env' / 'component.yaml'
    prepare_op_ = components.load_component_from_file(str(component_path))
    prepare_op_ = update_op_project_id_img(prepare_op_)

    prepare_op = prepare_op_(
        bucket=bucket,
        es_host=es_host,
        force_restart=force_restart,
        model_name=model_name
    ).set_display_name('Preparing Environment')

    component_path = main_path / 'data' / 'validation' / 'component.yaml'
    validation_op_ = components.load_component_from_file(str(component_path))
    validation_op_ = update_op_project_id_img(validation_op_)

    _ = validation_op_(
        bucket=f'{bucket}/validation/regular',
        validation_init_date=validation_init_date,
        validation_end_date=validation_end_date
    ).set_display_name('Build Regular Validation Dataset.').after(prepare_op)

    _ = validation_op_(
        bucket=f'{bucket}/validation/train',
        validation_init_date=train_init_date,
        validation_end_date=train_end_date
    ).set_display_name('Build Validation Dataset of Train Data.').after(prepare_op)
