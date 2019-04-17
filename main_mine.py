from options import Options
from yolo.net.yolonet import Yolonet
from trainers.trainer_coco import Trainer
import tensorflow.python.keras as keras
from tensorflow import keras
import tensorflow as tf
import json
import os

tf.config.gpu.set_per_process_memory_growth(True)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = '1'

opt = Options()
args = opt.opt
args.experiment_name = 'test'
args.learning_rate = 0.00001
args.config_path = './configs/coco.json'
args.total_epoch = 80
args.dataset_root='/home/gwl/datasets/coco2017'
#args.log_iter = 5000
args.resume = 'load_darknet'
# args.do_test = True
net = Yolonet(n_classes=80)
# lr_schedule = keras.optimizers.schedules.PiecewiseConstantDecay(
#   boundaries=[50,100],
#   values=[args.learning_rate, args.learning_rate * 0.1, args.learning_rate * 0.01]
# )
optimizer = keras.optimizers.SGD(learning_rate=args.learning_rate,
                                 momentum=args.momentum)

_Trainer = Trainer(args=args,
                   model=net,
                   optimizer=optimizer
                   )
if args.do_test:
  _Trainer._valid_epoch()
else:
  _Trainer.train()

  #
