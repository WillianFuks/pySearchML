import os
import pathlib

from kfp import dsl


PATH = pathlib.Path(__file__).parent
PROJECT_ID = os.getenv('PROJECT_ID')


@dsl.pipeline(
    name='Train Lambda Mart Pipeline',
    description=('Responsible for generating all datasets and optimization process for'
                 ' the chosen Ranker algorithm.')
)
def build_pipeline(
    bucket='pysearchml',
    es_host='elasticsearch.elastic-system.svc.cluster.local:9200',
    force_restart=False,
    train_init_date='20160801',
    train_end_date='20160801',
    validation_init_date='20160802',
    validation_end_date='20160802',
    test_init_date='20160802',
    test_end_date='20160802',
    model_name='lambdamart0',
    ranker='lambdamart',
    index='pysearchml'
):
    pvc = dsl.PipelineVolume(pvc='pysearchml-nfs')

    prepare_op = dsl.ContainerOp(
        name='prepare env',
        image=f'gcr.io/{PROJECT_ID}/prepare_env',
        arguments=[
            f'--force_restart={force_restart}',
            f'--es_host={es_host}',
            f'--bucket={bucket}',
            f'--model_name={model_name}'
        ],
        pvolumes={'/data': pvc}
    )

    val_reg_dataset_op = dsl.ContainerOp(
        name='validation regular dataset',
        image=f'gcr.io/{PROJECT_ID}/data_validation',
        arguments=[
            f'--bucket={bucket}/validation/regular',
            f'--validation_init_date={validation_init_date}',
            f'--validation_end_date={validation_end_date}',
            '--destination=/data/pysearchml/{model_name}/validation_regular'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Build Regular Validation Dataset').after(prepare_op)

    val_train_dataset_op = dsl.ContainerOp(
        name='validation train dataset',
        image=f'gcr.io/{PROJECT_ID}/data_validation',
        arguments=[
            f'--bucket={bucket}/validation/train',
            f'--validation_init_date={train_init_date}',
            f'--validation_end_date={train_end_date}',
            '--destination=/data/pysearchml/{model_name}/validation_train'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Build Train Validation Dataset').after(prepare_op)

    val_test_dataset_op = dsl.ContainerOp(
        name='validation test dataset',
        image=f'gcr.io/{PROJECT_ID}/data_validation',
        arguments=[
            f'--bucket={bucket}/validation/test',
            f'--validation_init_date={test_init_date}',
            f'--validation_end_date={test_end_date}',
            f'--destination=/data/pysearchml/{model_name}/validation_test'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Build Test Validation Dataset').after(prepare_op)

    train_dataset_op = dsl.ContainerOp(
        name='train dataset',
        image=f'gcr.io/{PROJECT_ID}/data_train',
        command=['python', '/train/run.py'],
        arguments=[
            f'--bucket={bucket}',
            f'--train_init_date={train_init_date}',
            f'--train_end_date={train_end_date}',
            f'--es_host={es_host}',
            f'--model_name={model_name}',
            '--destination=/data/pysearchml/{model_name}/train'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Build Training Dataset').after(prepare_op)

    katib_op = dsl.ContainerOp(
        name='pySearchML Bayesian Optimization Model',
        image=f'gcr.io/{PROJECT_ID}/model',
        command=['python', '/model/launch_katib.py'],
        arguments=[
            f'--es_host={es_host}',
            f'--model_name={model_name}',
            f'--ranker={ranker}',
            '--name=pysearchml',
            '--train_file_path=/data/pysearchml/{model_name}/train/train_dataset.txt',
            '--validation_files_path=/data/pysearchml/{model_name}/validation_regular',
            ('--validation_train_files_path=/data/pysearchml/{model_name}/'
             'validation_train'),
            '--destination=/data/pysearchml/{model_name}/'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Katib Optimization Process').after(
        val_reg_dataset_op, val_train_dataset_op, val_test_dataset_op, train_dataset_op
    )

    post_model_op = dsl.ContainerOp(
        name='Post Best RankLib Model to ES',
        image=f'gcr.io/{PROJECT_ID}/model',
        command=['python', '/model/post_model.py'],
        arguments=[
            f'--es_host={es_host}',
            f'--model_name={model_name}',
            '--destination=/data/pysearchml/{model_name}/best_model.txt'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Post RankLib Model to ES').after(katib_op)

    _ = dsl.ContainerOp(
        name='Test Model',
        image=f'gcr.io/{PROJECT_ID}/model',
        command=['python', '/model/test.py'],
        arguments=[
            f'--files_path=/data/pysearchml/{model_name}/validation_test',
            f'--index={index}',
            f'--es_host={es_host}',
            f'--model_name={model_name}',
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Run Test Step').after(post_model_op)
