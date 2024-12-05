import network
import time
import gc
import machine
from machine import UART
from machine import Pin
from umqtt.simple import MQTTClient


class config:
    SSID = ''
    PSK = ''
    MQTT_HOST = ''
    MQTT_USERNAME = ''
    MQTT_PASSWORD = ''
    MQTT_TOPIC = ''


class FakeData():

    DATA = [
        "/KAM5",
        "",
        "0-0:1.0.0(231117132609W)",
        "1-0:1.8.0(00010293.840*kWh)",
        "1-0:2.8.0(00000000.000*kWh)",
        "1-0:3.8.0(00000957.525*kVArh)",
        "1-0:4.8.0(00001483.853*kVArh)",
        "1-0:1.7.0(0000.345*kW)",
        "1-0:2.7.0(0000.000*kW)",
        "1-0:3.7.0(0000.000*kVAr)",
        "1-0:4.7.0(0000.126*kVAr)",
        "1-0:21.7.0(0000.027*kW)",
        "1-0:41.7.0(0000.105*kW)",
        "1-0:61.7.0(0000.213*kW)",
        "1-0:22.7.0(0000.000*kW)",
        "1-0:42.7.0(0000.000*kW)",
        "1-0:62.7.0(0000.000*kW)",
        "1-0:23.7.0(0000.006*kVAr)",
        "1-0:43.7.0(0000.000*kVAr)",
        "1-0:63.7.0(0000.000*kVAr)",
        "1-0:24.7.0(0000.000*kVAr)",
        "1-0:44.7.0(0000.097*kVAr)",
        "1-0:64.7.0(0000.035*kVAr)",
        "1-0:32.7.0(229.4*V)",
        "1-0:52.7.0(228.6*V)",
        "1-0:72.7.0(230.0*V)",
        "1-0:31.7.0(000.1*A)",
        "1-0:51.7.0(000.7*A)",
        "1-0:71.7.0(001.1*A)",
        "!9421"
    ]

    def __init__(self):
        self.pos = 0

    def readline(self):
        if self.pos % len(self.DATA) == 0:
            time.sleep(10)
        tmp = self.DATA[self.pos % len(self.DATA)]
        self.pos += 1
        return tmp + '\n'


def readline_into_buffer(uart, buffer, pos):
    s = uart.readline()
    if s is None:
        print('UART TIMEOUT')
        machine.soft_reset()
        return
    sb = bytes(s, 'utf-8')
    buffer[pos : pos + len(sb)] = sb
    return len(sb)


def main():
    # Setup
    uart = UART(1, baudrate=115200, invert=UART.INV_RX, rx=Pin(5), timeout=11000)
    #uart = FakeData()
    led = machine.Pin('LED', machine.Pin.OUT)

    # Connect wlan
    led.off()
    network.hostname('HANmeter')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config.SSID, config.PSK)

    waitcount = 0
    while wlan.status() != 3:
        waitcount += 1
        time.sleep(0.5)
        led.toggle()
        if waitcount > 120:
            led.off()
            print('WIFI CONNECTION TIMEOUT')
            machine.soft_reset()
            return

    led.on()
    print('WIFI CONNECTED')

    # Connect MQTT
    mqc = MQTTClient('HANMeter', config.MQTT_HOST, 1883,
                     user=config.MQTT_USERNAME, password=config.MQTT_PASSWORD)
    try:
        mqc.connect()
    except Exception as e:
        print(f'MQTT EXCEPTION {type(e)}: {e}')
        machine.soft_reset()
        return
    print('MQTT CONNECTED')

    # Main loop
    buffer = bytearray(1024)
    while True:
        pos = 0

        # Read lines until we read the first line of a message
        # (which starts with a '/')
        while True:
            tmp = readline_into_buffer(uart, buffer, pos)
            if buffer[0] == ord('/'):
                pos = tmp
                break

        led.off()

        # Keep reading lines, adding them to the buffer, until we read the
        # last line of the message (which starts with a '!')
        while True:
            tmp = readline_into_buffer(uart, buffer, pos)
            pos += tmp
            if buffer[pos - tmp] == ord('!'):
                break

        # Publish the message
        try:
            mqc.publish(config.MQTT_TOPIC, buffer[:pos])
            print(f'MQTT MESSAGE PUBLISHED')
        except Exception as e:
            print(f'MQTT EXCEPTION {type(e)}: {e}')
            machine.soft_reset()
            return

        gc.collect()
        led.on()


main()