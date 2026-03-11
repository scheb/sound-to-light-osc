from pythonosc import udp_client
from pythonosc.udp_client import SimpleUDPClient


class OscClient:
    osc_client: SimpleUDPClient

    def __init__(self, server, port) -> None:
        self.osc_client = udp_client.SimpleUDPClient(server, port)

    def send_prog_signal(self, program):
        # print("send program signal")
        self.osc_client.send_message("/prog{:d}".format(program), 1.0)

    def send_beat_signal(self):
        # print("send beat signal")
        self.osc_client.send_message("/beat", 1.0)
        self.osc_client.send_message("/beat", 0.0)

    def send_bar_signal(self):
        # print("send bar signal")
        self.osc_client.send_message("/bar", 1.0)
        self.osc_client.send_message("/bar", 0.0)
