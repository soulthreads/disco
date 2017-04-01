import ctypes
import ctypes.util

uchar_ptr = ctypes.POINTER(ctypes.c_ubyte)
int16_ptr = ctypes.POINTER(ctypes.c_int16)
int_ptr = ctypes.POINTER(ctypes.c_int32)

class OpusEncoder(ctypes.Structure):
    pass

OpusEncoder_ptr = ctypes.POINTER(OpusEncoder)

_opus = ctypes.cdll.LoadLibrary(ctypes.util.find_library('opus'))

opus_strerror = _opus.opus_strerror
opus_strerror.argtypes = [ctypes.c_int]
opus_strerror.restype = ctypes.c_char_p

class OpusException(Exception):
    def __init__(self, ret):
        super().__init__(opus_strerror(ret).decode())

def errcheck(ret, func, args):
    if ret < 0:
        raise OpusException(ret)
    return ret

opus_encoder_create = _opus.opus_encoder_create
opus_encoder_create.argtypes = [ctypes.c_int32, ctypes.c_int, ctypes.c_int, int_ptr]
opus_encoder_create.restype = OpusEncoder_ptr

opus_encoder_destroy = _opus.opus_encoder_destroy
opus_encoder_destroy.argtypes = [OpusEncoder_ptr]

opus_encode = _opus.opus_encode
opus_encode.argtypes = [OpusEncoder_ptr, int16_ptr, ctypes.c_int, uchar_ptr, ctypes.c_int32]
opus_encode.restype = ctypes.c_int32
opus_encode.errcheck = errcheck

opus_encoder_ctl = _opus.opus_encoder_ctl
opus_encoder_ctl.restype = ctypes.c_int32
opus_encoder_ctl.errcheck = errcheck

OPUS_APPLICATION_VOIP = 2048
OPUS_APPLICATION_AUDIO = 2049
OPUS_APPLICATION_RESTRICTED_LOWDELAY = 2051
OPUS_SET_BITRATE_REQUEST = 4002
OPUS_SET_BANDWIDTH_REQUEST = 4008
OPUS_SET_INBAND_FEC_REQUEST = 4012
OPUS_SET_PACKET_LOSS_PERC_REQUEST = 4014
OPUS_SET_SIGNAL_REQUEST = 4024

OPUS_AUTO = -1000
OPUS_SIGNAL_VOICE = 3001
OPUS_SIGNAL_MUSIC = 3002

OPUS_BANDWIDTH_FULLBAND = 1105

class Encoder:
    def __init__(self):
        self.sampling_rate = 48000
        self.channels = 2
        self.frame_length = 20
        self.frame_size = int(self.sampling_rate * self.frame_length / 1000)
        self.frame_byte_length = self.frame_size * self.channels * ctypes.sizeof(ctypes.c_int16)
        self.bitrate = 128

        ret = ctypes.c_int()
        self.encoder = opus_encoder_create(
            self.sampling_rate,
            self.channels,
            OPUS_APPLICATION_AUDIO,
            ctypes.byref(ret)
        )
        if ret.value < 0:
            raise OpusException(ret)

        opus_encoder_ctl(
            self.encoder,
            OPUS_SET_BITRATE_REQUEST,
            self.bitrate * 1024
        )
        opus_encoder_ctl(
            self.encoder,
            OPUS_SET_BANDWIDTH_REQUEST,
            OPUS_BANDWIDTH_FULLBAND
        )
        opus_encoder_ctl(
            self.encoder,
            OPUS_SET_INBAND_FEC_REQUEST,
            1
        )
        opus_encoder_ctl(
            self.encoder,
            OPUS_SET_PACKET_LOSS_PERC_REQUEST,
            15
        )
        opus_encoder_ctl(
            self.encoder,
            OPUS_SET_SIGNAL_REQUEST,
            OPUS_SIGNAL_MUSIC
        )

    def __del__(self):
        if self.encoder is not None:
            opus_encoder_destroy(self.encoder)
            self.encoder = None

    def encode(self, pcm):
        max_data_bytes = len(pcm)
        data = (ctypes.c_ubyte * max_data_bytes)()
        size = opus_encode(
            self.encoder,
            ctypes.cast(pcm, int16_ptr),
            self.frame_size,
            data,
            max_data_bytes,
        )
        return data[:size]
