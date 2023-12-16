import numpy as np
import codec2
import ctypes
import structlog
import threading
import audio
import os
from modem_frametypes import FRAME_TYPE
import itertools

TESTMODE = False

class Demodulator():

    def __init__(self, config, audio_rx_q, modem_rx_q, data_q_rx, states, event_manager, fft_queue):
        self.tuning_range_fmin = config['MODEM']['tuning_range_fmin']
        self.tuning_range_fmax = config['MODEM']['tuning_range_fmax']
        self.enable_fsk = config['MODEM']['enable_fsk']
        self.rx_audio_level = config['AUDIO']['rx_audio_level']

        self.AUDIO_FRAMES_PER_BUFFER_RX = 2400 * 2  # 8192
        self.buffer_overflow_counter = [0, 0, 0, 0, 0, 0, 0, 0]
        self.is_codec2_traffic_counter = 0
        self.is_codec2_traffic_cooldown = 20

        # Receive only specific modes to reduce CPU load
        self.RECEIVE_SIGNALLING = True
        self.RECEIVE_DATAC1 = False
        self.RECEIVE_DATAC3 = False
        self.RECEIVE_DATAC4 = False

        self.RXCHANNEL = ""

        self.log = structlog.get_logger("Demodulator")

        self.audio_received_queue = audio_rx_q
        self.modem_received_queue = modem_rx_q
        self.data_queue_received = data_q_rx

        self.states = states
        self.event_manager = event_manager

        self.fft_queue = fft_queue

        # init codec2 resampler
        self.resampler = codec2.resampler()

        self.init_state_buffers()
        self.init_codec2()

    def init_state_buffers(self):
        # state buffer
        self.SIGNALLING_DATAC13_STATE = []
        self.SIG1_DATAC13_STATE = []
        self.DAT0_DATAC1_STATE = []
        self.DAT0_DATAC3_STATE = []
        self.DAT0_DATAC4_STATE = []

        self.FSK_LDPC0_STATE = []
        self.FSK_LDPC1_STATE = []

    def init_codec2(self):
        # Open codec2 instances

        # DATAC13
        # SIGNALLING MODE 0 - Used for Connecting - Payload 14 Bytes
        self.signalling_datac13_freedv, \
                self.signalling_datac13_bytes_per_frame, \
                self.signalling_datac13_bytes_out, \
                self.signalling_datac13_buffer, \
                self.signalling_datac13_nin = \
                self.init_codec2_mode(codec2.FREEDV_MODE.datac13.value, None)

        # DATAC1
        self.dat0_datac1_freedv, \
                self.dat0_datac1_bytes_per_frame, \
                self.dat0_datac1_bytes_out, \
                self.dat0_datac1_buffer, \
                self.dat0_datac1_nin = \
                self.init_codec2_mode(codec2.FREEDV_MODE.datac1.value, None)

        # DATAC3
        self.dat0_datac3_freedv, \
                self.dat0_datac3_bytes_per_frame, \
                self.dat0_datac3_bytes_out, \
                self.dat0_datac3_buffer, \
                self.dat0_datac3_nin = \
                self.init_codec2_mode(codec2.FREEDV_MODE.datac3.value, None)

        # DATAC4
        self.dat0_datac4_freedv, \
                self.dat0_datac4_bytes_per_frame, \
                self.dat0_datac4_bytes_out, \
                self.dat0_datac4_buffer, \
                self.dat0_datac4_nin = \
                self.init_codec2_mode(codec2.FREEDV_MODE.datac4.value, None)

    def init_codec2_mode(self, mode, adv):
        """
        Init codec2 and return some important parameters

        Args:
          self:
          mode:
          adv:

        Returns:
            c2instance, bytes_per_frame, bytes_out, audio_buffer, nin
        """

        # create codec2 instance
        c2instance = ctypes.cast(
            codec2.api.freedv_open(mode), ctypes.c_void_p
        )

        # set tuning range
        codec2.api.freedv_set_tuning_range(
            c2instance,
            ctypes.c_float(float(self.tuning_range_fmin)),
            ctypes.c_float(float(self.tuning_range_fmax)),
        )

        # get bytes per frame
        bytes_per_frame = int(
            codec2.api.freedv_get_bits_per_modem_frame(c2instance) / 8
        )

        # create byte out buffer
        bytes_out = ctypes.create_string_buffer(bytes_per_frame)

        # set initial frames per burst
        codec2.api.freedv_set_frames_per_burst(c2instance, 1)

        # init audio buffer
        audio_buffer = codec2.audio_buffer(2 * self.AUDIO_FRAMES_PER_BUFFER_RX)

        # get initial nin
        nin = codec2.api.freedv_nin(c2instance)

        # Additional Datac0-specific information - these are not referenced anywhere else.
        # self.signalling_datac0_payload_per_frame = self.signalling_datac0_bytes_per_frame - 2
        # self.signalling_datac0_n_nom_modem_samples = codec2.api.freedv_get_n_nom_modem_samples(
        #     self.signalling_datac0_freedv
        # )
        # self.signalling_datac0_n_tx_modem_samples = codec2.api.freedv_get_n_tx_modem_samples(
        #     self.signalling_datac0_freedv
        # )
        # self.signalling_datac0_n_tx_preamble_modem_samples = (
        #     codec2.api.freedv_get_n_tx_preamble_modem_samples(self.signalling_datac0_freedv)
        # )
        # self.signalling_datac0_n_tx_postamble_modem_samples = (
        #     codec2.api.freedv_get_n_tx_postamble_modem_samples(self.signalling_datac0_freedv)
        # )

        # return values
        return c2instance, bytes_per_frame, bytes_out, audio_buffer, nin

    def start(self, stream):

        self.stream = stream

        # Start decoder threads
        audio_thread_signalling_datac13 = threading.Thread(
            target=self.audio_signalling_datac13, name="AUDIO_THREAD DATAC13 - 0", daemon=True
        )
        audio_thread_signalling_datac13.start()

        audio_thread_dat0_datac1 = threading.Thread(
            target=self.audio_dat0_datac1, name="AUDIO_THREAD DATAC1", daemon=True
        )
        audio_thread_dat0_datac1.start()

        audio_thread_dat0_datac3 = threading.Thread(
            target=self.audio_dat0_datac3, name="AUDIO_THREAD DATAC3", daemon=True
        )
        audio_thread_dat0_datac3.start()

        audio_thread_dat0_datac4 = threading.Thread(
            target=self.audio_dat0_datac4, name="AUDIO_THREAD DATAC4", daemon=True
        )
        audio_thread_dat0_datac4.start()

    def audio_signalling_datac13(self) -> None:
        """Receive data encoded with datac13 - 0"""
        self.signalling_datac13_nin = self.demodulate_audio(
            self.signalling_datac13_buffer,
            self.signalling_datac13_nin,
            self.signalling_datac13_freedv,
            self.signalling_datac13_bytes_out,
            self.signalling_datac13_bytes_per_frame,
            self.SIGNALLING_DATAC13_STATE,
            "signalling-datac13"
        )

    def audio_dat0_datac4(self) -> None:
        """Receive data encoded with datac4"""
        self.dat0_datac4_nin = self.demodulate_audio(
            self.dat0_datac4_buffer,
            self.dat0_datac4_nin,
            self.dat0_datac4_freedv,
            self.dat0_datac4_bytes_out,
            self.dat0_datac4_bytes_per_frame,
            self.DAT0_DATAC4_STATE,
            "dat0-datac4"
        )

    def audio_dat0_datac1(self) -> None:
        """Receive data encoded with datac1"""
        self.dat0_datac1_nin = self.demodulate_audio(
            self.dat0_datac1_buffer,
            self.dat0_datac1_nin,
            self.dat0_datac1_freedv,
            self.dat0_datac1_bytes_out,
            self.dat0_datac1_bytes_per_frame,
            self.DAT0_DATAC1_STATE,
            "dat0-datac1"
        )

    def audio_dat0_datac3(self) -> None:
        """Receive data encoded with datac3"""
        self.dat0_datac3_nin = self.demodulate_audio(
            self.dat0_datac3_buffer,
            self.dat0_datac3_nin,
            self.dat0_datac3_freedv,
            self.dat0_datac3_bytes_out,
            self.dat0_datac3_bytes_per_frame,
            self.DAT0_DATAC3_STATE,
            "dat0-datac3"
        )

    def sd_input_audio_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
            audio_48k = np.frombuffer(indata, dtype=np.int16)
            audio_8k = self.resampler.resample48_to_8(audio_48k)
            audio.calculate_fft(audio_8k, self.fft_queue, self.states)

            audio_8k_level_adjusted = audio.set_audio_volume(audio_8k, self.rx_audio_level)

            length_audio_8k_level_adjusted = len(audio_8k_level_adjusted)
            # Avoid buffer overflow by filling only if buffer for
            # selected datachannel mode is not full
            for audiobuffer, receive, index in [
                (self.signalling_datac13_buffer, self.RECEIVE_SIGNALLING, 0),
                (self.dat0_datac1_buffer, self.RECEIVE_DATAC1, 2),
                (self.dat0_datac3_buffer, self.RECEIVE_DATAC3, 3),
                (self.dat0_datac4_buffer, self.RECEIVE_DATAC4, 4),
            ]:
                if (audiobuffer.nbuffer + length_audio_8k_level_adjusted) > audiobuffer.size:
                    self.buffer_overflow_counter[index] += 1
                    self.event_manager.send_buffer_overflow(self.buffer_overflow_counter)
                elif receive:
                    audiobuffer.push(audio_8k_level_adjusted)
            return audio_8k_level_adjusted

    def worker_received(self) -> None:
        """Worker for FIFO queue for processing received frames"""
        while True:
            data = self.modem_received_queue.get()
            self.log.debug("[MDM] worker_received: received data!")
            # data[0] = bytes_out
            # data[1] = freedv session
            # data[2] = bytes_per_frame
            # data[3] = snr

            item = {
                'payload': data[0],
                'freedv': data[1],
                'bytes_per_frame': data[2],
                'snr': data[3],
                'frequency_offset': self.get_frequency_offset(data[1]),
            }

            self.data_queue_received.put(item)
            self.modem_received_queue.task_done()

    def get_frequency_offset(self, freedv: ctypes.c_void_p) -> float:
        """
        Ask codec2 for the calculated (audio) frequency offset of the received signal.

        :param freedv: codec2 instance to query
        :type freedv: ctypes.c_void_p
        :return: Offset of audio frequency in Hz
        :rtype: float
        """
        modemStats = codec2.MODEMSTATS()
        codec2.api.freedv_get_modem_extended_stats(freedv, ctypes.byref(modemStats))
        offset = round(modemStats.foff) * (-1)
        return offset

    def demodulate_audio(
            self,
            audiobuffer: codec2.audio_buffer,
            nin: int,
            freedv: ctypes.c_void_p,
            bytes_out,
            bytes_per_frame,
            state_buffer,
            mode_name,
    ) -> int:
        """
        De-modulate supplied audio stream with supplied codec2 instance.
        Decoded audio is placed into `bytes_out`.

        :param audiobuffer: Incoming audio
        :type audiobuffer: codec2.audio_buffer
        :param nin: Number of frames codec2 is expecting
        :type nin: int
        :param freedv: codec2 instance
        :type freedv: ctypes.c_void_p
        :param bytes_out: Demodulated audio
        :type bytes_out: _type_
        :param bytes_per_frame: Number of bytes per frame
        :type bytes_per_frame: int
        :param state_buffer: modem states
        :type state_buffer: int
        :param mode_name: mode name
        :type mode_name: str
        :return: NIN from freedv instance
        :rtype: int
        """

        nbytes = 0
        #try:
        while self.stream.active:
            threading.Event().wait(0.01)
            while audiobuffer.nbuffer >= nin:
                # demodulate audio
                nbytes = codec2.api.freedv_rawdatarx(
                    freedv, bytes_out, audiobuffer.buffer.ctypes
                )
                # get current modem states and write to list
                # 1 trial
                # 2 sync
                # 3 trial sync
                # 6 decoded
                # 10 error decoding == NACK
                rx_status = codec2.api.freedv_get_rx_status(freedv)

                if rx_status not in [0]:
                    # we need to disable this if in testmode as its causing problems with FIFO it seems
                    if not TESTMODE:
                        self.states.set("is_codec2_traffic", True)
                        self.is_codec2_traffic_counter = self.is_codec2_traffic_cooldown
                        if not self.states.channel_busy:
                            self.log.debug("[MDM] Setting channel_busy since codec2 data detected")
                            self.states.set("channel_busy", True)
                            #self.channel_busy_delay += 10
                    self.log.debug(
                        "[MDM] [demod_audio] modem state", mode=mode_name, rx_status=rx_status,
                        sync_flag=codec2.api.rx_sync_flags_to_text[rx_status]
                    )
                else:
                    self.states.set("is_codec2_traffic", False)

                # decrement codec traffic counter for making state smoother
                if self.is_codec2_traffic_counter > 0:
                    self.is_codec2_traffic_counter -= 1
                    self.states.set("is_codec2_traffic", True)
                else:
                    self.states.set("is_codec2_traffic", False)

                if rx_status == 10:
                    state_buffer.append(rx_status)

                audiobuffer.pop(nin)
                nin = codec2.api.freedv_nin(freedv)
                if nbytes == bytes_per_frame:
                    print(bytes(bytes_out))

                    if int.from_bytes(bytes(bytes_out[:1]), "big") in [
                        FRAME_TYPE.MESH_BROADCAST.value,
                        FRAME_TYPE.MESH_SIGNALLING_PING.value,
                        FRAME_TYPE.MESH_SIGNALLING_PING_ACK.value,
                    ]:
                        self.log.debug(
                            "[MDM] [demod_audio] moving data to mesh dispatcher", nbytes=nbytes
                        )
                        MESH_RECEIVED_QUEUE.put([bytes(bytes_out), snr])

                    else:
                        self.log.debug(
                            "[MDM] [demod_audio] Pushing received data to received_queue", nbytes=nbytes
                        )
                        snr = self.calculate_snr(freedv)
                        self.modem_received_queue.put([bytes_out, freedv, bytes_per_frame, snr])
                        self.get_scatter(freedv)
                        state_buffer = []

        #except Exception as e:
        #    self.log.warning("[MDM] [demod_audio] Stream not active anymore", e=e)

        return nin

    def tci_rx_callback(self) -> None:
        """
        Callback for TCI RX

        data_in48k must be filled with 48000Hz audio raw data

        """

        while True:

            x = self.audio_received_queue.get()
            x = np.frombuffer(x, dtype=np.int16)
            # x = self.resampler.resample48_to_8(x)
            
            audio.calculate_fft(x, self.fft_queue, self.states)

            length_x = len(x)
            for data_buffer, receive in [
                (self.signalling_datac13_buffer, self.RECEIVE_SIGNALLING),
                (self.dat0_datac1_buffer, self.RECEIVE_DATAC1),
                (self.dat0_datac3_buffer, self.RECEIVE_DATAC3),
                (self.dat0_datac4_buffer, self.RECEIVE_DATAC4),
            ]:
                if (
                        not (data_buffer.nbuffer + length_x) > data_buffer.size
                        and receive
                ):
                    data_buffer.push(x)

    def set_frames_per_burst(self, frames_per_burst: int) -> None:
        """
        Configure codec2 to send the configured number of frames per burst.

        :param frames_per_burst: Number of frames per burst requested
        :type frames_per_burst: int
        """
        # Limit frames per burst to acceptable values
        frames_per_burst = min(frames_per_burst, 1)
        frames_per_burst = max(frames_per_burst, 5)

        frames_per_burst = 1

        codec2.api.freedv_set_frames_per_burst(self.dat0_datac1_freedv, frames_per_burst)
        codec2.api.freedv_set_frames_per_burst(self.dat0_datac3_freedv, frames_per_burst)
        codec2.api.freedv_set_frames_per_burst(self.dat0_datac4_freedv, frames_per_burst)

    def calculate_snr(self, freedv: ctypes.c_void_p) -> float:
        """
        Ask codec2 for data about the received signal and calculate
        the signal-to-noise ratio.

        :param freedv: codec2 instance to query
        :type freedv: ctypes.c_void_p
        :return: Signal-to-noise ratio of the decoded data
        :rtype: float
        """
        try:
            modem_stats_snr = ctypes.c_float()
            modem_stats_sync = ctypes.c_int()

            codec2.api.freedv_get_modem_stats(
                freedv, ctypes.byref(modem_stats_sync), ctypes.byref(modem_stats_snr)
            )
            modem_stats_snr = modem_stats_snr.value
            modem_stats_sync = modem_stats_sync.value

            snr = round(modem_stats_snr, 1)
            self.log.info("[MDM] calculate_snr: ", snr=snr)
            # snr = np.clip(
            #    snr, -127, 127
            # )  # limit to max value of -128/128 as a possible fix of #188
            return int(snr)
        except Exception as err:
            self.log.error(f"[MDM] calculate_snr: Exception: {err}")
            return 0

    def get_scatter(self, freedv: ctypes.c_void_p) -> None:
        """
        Ask codec2 for data about the received signal and calculate the scatter plot.

        :param freedv: codec2 instance to query
        :type freedv: ctypes.c_void_p
        """
       
        modemStats = codec2.MODEMSTATS()
        ctypes.cast(
            codec2.api.freedv_get_modem_extended_stats(freedv, ctypes.byref(modemStats)),
            ctypes.c_void_p,
        )

        scatterdata = []
        # original function before itertool
        # for i in range(codec2.MODEM_STATS_NC_MAX):
        #    for j in range(1, codec2.MODEM_STATS_NR_MAX, 2):
        #        # print(f"{modemStats.rx_symbols[i][j]} - {modemStats.rx_symbols[i][j]}")
        #        xsymbols = round(modemStats.rx_symbols[i][j - 1] // 1000)
        #        ysymbols = round(modemStats.rx_symbols[i][j] // 1000)
        #        if xsymbols != 0.0 and ysymbols != 0.0:
        #            scatterdata.append({"x": str(xsymbols), "y": str(ysymbols)})

        for i, j in itertools.product(range(codec2.MODEM_STATS_NC_MAX), range(1, codec2.MODEM_STATS_NR_MAX, 2)):
            # print(f"{modemStats.rx_symbols[i][j]} - {modemStats.rx_symbols[i][j]}")
            xsymbols = round(modemStats.rx_symbols[i][j - 1] // 1000)
            ysymbols = round(modemStats.rx_symbols[i][j] // 1000)
            if xsymbols != 0.0 and ysymbols != 0.0:
                scatterdata.append({"x": str(xsymbols), "y": str(ysymbols)})

        # Send all the data if we have too-few samples, otherwise send a sampling
        if 150 > len(scatterdata) > 0:
            self.event_manager.send_scatter_change(scatterdata)

        else:
            # only take every tenth data point
            self.event_manager.send_scatter_change(scatterdata[::10])

    def reset_data_sync(self) -> None:
        """
        reset sync state for data modes

        :param frames_per_burst: Number of frames per burst requested
        :type frames_per_burst: int
        """

        codec2.api.freedv_set_sync(self.dat0_datac1_freedv, 0)
        codec2.api.freedv_set_sync(self.dat0_datac3_freedv, 0)
        codec2.api.freedv_set_sync(self.dat0_datac4_freedv, 0)
