from base.base_trainer import BaseTrainer
import tensorflow as tf
from evaluator.voceval import EvaluatorVOC
from tensorflow.python.keras import metrics
from yolo.yolo_loss import loss_yolo
import time

class Trainer(BaseTrainer):
  def __init__(self, args, model, optimizer):
    super().__init__(args, model, optimizer)

  def _get_loggers(self):
    self.TESTevaluator = EvaluatorVOC(anchors=self.anchors,
                                       inputsize=(self.net_size,
                                                  self.net_size),
                                       cateNames=self.labels,
                                       rootpath=self.dataset_root,
                                       score_thres=0.01,
                                       iou_thres=0.5,
                                      use_07_metric=False
                                      )

    self.LossBox = metrics.Mean()
    self.LossConf = metrics.Mean()
    self.LossClass = metrics.Mean()
    self.logger_losses = {}
    self.logger_losses.update({"lossBox": self.LossBox})
    self.logger_losses.update({"lossConf": self.LossConf})
    self.logger_losses.update({"lossClass": self.LossClass})
    self.logger_voc = ['AP@{}'.format(cls) for cls in self.labels] + ['mAP']

  def _reset_loggers(self):
    self.TESTevaluator.reset()
    self.LossClass.reset_states()
    self.LossConf.reset_states()
    self.LossBox.reset_states()

  @tf.function
  def train_step(self, imgs, labels):
    with tf.GradientTape() as tape:
      outputs = self.model(imgs, training=True)
      inputshape=tf.shape(imgs)[1:3]
      loss_box, loss_conf, loss_class = loss_yolo(outputs, labels, anchors=self.anchors,
                                                  inputshape=inputshape,
                                                  num_classes=self.num_classes)
      loss = tf.reduce_sum(loss_box + loss_conf + loss_class)
    grads = tape.gradient(loss, self.model.trainable_variables)
    self.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))
    self.LossBox.update_state(loss_box)
    self.LossConf.update_state(loss_conf)
    self.LossClass.update_state(loss_class)
    return outputs

  def _valid_epoch(self):
    for idx_batch, inputs in enumerate(self.test_dataloader):
      # if idx_batch ==5:
      #   break
      inputs = [tf.squeeze(input, axis=0) for input in inputs]
      (imgs, imgpath, annpath, scale, ori_shapes, *_)=inputs
      if idx_batch == self.args.valid_batch and not self.args.do_test:  # to save time
        break
      grids = self.model(imgs, training=False)
      self.TESTevaluator.append(grids, imgpath, annpath, scale, ori_shapes)
    results = self.TESTevaluator.evaluate()
    imgs = self.TESTevaluator.visual_imgs
    return results, imgs

  def _train_epoch(self):
    for i, inputs in enumerate(self.train_dataloader):
      inputs = [tf.squeeze(input, axis=0) for input in inputs]
      img, _, _, _, _, *labels=inputs
      self.global_iter.assign_add(1)
      if self.global_iter.numpy() % 1 == 0:
        print(self.global_iter.numpy())
        for k, v in self.logger_losses.items():
          print(k, ":", v.result().numpy())
      _ = self.train_step(img, labels)

      if self.global_iter.numpy() % self.log_iter == 0:
        results, imgs = self._valid_epoch()

        with self.trainwriter.as_default():
          for k, v in zip(self.logger_voc, results):
            tf.summary.scalar(k, v, step=self.global_iter.numpy())
          for k, v in self.logger_losses.items():
            tf.summary.scalar(k, v.result(), step=self.global_iter.numpy())
          for i in range(len(imgs)):
            tf.summary.image("detections_{}".format(i), tf.expand_dims(tf.convert_to_tensor(imgs[i]), 0),
                             step=self.global_iter.numpy())
        self._reset_loggers()
    self.ckpt_manager.save(self.global_epoch)
