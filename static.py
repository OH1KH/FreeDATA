#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 11:13:57 2020

@author: DJ2LS
"""

# Operator Defaults
MYCALLSIGN = b'AA0AA'
MYCALLSIGN_CRC8 = b'A'

DXCALLSIGN = b'AA0AA'
DXCALLSIGN_CRC8 = b'A'

MYGRID = b''
#---------------------------------

# Server Defaults
HOST = "localhost"
PORT = 3000
#---------------------------------

# FreeDV Defaults
FREEDV_RECEIVE = True

FREEDV_DATA_MODE = 10
FREEDV_SIGNALLING_MODE = 14

FREEDV_DATA_BYTES_PER_FRAME = 0
FREEDV_DATA_PAYLOAD_PER_FRAME = 0
FREEDV_SIGNALLING_BYTES_PER_FRAME = 0
FREEDV_SIGNALLING_PAYLOAD_PER_FRAME = 0
#---------------------------------

#Audio Defaults
AUDIO_INPUT_DEVICE = 1
AUDIO_OUTPUT_DEVICE = 1
#TX_SAMPLE_STATE = None
#RX_SAMPLE_STATE = None

#AUDIO_SAMPLE_RATE_RX = 44100
#AUDIO_SAMPLE_RATE_TX = 44100
MODEM_SAMPLE_RATE = 8000 #8000
AUDIO_FRAMES_PER_BUFFER = 2048
AUDIO_CHANNELS = 1
#---------------------------------

#ARQ DEFAULTS
TX_N_MAX_RETRIES = 10
TX_N_RETRIES = 0

ARQ_TX_N_FRAMES_PER_BURST = 0
ARQ_TX_N_BURSTS = 0

ARQ_PAYLOAD_PER_FRAME = 0

ARQ_RX_BURST_BUFFER = []
ARQ_RX_FRAME_BUFFER = []
ARQ_RX_FRAME_N_BURSTS = 0

## TX
ARQ_TX_N_CURRENT_ARQ_FRAME = 0
ARQ_TX_N_TOTAL_ARQ_FRAMES = 0
##

## RX
ARQ_N_ARQ_FRAMES_PER_DATA_FRAME = 0 #total number of arq frames per data frame
ARQ_RX_N_CURRENT_ARQ_FRAME = 0
##

ARQ_N_RX_ARQ_FRAMES = 0 # total number of received frames
ARQ_N_RX_FRAMES_PER_BURSTS = 0 # NUMBER OF FRAMES WE ARE WAITING FOR --> GOT DATA FROM RECEIVED FRAME
ARQ_ACK_PAYLOAD_PER_FRAME = 0 # PAYLOAD per ACK frame

ARQ_ACK_RECEIVED = False # set to 1 if ACK received
ARQ_RX_ACK_TIMEOUT = False # set to 1 if timeut reached
ARQ_RX_ACK_TIMEOUT_SECONDS = 10.0 #timeout for waiting for ACK frames

ARQ_FRAME_ACK_RECEIVED = False # set to 1 if FRAME ACK received
ARQ_RX_FRAME_TIMEOUT = False
ARQ_RX_FRAME_TIMEOUT_SECONDS = 10.0


ARQ_RX_RPT_TIMEOUT = False
ARQ_RX_RPT_TIMEOUT_SECONDS = 10.0
ARQ_RPT_RECEIVED = False #indicate if RPT frame has been received
ARQ_RPT_FRAMES = [] #buffer for frames which are requested to repeat

FRAME_CRC = b''
FRAME_BOF = b'\xAA\xAA' #here we define 2 bytes for the BOF
FRAME_EOF = b'\xFF\xFF' #here we define 2 bytes for the EOF
ARQ_FRAME_BOF_RECEIVED = False # status, if we received a BOF of a data frame
ARQ_FRAME_EOF_RECEIVED = False # status, if we received a EOF of a data frame

ARQ_N_SENT_FRAMES = 0 #counter for already sent frames


# ARQ STATES:
# IDLE
# RECEIVING_DATA
# SENDING_DATA
# RECEIVING_SIGNALLING
# SENDING_ACK
# ACK_RECEIVED
#
#
#
ARQ_STATE = 'RECEIVING_DATA'

# ------- TX BUFFER
TX_BUFFER_SIZE = 0
TX_BUFFER = []
# ------- RX BUFFER
RX_BUFFER = []
RX_BUFFER_SIZE = 0

