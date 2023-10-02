import argparse as ARG
import random as RDM
import time as TIME

from pythonosc import udp_client


if __name__ == "__main__":
    print('client process start')
    parser = ARG.ArgumentParser()
    #Add ip to the argument parser
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    client = udp_client.SimpleUDPClient(args.ip, args.port)

    for x in range(10):
        value = RDM.random()
        print(value)
        client.send_message("/values", value)
        print('sent message on: ' + str(value))
        TIME.sleep(2)
