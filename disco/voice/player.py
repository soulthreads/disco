import time
import subprocess
import gevent
from gevent.event import Event

from disco.util.logging import LoggingClass
from disco.voice.opus import Encoder

class StreamPlayer(LoggingClass):
    def __init__(self, vc, stream):
        super().__init__()
        self.vc = vc
        self.stream = stream
        self.encoder = Encoder()
        self.stop_event = Event()

    def run(self):
        self.vc.set_speaking(True)
        start = time.time()
        delta = 0
        while not self.stop_event.is_set():
            data = self.stream.read(self.encoder.frame_byte_length)
            if len(data) < self.encoder.frame_byte_length:
                self.stop_event.set()
                break

            self.vc.udp.send_encrypted(self.encoder.encode(data))
            self.vc.udp.sequence += 1
            self.vc.udp.timestamp += self.encoder.frame_size
            delta += self.encoder.frame_length
            gevent.sleep(start + delta / 1000 - time.time())
        self.vc.set_speaking(False)

    def stop(self):
        self.stop_event.set()

class ProcessPlayer(StreamPlayer):
    def __init__(self, vc, process):
        super().__init__(vc, process.stdout)
        self.process = process

    def run(self):
        super().run()
        self.process.communicate()

def open_ffmpeg_player(vc, filename):
    ffmpeg = subprocess.Popen(
        [
            'ffmpeg',
            '-i', filename,
            '-f', 's16le',
            '-ac', '2',
            '-ar', '48000',
            '-acodec', 'pcm_s16le',
            '-nostdin',
            '-loglevel', 'fatal',
            '-'
        ],
        stdout=subprocess.PIPE,
    )
    return ProcessPlayer(vc, ffmpeg)
