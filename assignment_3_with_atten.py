# -*- coding: utf-8 -*-
"""assignment-3 with atten.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JYZFpkPKAwYAH6ARd3z3bWB-TkUy9ENS
"""

# from google.colab import drive
# drive.mount('/content/drive/')

# !pip install wandb --upgrade

import os
import pandas as pd
import cv2
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import pathlib
from tensorflow.keras import layers
from tensorflow.keras.layers import Dense, Input, InputLayer, Flatten, Activation, LSTM, SimpleRNN, GRU, TimeDistributed, Concatenate,dot,BatchNormalization,concatenate
from tensorflow.keras.utils import plot_model
from tensorflow.keras.models import load_model, Sequential,  Model
from tensorflow.keras.callbacks import EarlyStopping
import wandb

def dictLookup(vocab):
    char2int = dict([(char, i) for i, char in enumerate(vocab)])
    int2char = dict((i, char) for char, i in char2int.items())
    return char2int, int2char


def encode(source, target, sourceChar, targetChar, source_char2int=None, target_char2int=None):
    numEncoderTokens = len(sourceChar)
    numDecoderTokens = len(targetChar)
    maxSourceLength = max([len(txt) for txt in source])
    max_target_length = max([len(txt) for txt in target])

    sourceVocab, targetVocab = None, None
    if source_char2int == None and target_char2int == None:
        print("Generating the dictionary lookups for character to integer mapping and back")
        source_char2int, source_int2char = dictLookup(sourceChar)
        target_char2int, target_int2char = dictLookup(targetChar)

        sourceVocab = (source_char2int, source_int2char)
        targetVocab = (target_char2int, target_int2char)

    encoderInputData = np.zeros(
        (len(source), maxSourceLength, numEncoderTokens), dtype="float32"
    )
    decoderIData = np.zeros(
        (len(source), max_target_length, numDecoderTokens), dtype="float32"
    )
    decoderTData = np.zeros(
        (len(source), max_target_length, numDecoderTokens), dtype="float32"
    )

    for i, (input_text, target_text) in enumerate(zip(source, target)):
        for t, char in enumerate(input_text):
            encoderInputData[i, t, source_char2int[char]] = 1.0
        encoderInputData[i, t + 1 :, source_char2int[" "]] = 1.0
        for t, char in enumerate(target_text):
            # decoderTData is ahead of decoderIData by one timestep
            decoderIData[i, t, target_char2int[char]] = 1.0
            if t > 0:
                # decoderTData will be ahead by one timestep
                # and will not include the start character.
                decoderTData[i, t - 1, target_char2int[char]] = 1.0
        decoderIData[i, t + 1 :, target_char2int[" "]] = 1.0
        decoderTData[i, t:, target_char2int[" "]] = 1.0
    if sourceVocab != None and targetVocab != None:
        return (
            encoderInputData,
            decoderIData,
            decoderTData,
            sourceVocab,
            targetVocab,
        )
    else:
        return encoderInputData, decoderIData, decoderTData

def pre(source , target):
    sourceChar = set()
    targetChar = set()

    source = [str(x) for x in source]
    target = [str(x) for x in target]

    sourceWord = []
    targetWord = []
    for src, tgt in zip(source, target):
        tgt = "\t" + tgt + "\n"
        sourceWord.append(src)
        targetWord.append(tgt)
        for char in src:
            if char not in sourceChar:
                sourceChar.add(char)
        for char in tgt:
            if char not in targetChar:
                targetChar.add(char)

    sourceChar = sorted(list(sourceChar))
    targetChar = sorted(list(targetChar))

    #The space needs to be appended so that the encode function doesn't throw errors
    sourceChar.append(" ")
    targetChar.append(" ")

    numEncoderTokens = len(sourceChar)
    numDecoderTokens = len(targetChar)
    maxSourceLength = max([len(txt) for txt in sourceWord])
    max_target_length = max([len(txt) for txt in targetWord])

    print("Number of samples:", len(source))
    print("Source Vocab length:", numEncoderTokens)
    print("Target Vocab length:", numDecoderTokens)
    print("Max sequence length for inputs:", maxSourceLength)
    print("Max sequence length for outputs:", max_target_length)

    return encode(sourceWord, targetWord, sourceChar, targetChar)

def DataProcessing(DATAPATH,source_lang = 'en', target_lang = "ta"):


    
    train_path = os.path.join(DATAPATH, target_lang, "lexicons", target_lang+".translit.sampled.train.tsv")
    val_path = os.path.join(DATAPATH, target_lang, "lexicons", target_lang+".translit.sampled.dev.tsv")
    test_path = os.path.join(DATAPATH, target_lang, "lexicons", target_lang+".translit.sampled.test.tsv")
    train = pd.read_csv(
        train_path,
        sep="\t",
        names=["tgt", "src", "count"],
    )
    val = pd.read_csv(
        val_path,
        sep="\t",
        names=["tgt", "src", "count"],
    )
    test = pd.read_csv(
        test_path,
        sep="\t",
        names=["tgt", "src", "count"],
    )

    # create train data
    train_data = pre(train["src"].to_list(), train["tgt"].to_list())
    (
        trainEncoderInput,
        trainDecoderInput,
        trainDecoderTarget,
        sourceVocab,
        targetVocab,
    ) = train_data
    source_char2int, source_int2char = sourceVocab
    target_char2int, target_int2char = targetVocab

    # create val data (only encode function suffices as the dictionary lookup should be kep the same.
    valData = encode(
        val["src"].to_list(),
        val["tgt"].to_list(),
        list(source_char2int.keys()),
        list(target_char2int.keys()),
        source_char2int=source_char2int,
        target_char2int=target_char2int,
    )
    valEncoderInput, valDecoderInput, valDecoderTarget = valData
    source_char2int, source_int2char = sourceVocab
    target_char2int, target_int2char = targetVocab

    # create test data
    testData = encode(
        test["src"].to_list(),
        test["tgt"].to_list(),
        list(source_char2int.keys()),
        list(target_char2int.keys()),
        source_char2int=source_char2int,
        target_char2int=target_char2int,
    )
    testEncoderInput, testDecoderInput, testDecoderTarget = testData
    source_char2int, source_int2char = sourceVocab
    target_char2int, target_int2char = targetVocab
    return source_lang,target_lang,source_char2int,target_char2int,trainEncoderInput, trainDecoderInput, trainDecoderTarget,valEncoderInput, valDecoderInput, valDecoderTarget,train_data,valData



def build_attention_model(cell_type,srcChar2Int,numEncoders,latentDim,dropout,tgtChar2Int,numDecoders,hidden):
        
  # encoder
  print("encoder")
  encoderInput = Input(shape=(None, len(srcChar2Int)))
  encoderOutput = encoderInput
  for i in range(1, numEncoders + 1):
    if cell_type == "RNN":
      encoder = SimpleRNN(
          latentDim,
          return_state=True,
          return_sequences=True,
          dropout=dropout,
      )
    elif cell_type == 'LSTM':
      encoder = LSTM(
            latentDim,
            return_state=True,
            return_sequences=True,
            dropout=dropout,
        )
    elif cell_type == 'GRU':
      encoder = GRU(
            latentDim,
            return_state=True,
            return_sequences=True,
            dropout=dropout,
        )

    encoderOutput, state = encoder(encoderInput) 
        
    if i == 1:
        encoder_first_outputs= encoderOutput                  
    encoderState = [state]
    print("decoder")

    # decoder
    decoderInput = Input(shape=(None, len(tgtChar2Int)))
    print("decoderOutput")
    decoderOutput = decoderInput
    for i in range(1, numDecoders + 1):
      if cell_type == "RNN":
        decoder = SimpleRNN(
            latentDim,
            return_state=True,
            return_sequences=True,
            dropout=dropout,
        )
      elif cell_type == 'LSTM':
        decoder = LSTM(
              latentDim,
              return_state=True,
              return_sequences=True,
              dropout=dropout,
          )
      elif cell_type == 'GRU':
        decoder = GRU(
              latentDim,
              return_state=True,
              return_sequences=True,
              dropout=dropout,
          )
    decoderOutput, _ = decoder(decoderInput, initial_state=encoderState)
        
    if i == numDecoders:
        decoder_first_outputs = decoderOutput
    
    print("attention_layer",decoderOutput,encoderOutput)
    attention= BahdanauAttention(latentDim, verbose=1)
    # attention_layer = AttentionLayer(units=128)
    # attention_out, attention_states = attention_layer([encoder_first_outputs, decoder_first_outputs],hidden=hidden)
    attention_out, attention_states = attention(decoderOutput, encoderOutput)

    decoderConcatOutput = Concatenate(axis=-1, name='concat_layer')([decoderOutput, attention_out])

    # dense
    hidden = Dense(hidden, activation="relu")
    hidden_time = TimeDistributed(hidden, name='time_distributed_layer')
    hiddenOutput = hidden(decoderConcatOutput)
    decoderDense = Dense(len(tgtChar2Int), activation="softmax")
    decoderOutput = decoderDense(hiddenOutput)
    model = Model([encoderInput, decoderInput], decoderOutput)
    
    return model,encoderOutput,decoderOutput


def train():

    config_defaults = {
        "cell_type": "LSTM",
        "latentDim": 256,
        "hidden": 128,
        "optimiser": "rmsprop",
        "numEncoders": 1,
        "numDecoders": 1,
        "dropout": 0.2,
        "epochs": 1,
        "batch_size": 64,
    }


    wandb.init(config=config_defaults, project="cs6910_assignment3", entity="cs6910_assignment")
    config = wandb.config
    wandb.run.name = (
        str(config.cell_type)
        + source_lang
        + str(config.numEncoders)
        + "_"
        + target_lang
        + "_"
        + str(config.numDecoders)
        + "_"
        + config.optimiser
        + "_"
        + str(config.epochs)
        + "_"
        + str(config.dropout) 
        + "_"
        + str(config.batch_size)
        + "_"
        + str(config.latentDim)
    )
    wandb.run.save()

    # modelInit = S2STranslation(config,srcChar2Int=dataBase.source_char2int, tgtChar2Int=dataBase.target_char2int)

    numEncoders = config["numEncoders"]
    cell_type = config["cell_type"]
    latentDim = config["latentDim"]
    dropout = config["dropout"]
    numDecoders = config["numDecoders"]
    hidden = config["hidden"]
    tgtChar2Int = target_char2int
    srcChar2Int = source_char2int

    model,encoderOutput,decoderOutput = build_attention_model(cell_type,srcChar2Int,numEncoders,latentDim,dropout,tgtChar2Int,numDecoders,hidden)
    
    model.summary()
    model.compile(
        optimizer=config.optimiser,
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    earlystopping = EarlyStopping(
        monitor="val_loss", min_delta=0.5, patience=2, verbose=2, mode="auto"
    )
    
    model.fit(
        [trainEncoderInput, trainDecoderInput],
        trainDecoderTarget,
        batch_size=config.batch_size,
        epochs=config.epochs,
        callbacks=[earlystopping, WandbCallback()],
    )

    model.save(os.path.join("./TrainedModelsAttention", wandb.run.name))    
    wandb.finish()
    
    #return model

class BahdanauAttention(tf.keras.layers.Layer):
  def __init__(self, units, verbose=0):
    super(BahdanauAttention, self).__init__()
    self.W1 = tf.keras.layers.Dense(units)
    self.W2 = tf.keras.layers.Dense(units)
    self.V = tf.keras.layers.Dense(1)
    self.verbose= verbose

  def call(self, query, values):
    if query.shape != values.shape:
      query = values
    if self.verbose:
      print('\n******* Bahdanau Attention STARTS******')
      print('query (decoder hidden state): (batch_size, hidden size) ', query.shape)
      print('values (encoder all hidden state): (batch_size, max_len, hidden size) ', values.shape)

    # query hidden state shape == (batch_size, hidden size)
    # query_with_time_axis shape == (batch_size, 1, hidden size)
    # values shape == (batch_size, max_len, hidden size)
    # we are doing this to broadcast addition along the time axis to calculate the score
    query_with_time_axis = tf.expand_dims(query, 1)
    
    if self.verbose:
      print('query_with_time_axis:(batch_size, 1, hidden size) ', query_with_time_axis.shape)

    # score shape == (batch_size, max_length, 1)
    # we get 1 at the last axis because we are applying score to self.V
    # the shape of the tensor before applying self.V is (batch_size, max_length, units)
    score = self.V(tf.nn.tanh(
        self.W1(query_with_time_axis) + self.W2(values)))
    if self.verbose:
      print('score: (batch_size, max_length, 1) ',score.shape)
    # attention_weights shape == (batch_size, max_length, 1)
    attention_weights = tf.nn.softmax(score, axis=1)
    if self.verbose:
      print('attention_weights: (batch_size, max_length, 1) ',attention_weights.shape)
    # context_vector shape after sum == (batch_size, hidden_size)
    context_vector = attention_weights * values
    if self.verbose:
      print('context_vector before reduce_sum: (batch_size, max_length, hidden_size) ',context_vector.shape)
    context_vector = tf.reduce_sum(context_vector, axis=1)
    if self.verbose:
      print('context_vector after reduce_sum: (batch_size, hidden_size) ',context_vector.shape)
      print('\n******* Bahdanau Attention ENDS******')
    return context_vector, attention_weights



from tensorflow.keras import Input, Model
from wandb.keras import WandbCallback
from tensorflow.keras.preprocessing.text import Tokenizer

physical_devices = tf.config.list_physical_devices('GPU')
try:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
except:
#Invalid device or cannot modify virtual devices once initialized.
    pass
path = os.path.dirname(os.getcwd())
DATAPATH = path +'/dakshina_dataset_v1.0'
source_lang,target_lang,source_char2int,target_char2int,trainEncoderInput, trainDecoderInput, trainDecoderTarget,valEncoderInput, valDecoderInput, valDecoderTarget,train_data,val_data = DataProcessing(DATAPATH)
# train()



sweep_config = {
    "name": "Bayesian Sweep with attention",
    "method": "bayes",
    "metric": {"name": "val_accuracy", "goal": "maximize"},
    "parameters": {
        
        "cell_type": {"values": ["RNN", "GRU", "LSTM"]},
        
        "latentDim": {"values": [256, 128, 64, 32]},
        
        "hidden": {"values": [128, 64, 32, 16]},
        
        "optimiser": {"values": ["rmsprop", "adam"]},
        
        "numEncoders": {"values": [1, 2, 3]},
        
        "numDecoders": {"values": [1, 2, 3]},
        
        "dropout": {"values": [0.1, 0.2, 0.3]},
        
        "epochs": {"values": [5,10,15, 20]},
        
        "batch_size": {"values": [32, 64]},
    },
}



sweep_id = wandb.sweep(sweep_config, project="cs6910_assignment3", entity="cs6910_assignment")

wandb.agent(sweep_id, train, count = 100)

