import tensorflow as tf
import glob
import cv2
import random
import numpy as np
import os
from time import time
import pickle
import sys

def recup(folder):
  X_train = pickle.load(open('./'+ folder + '/Xtrain.dump', 'rb'))
  X_test = pickle.load(open('./'+ folder + '/Xtest.dump', 'rb'))
  y_test = pickle.load(open('./'+ folder + '/Ytest.dump', 'rb'))
  y_train = pickle.load(open('./'+ folder + '/Ytrain.dump', 'rb'))
  return X_train, y_train, X_test, y_test

def new_weights_conv(name,shape):
    return tf.get_variable(name, shape=shape, dtype=tf.float32,
           initializer=tf.contrib.layers.xavier_initializer_conv2d())

def new_weights_fc(name,shape):
    return tf.get_variable(name, shape=shape, dtype=tf.float32,
           initializer=tf.contrib.layers.xavier_initializer())
       
def new_biases(length):
    return tf.Variable(tf.constant(0.05, shape=[length], dtype=tf.float32), dtype=tf.float32)

def new_conv_layer(name,input,              # The previous layer.
                   num_input_channels, # Num. channels in prev. layer.
                   filter_size,    # Width and height of each filter.
                   num_filters,    # Number of filters.
                   use_pooling=True): # Use 2x2 max-pooling.

    shape = [filter_size, filter_size, num_input_channels, num_filters]

    # Create new weights aka. filters with the given shape.
    weights = new_weights_conv(name,shape)

    # Create new biases, one for each filter.
    biases = new_biases(length=num_filters)
    layer = tf.nn.conv2d(input=input,
                         filter=weights,
                         strides=[1, 1, 1, 1],
                         padding='SAME')

    layer += biases

    # Use pooling to down-sample the image resolution?
    if use_pooling:
        layer = tf.nn.max_pool(value=layer,
                               ksize=[1, 2, 2, 1],
                               strides=[1, 2, 2, 1],
                               padding='SAME')
    layer = tf.nn.relu(layer)
    return layer, weights
  
def flatten_layer(layer):
    # Get the shape of the input layer.
    layer_shape = layer.get_shape()
    num_features = layer_shape[1:4].num_elements()
    layer_flat = tf.reshape(layer, [-1, num_features])
    return layer_flat, num_features


def new_fc_layer(name,input,          # The previous layer.
                 num_inputs,     # Num. inputs from prev. layer.
                 num_outputs, use_nonlinear):
    weights = new_weights_fc(name,[num_inputs, num_outputs])
    biases = new_biases(length=num_outputs)

    layer = tf.matmul(input, weights) + biases
    if use_nonlinear:
      layer = tf.nn.sigmoid(layer)

    return layer, weights


X_train, y_train, X_test, y_test = recup('dataTrain_box')
print(len(X_train), len(X_test))


print(X_train[0])
print('')
print(y_train[0])

input("recuperation done")
# Convolutional Layer 1.
filter_size1 = 5
num_filters1 = 32
num_filters2 = 64
num_filters3 = 128


n_classes = 4
batch_size = 256
imgSize = 64

x = tf.placeholder(tf.float32, [None, imgSize, imgSize])
x_image = tf.reshape(x, [-1, imgSize, imgSize, 1])
y = tf.placeholder(tf.float32)
keep_prob = tf.placeholder(tf.float32)

layer_conv1a, weights_conv1a = \
    new_conv_layer("conv1a",input=x_image,
                   num_input_channels=1,
                   filter_size=filter_size1,
                   num_filters=num_filters1,
                   use_pooling=False)

layer_conv1a1, weights_conv1a1 = \
    new_conv_layer("conv1a1",input=layer_conv1a,
                   num_input_channels=num_filters1,
                   filter_size=filter_size1,
                   num_filters=num_filters1,
                   use_pooling=True)

layer_conv1b, weights_conv1b = \
    new_conv_layer("conv1b",input=layer_conv1a1,
                   num_input_channels=num_filters1,
                   filter_size=filter_size1,
                   num_filters=num_filters1,
                   use_pooling=False)

layer_conv1b1, weights_conv1b1 = \
    new_conv_layer("conv1b1",input=layer_conv1b,
                   num_input_channels=num_filters1,
                   filter_size=filter_size1,
                   num_filters=num_filters1,
                   use_pooling=True)

layer_conv1c, weights_conv1c = \
    new_conv_layer("conv1c",input=layer_conv1b1,
                   num_input_channels=num_filters1,
                   filter_size=filter_size1,
                   num_filters=num_filters1,
                   use_pooling=False)

layer_conv1c1, weights_conv1c1 = \
    new_conv_layer("conv1c1",input=layer_conv1c,
                   num_input_channels=num_filters1,
                   filter_size=filter_size1,
                   num_filters=num_filters1,
                   use_pooling=True)

layer_flat, num_features = flatten_layer(layer_conv1c1)

layer_f, weights_f = new_fc_layer("fc",input=layer_flat,
                         num_inputs=num_features,
                         num_outputs=n_classes,
                         use_nonlinear=True)

y_pred = layer_f

print(layer_conv1a)
print(layer_flat)
print(layer_f)



rate = tf.placeholder(tf.float32, shape=[])
l_rate = 0.00005#5e-4
beta = 0.00
cost = tf.reduce_mean(tf.square(y_pred - y)) \
     + beta * (tf.nn.l2_loss(weights_f))

optimizer = tf.train.AdamOptimizer(rate).minimize(cost)

accuracy = tf.sqrt(tf.reduce_mean(tf.square(y_pred - y)))

saver = tf.train.Saver()
save_dir = 'final_model_box/'
if not os.path.exists(save_dir):
    os.makedirs(save_dir)
save_path = os.path.join(save_dir, 'best_model')

hm_epochs = 1500
t = time()
compteur = 0
prec = 10e100
with tf.Session() as sess:
  sess.run(tf.global_variables_initializer())
  saver.restore(sess=sess, save_path=save_path)
  res2 = accuracy.eval({x:X_train[:batch_size], y:y_train[:batch_size]})
  res3 = accuracy.eval({x:X_test[:batch_size], y:y_test[:batch_size]})
  epoch = 0
      
  while epoch < hm_epochs:
    epoch_loss = 0
    epoch += 1
    for g in range(0,len(X_train),batch_size):
      _, c = sess.run([optimizer, cost], feed_dict={keep_prob: 1, rate: l_rate, x: X_train[g:g+batch_size], y: y_train[g:g+batch_size]})
      
      sys.stdout.write('\r' + str(g) + '/' + str(len(X_train)))
      sys.stdout.flush()
      epoch_loss += c

    tempsEcoule = time() - t

    sys.stdout.write('\rEpoch : ' + str(epoch) + ' Loss : ' + str(epoch_loss) + ' Batch size : ' + str(batch_size) + ' LRate : ' + str(l_rate) + ' Time : ' + str(tempsEcoule))
    sys.stdout.write('\nTrain : ' + str(res2) + ' Test : ' + str(res3))
    sys.stdout.write('\n')
    t = time()
    if epoch_loss > prec:
      compteur += 1
    else:
      if compteur > 0:
        compteur -= 1
      prec = epoch_loss
      res2 = accuracy.eval({x:X_train[:batch_size], y:y_train[:batch_size]})
      res3 = accuracy.eval({x:X_test[:batch_size], y:y_test[:batch_size]})
      saver.save(sess=sess, save_path=save_path)
    if compteur >= 2:
      compteur = 0
      l_rate /= 1.5
      #batch_size = int(batch_size*1.5)

  res2, res = 0, 0
  for g in range(0,len(X_train),batch_size):
      res2 += accuracy.eval({x:X_train[g:g+batch_size], y:y_train[g:g+batch_size]})
  res2 /= (g/batch_size) + 1
  for g in range(0,len(X_test),batch_size):
      res += accuracy.eval({x:X_test[g:g+batch_size], y:y_test[g:g+batch_size]})
  res /= (g/batch_size) + 1
print('Epoch', epoch,'loss :',epoch_loss,'train :',res2,'test :', res)