#!/usr/bin/env python3

try:
    from asyncio.exceptions import CancelledError
except ModuleNotFoundError:
    from asyncio import CancelledError
from konashi import *
import konashi
from konashi.Settings import System as KonashiSystem
from konashi.Settings import Bluetooth as KonashiBluetooth
from konashi.Io import SoftPWM as KonashiSPWM
from konashi.Io import HardPWM as KonashiHPWM
from konashi.Io import Gpio as KonashiGpio
from konashi.Io import Analog as KonashiAin
from konashi.Builtin import Presence as KonashiPresence
from konashi.Builtin import AccelGyro as KonashiAccelGyro
from konashi.Builtin import Temperature as KonashiTemperature
from konashi.Builtin import Humidity as KonashiHumidity
from konashi.Builtin import Presence as KonashiPresence
from konashi.Builtin import RGBLed as KonashiRGB
import logging
import asyncio
import argparse

import math

global END
END=False
global Presence
Presence=False
global mel
#ド〜ファ〜ファファ ラ〜ソ〜ファソ ラ〜ファ〜ファ〜ラ〜ド〜レ〜
#レ〜ド〜ララ ファ〜ソ〜ファソ ラ〜(ソ)ファ〜レレ〜ド〜ファ〜
#レ〜ド〜ララ ファ〜ソ〜ファソ レ〜ド〜ララ〜ド〜レ〜
#レ〜ド〜ララ ファ〜ソ〜ファソ ラ〜(ソ)ファ〜レレ〜ド〜ファ〜
mel=[0,3,3,3,5,4,3,4,5,3,3,5,7,8 ,8,7,5,5,3,4,3,4,5,3,1,1,0,3 ,8,7,5,5,3,4,3,4,8,7,5,5,7,8, 8,7,5,5,3,4,3,4,5,3,1,1,0,3]
global Scale
#　　　  0       1      2      3     4      5      6       7　　　8      9     10     11     12
#       ド　　　レ　　 ミ    ファ　 ソ     ラ     シ　　　ド     レ     ミ    ファ    ソ     ラ　
Scale=[220.0, 246.9, 277.2, 293.7, 329.6 ,370.0, 415.3, 440.0, 493.9, 523.3, 587.3, 659.3, 698.5]
global RGB
RGB=[
        [255,0,0],
        [255,128,0],
        [255,255,0],
        [255,255,128],
        [255,255,255],
        [255,128,255],
        [255,0,255],

        [128,0,0],
        [128,128,0],
        [128,255,0],
        [128,255,128],
        [128,255,255],
        [128,128,255],
        [128,0,128],
    ]
global alpha
alpha=255

async def main(device):
    global END
    try:
        if device is None:
            logging.info("Scan for konashi devices for 5 seconds")
            ks = await Konashi.search(5)
            if len(ks) > 0:
                device = ks[0]
                logging.info("Use konashi device: {}".format(device.name))
            else:
                logging.error("Could no find a konashi device")
                return
        try:
            await device.connect(5)
        except Exception as e:
            logging.error("Could not connect to konashi device '{}': {}".format(device.name, e))
            return
        logging.info("Connected to device")

        global mel
        global alpha
        global RGB
        global Scale
        global d
        global f
        f=220.0
        d=0

        def presence_cb(pres):#人感センサー1
            global Presence
            Presence=pres
            print("Presence1:", pres)
        def input_cb(pin, level):
            global Presence2
            if level:
                Presence2=True
            else:
                Presence2=False
            logging.info("Pin {}: {},d= {}".format(pin, level,d))

        #人感センサ設定
        await device.builtin.presence.set_callback(presence_cb)
        # Input callback function set
        global Presence2
        Presence2=False
        device.io.gpio.set_input_cb(input_cb)
        # GPIO0: enable, input, notify on change, pull-down off, pull-up off, wired function off
        # GPIO1~4: enable, output, pull-down off, pull-up off, wired function off
        await device.io.gpio.config_pins([
            (0x01, KonashiGpio.PinConfig(KonashiGpio.PinDirection.INPUT, KonashiGpio.PinPull.NONE, True)),
        ])
        def hpwm_trans_end_cb(pin, duty):
            global Presence
            global alpha
            if 0 < pin <= 3:
                logging.info("HardPWM transition end on pin {}: current duty {}%".format(pin, duty))
                new_pin = 2
                if Presence or Presence2:
                    new_duty = 50
                    alpha=255
                else:
                    new_duty = 0
                    alpha=0
                if END:
                    new_duty = 0
                    alpha=0
                asyncio.create_task(device.io.hardpwm.control_pins([(0x1<<new_pin, KonashiHPWM.PinControl(device.io.hardpwm.calc_control_value_for_duty(new_duty), 2000))]))
        # Transition end callback functions set
        device.io.hardpwm.set_transition_end_cb(hpwm_trans_end_cb)
        # HardPWM clock settings: 10ms period
        await device.io.hardpwm.config_pwm(0.01)
        # HardPWM1~3: enable
        await device.io.hardpwm.config_pins([(0xe, True)])

        await device.io.hardpwm.control_pins([(0x2, KonashiHPWM.PinControl(device.io.hardpwm.calc_control_value_for_duty(100), 2000))])

        t=0
        while True:
            d=mel[t]
            f=Scale[d]
            await device.builtin.rgbled.set(RGB[d][0],RGB[d][1],RGB[d][2],alpha,100)
            await device.io.hardpwm.config_pwm(1/f)#音を鳴らす
            if Presence or Presence2:
                t+=1
                if t >= len(mel):
                    t=0
            logging.info("t={},{}".format(t,len(mel)))
            await asyncio.sleep(1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("Stop loop")
        END=True
        await device.builtin.rgbled.set(RGB[d][0],RGB[d][1],RGB[d][2],0,1)
    finally:
        try:
            if device is not None:
                await device.disconnect()
                logging.info("Disconnected")
        except konashi.Errors.KonashiConnectionError:
            pass
    logging.info("Exit")


parser = argparse.ArgumentParser(description="Connect to a konashi device, setup the PWMs and control them.")
parser.add_argument("--device", "-d", type=Konashi, help="The konashi device name to use. Ommit to scan and use first discovered device.")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()
main_task = None
try:
    main_task = loop.create_task(main(args.device))
    loop.run_until_complete(main_task)
except KeyboardInterrupt:
    if main_task is not None:
        main_task.cancel()
        loop.run_until_complete(main_task)
        main_task.exception()
finally:
    loop.close()