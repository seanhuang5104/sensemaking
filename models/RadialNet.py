import tensorflow as tf
import numpy as np
import math
import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, '../utils'))
import tf_util
#from transform_Vector import input_transform_Vector, inputvectorFeature
#from Transform_RBF_Feature import input_rbfTransform,feature_transform_net,input_transform_net
from RBF_RadialNet import input_rbfTransform,input_transform_net
def placeholder_inputs(batch_size, num_point):
    pointclouds_pl = tf.placeholder(tf.float32, shape=(batch_size, num_point, 3))
    labels_pl = tf.placeholder(tf.int32, shape=(batch_size))
    return pointclouds_pl, labels_pl


def get_model(point_cloud, is_training, bn_decay=None):
    """ Classification PointNet, input is BxNx3, output Bx40 """
    batch_size = point_cloud.get_shape()[0].value
    num_point = point_cloud.get_shape()[1].value
    end_points = {}
#    input_image = tf.expand_dims(point_cloud, -1)
    
    with tf.variable_scope('transform_net') as sc:
        transform = input_transform_net(point_cloud, is_training, bn_decay, K=3)
#    end_points['transform'] = transform
    point_cloud_transformed = tf.matmul(point_cloud, transform)
    point_cloud_transformed = tf.expand_dims(point_cloud_transformed, -1)
    
    
    with tf.variable_scope('transform_inceptNet') as sc:
        net, featureTransform = input_rbfTransform(point_cloud_transformed, is_training, bn_decay)
    end_points['transform'] = featureTransform
   
    print ("fully net", net)
    net = tf_util.fully_connected(net, 512, bn=True, is_training=is_training,
                                  scope='fc1', bn_decay=bn_decay)
    
    net = tf_util.dropout(net, keep_prob=0.4, is_training=is_training,
                          scope='dp1')
    
    net = tf_util.fully_connected(net, 256, bn=True, is_training=is_training,
                                  scope='fc2', bn_decay=bn_decay)
    net = tf_util.dropout(net, keep_prob=0.4, is_training=is_training,
                          scope='dp1')
    print ("net", net)
    net = tf_util.fully_connected(net, 40, activation_fn=None, scope='fc3')

    return net, end_points



def get_loss(pred, label, end_points, reg_weight=0.002):
    """ pred: B*NUM_CLASSES,
        label: B, """
    loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=pred, labels=label)
    classify_loss = tf.reduce_mean(loss)
    tf.summary.scalar('classify loss', classify_loss)

    # Enforce the transformation as orthogonal matrix
    transform = end_points['transform'] # BxKxK
    K = transform.get_shape()[1].value
    mat_diff = tf.matmul(transform, tf.transpose(transform, perm=[0,2,1]))
    mat_diff -= tf.constant(np.eye(K), dtype=tf.float32)
    mat_diff_loss = tf.nn.l2_loss(mat_diff) 
    tf.summary.scalar('mat loss', mat_diff_loss)

    return classify_loss + mat_diff_loss * reg_weight


if __name__=='__main__':
    with tf.Graph().as_default():
        inputs = tf.zeros((32,1024,3))
        outputs = get_model(inputs, tf.constant(True))
        print(outputs)
