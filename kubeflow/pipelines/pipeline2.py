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
    train_init_date='20170801',
    train_end_date='20170801',
    validation_init_date='20170802',
    validation_end_date='20170802',
    model_name='lambdamart0',
    ranker='lambdamart'
):

    pvc = dsl.PipelineVolume(pvc='pysearchml-pvc')

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
            '--destination=/data/validation_regular'
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
            '--destination=/data/validation_train'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Build Train Validation Dataset').after(prepare_op)

    train_dataset_op = dsl.ContainerOp(
        name='train dataset',
        image=f'gcr.io/{PROJECT_ID}/data_train',
        arguments=[
            f'--bucket={bucket}',
            f'--train_init_date={train_init_date}',
            f'--train_end_date={train_end_date}',
            f'--es_host={es_host}',
            f'--model_name={model_name}',
            '--destination=/data/train'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Build Training Dataset').after(prepare_op)

    _ = dsl.ContainerOp(
        name='pySearchML Bayesian Optimization Model',
        image=f'gcr.io/{PROJECT_ID}/model',
        command=['python', '/model/launch_katib.py'],
        arguments=[
            f'--es_host={es_host}',
            f'--model_name={model_name}',
            f'--ranker={ranker}',
            '--name=pysearchml',
            '--train_file_path=/data/train/train_dataset.txt',
            '--validation_files_path=/data/validation_regular',
            '--validation_train_files_path=/data/validation_train',
            '--destination=/data/model'
        ],
        pvolumes={'/data': pvc}
    ).set_display_name('Katib Optimization Process').after(val_reg_dataset_op,
                                                           val_train_dataset_op,
                                                           train_dataset_op)


    # model_op = model_op_(
        # name='lambdamart',
        # train_file_path=train_op.outputs['destination'],
        # validation_files_path=val_reg_op.outputs['destination'],
        # validation_train_files_path=val_train_op.outputs['destination'],
        # es_host=es_host,
        # model_name=model_name,
        # ranker=ranker
    # ).set_display_name('Launch Katib Optimization').after(val_reg_op,
                                                          # val_train_op,
                                                          # train_op)

  #   _ = dsl.ContainerOp(
        # name="my-out-cop",
        # image="library/bash:4.4.23",
        # command=["sh", "-c"],
        # arguments=["echo hyperparameter: %s" % model_op.output],
  #   )
