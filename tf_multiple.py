import logging
import datetime

import numpy as np
import pandas as pd

import tensorflow as tf
import tensorflow.contrib.rnn as rnn

import sklearn.preprocessing as pp

import functools

# initialize and configure logging
logger = logging.getLogger('tf_multiple')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('tf_multiple.log')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

# prevent tensorflow from allocating the entire GPU memory at once
#config = tf.ConfigProto()
#config.gpu_options.allow_growth = True
#sess = tf.Session(config=config)

def lazy_property(function):
    attribute = '_' + function.__name__

    @property
    @functools.wraps(function)
    def wrapper(self):
        if not hasattr(self, attribute):
            setattr(self, attribute, function(self))
        return getattr(self, attribute)
    return wrapper

class Config_LSTM_1:

    def __init__(self):

        self.batch_size = 64
        self.seq_len = 20
        self.learning_rate = 0.001
        self.state_size = 128
        self.num_layers = 2
        self.num_epochs = 15
        self.dropout_train = 0.25
        self.dropout_eval = 1

class LSTM_Model_1:

    def __init__(self, config):

        self.config = config
        self.add_placeholders()
        #self.get_input_placeholder
        #self.get_dropout_placeholder
        last_output = self.add_LSTM_layer()
        last_output = last_output[:, last_output.shape[1] - 1, :]
        last_output = self.add_dense_layer(last_output, self.config.state_size, 1)
        self.model = last_output
        self.optimize

    def add_placeholders(self):

        with tf.variable_scope("lstm_placeholders_model_1"):

            self.input_placeholder = tf.placeholder(tf.float32, [None, self.config.seq_len, 1], "input")
            self.dropout_placeholder = tf.placeholder(tf.float32, None, "dropout")
            self.target_placeholder = tf.placeholder(tf.float32, [None, 1, 1], "target")

    def add_LSTM_layer(self):

        with tf.variable_scope("lstm_layer_model_1"):

            # The following is replaced by the generator pattern cf. https://github.com/tensorflow/tensorflow/issues/8191            
            #onecell = rnn.GRUCell(self.config.state_size)
            #onecell = tf.contrib.rnn.DropoutWrapper(onecell, output_keep_prob=self.dropout_placeholder)            
            #multicell = tf.contrib.rnn.MultiRNNCell([onecell] * self.config.num_layers, state_is_tuple=False)

            multicell = rnn.MultiRNNCell([rnn.DropoutWrapper(rnn.GRUCell(self.config.state_size), output_keep_prob=self.dropout_placeholder) for _ in range(self.config.num_layers)], state_is_tuple=False)

            outputs, _ = tf.nn.dynamic_rnn(multicell, self.input_placeholder, dtype=tf.float32)
            return outputs
        
    def add_dense_layer(self, _input, hidden_size, out_size):

        weight = tf.Variable(tf.truncated_normal([hidden_size, out_size], stddev=0.01))
        bias = tf.Variable(tf.constant(0.1, shape=[out_size]))
        return tf.matmul(_input, weight) + bias

    @lazy_property
    def cost(self):
        """Add loss function
        """
        mse = tf.reduce_mean(tf.pow(tf.subtract(self.model, self.target_placeholder), 2.0))
        return mse

    @lazy_property
    def optimize(self):
        """Sets up the training Ops.
        """
        optimizer = tf.train.RMSPropOptimizer(self.config.learning_rate)
        return optimizer.minimize(self.cost)

    def batch_train_generator(self, X, y, location):
        """Consecutive mini
        batch generator
        """
        for i in range(len(X) // self.config.batch_size):
            batch_X = X[i:i+self.config.batch_size, location, :].reshape(self.config.batch_size, self.config.seq_len, 1)
            batch_y = y[i:i+self.config.batch_size, location].reshape(self.config.batch_size, 1, 1)
            yield batch_X, batch_y

    def train(self, X, y):

        sess = tf.Session()
        sess.run(tf.global_variables_initializer())

        for epoch in range(self.config.num_epochs):
            # mini batch generator for training
            gen_train = self.batch_train_generator(X, y, 0)

            for batch in range(len(X) // self.config.batch_size):
                logger.debug("Optimizing (epoch, batch) = ({0}, {1})".format(epoch, batch));
                batch_X, batch_y = next(gen_train);
                _ = sess.run(self.optimize, feed_dict={
                        self.input_placeholder: batch_X,
                        self.target_placeholder: batch_y,
                        self.dropout_placeholder: self.config.dropout_train
                })

            train_error = sess.run(self.cost, feed_dict={
                    self.input_placeholder: X[:, 0, :],
                    self.target_placeholder: y[:, 0],
                    self.dropout_placeholder: self.config.dropout_eval
            })

            logger.info("Epoch: %d, train error: %f", epoch, train_error)
           


    def predict(self, X):

        sess = tf.Session()
        sess.run(tf.global_variables_initializer())

        return sess.run(self.model, feed_dict={
                self.input_placeholder: X[:, 0, :],
                #self.target_placeholder: y[:, 0],
                self.dropout_placeholder: self.config.dropout_eval
        })
        



def main():    
    logger.info("Using TensorFlow " + tf.VERSION)

    logger.info("Loading data ...")
    data = pd.read_csv('data/4A_201701_Consistent.csv', sep=';')
    # Initial data-slicing
    data = data[(data.LinkTravelTime > 0) & (data.LineDirectionCode == 1)]
    data = data[(26 <= data.LineDirectionLinkOrder) & (data.LineDirectionLinkOrder <= 32)]
    data['DateTime'] = pd.to_datetime(data['DateTime'])
    data.set_index(pd.DatetimeIndex(data['DateTime']), inplace = True)

    logger.info("Transforming data ...")
    # Create and 2d matrix of traveltime with (x, y) = (space, time) = (linkRef, journeyRef)
    ts = data.pivot(index='JourneyRef', columns='LinkRef', values='LinkTravelTime')
    ts = ts[~np.isnan(ts).any(axis=1)]
    
    # TODO: Refactor 
    i = int(len(ts) * 0.8)
    n_test = len(ts) - i

    train = ts[0:i]
    test = ts[i:i + n_test]
       
    scaler = pp.RobustScaler(with_centering = True, quantile_range = (5, 95))
    train_norm = scaler.fit_transform(train)
    test_norm = scaler.transform(test)

    # Create lags travel time
    X_train_norm = np.stack([np.roll(train_norm, i) for i in range(20, 0, -1)], axis = -1)
    X_train_norm = X_train_norm[20:, ...]
    y_train_norm = train_norm[20:, ...]

    # Create lags travel time
    X_test_norm = np.stack([np.roll(test_norm, i) for i in range(20, 0, -1)], axis = -1)
    X_test_norm = X_test_norm[20:, ...]
    y_test_norm = test_norm[20:, ...]

    logger.info("Train size (X, y) = (" + str(X_train_norm.shape) + ", " + str(y_train_norm.shape) + ")")
    logger.info("Test size (X, y) = (" + str(X_test_norm.shape) + ", " + str(y_test_norm.shape) + ")")

    logger.info("Initializing model graph ...")
    tf.reset_default_graph()
    config_lstm_1 = Config_LSTM_1()
    model_1 = LSTM_Model_1(config_lstm_1)

    logger.info("Running training epochs ...")
    model_1.train(X_train_norm, y_train_norm)

    logger.info("Running test evaluation ...")
    preds_norm = model_1.predict(X_test_norm)
    preds = scaler.inverse_transform(preds)
    


if __name__ == "__main__": main()