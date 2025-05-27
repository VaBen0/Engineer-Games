import machine
from machine import Pin, PWM, I2C
from time import sleep_ms
import bluetooth
from ble_advertising import advertising_payload
from micropython import const
import uasyncio as asio

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_UART_UUID = bluetooth.UUID("0bc0a05f-a921-47c5-9add-340f010349fe")
_UART_TX = (
    bluetooth.UUID("0bc0a05f-a921-47c5-9add-340f010349fe"),
    _FLAG_NOTIFY,
)
_UART_RX = (
    bluetooth.UUID("e4407cbd-8edb-4d19-849a-c387b22788b0"),
    _FLAG_WRITE,
)
_UART_SERVICE = (
    _UART_UUID,
    (_UART_TX, _UART_RX),
)
_ADV_APPEARANCE_GENERIC_COMPUTER = const(128)

class BLEUART:
    def __init__(self, ble, name="test_bot", rxbuf=100):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((_UART_SERVICE,))
        self._ble.gatts_set_buffer(self._rx_handle, rxbuf, True)
        self._connections = set()
        self._rx_buffer = bytearray()
        self._handler = None
        self._payload = advertising_payload(name="lightings", appearance=_ADV_APPEARANCE_GENERIC_COMPUTER)
        self._advertise()

    def irq(self, handler):
        self._handler = handler

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if conn_handle in self._connections and value_handle == self._rx_handle:
                self._rx_buffer += self._ble.gatts_read(self._rx_handle)
                if self._handler:
                    self._handler()

    def any(self):
        return len(self._rx_buffer)

    def read(self, sz=None):
        if not sz:
            sz = len(self._rx_buffer)
        result = self._rx_buffer[:sz]
        self._rx_buffer = self._rx_buffer[sz:]
        return result

    def write(self, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._tx_handle, data)

    def close(self):
        for conn_handle in self._connections:
            self._ble.gap_disconnect(conn_handle)
        self._connections.clear()

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
        

# Инициализация BLE UART
ble = bluetooth.BLE()
uart = BLEUART(ble)
uart.irq(handler=on_rx)

sp = 1023  # Полная скорость
freq = 10000

# Мотор
in1 = PWM(Pin(2), freq) #левый
in2 = PWM(Pin(4), freq)

# Пины для второго мотора (правый)
in3 = PWM(Pin(17), freq)
in4 = PWM(Pin(16), freq) # D16, D17 — правый мотор

# Сервопривод
pwm = PWM(Pin(23, Pin.OUT))
pwm.freq(50)
pwm.duty(0)
an = 90  # Начальный угол сервы

comand = ''
on = 0

def stop_motor():
    in1.duty(0)
    in2.duty(0)
    in3.duty(0)
    in4.duty(0)
    print("Моторы остановлены")

def move_forward(spud):
    in1.duty(0)
    in2.duty(spud)  # Левый вперёд
    in3.duty(spud)  # Правый вперёд
    in4.duty(0)
    #print("Моторы движутся вперёд " + str(spud))

def move_backward(spud):
    in1.duty(spud)
    in2.duty(0)      # Левый назад
    in3.duty(0)
    in4.duty(spud)  # Правый назад
    print("Моторы движутся назад")

def move_left(spud):
    # Острый поворот на месте
    in1.duty(spud)
    in2.duty(0)
    in3.duty(spud)
    in4.duty(0)

def move_right(spud):
    # Острый поворот на месте
    in1.duty(0)
    in2.duty(spud)
    in3.duty(0)
    in4.duty(spud)

def turn(spud, direction):

    slow_speed = int(spud * 0.6)  # Меньшая скорость для одного из моторов

    if direction == "left_forward":
        # Левый мотор медленнее → поворот влево
        in1.duty(0)
        in2.duty(slow_speed)
        in3.duty(spud)
        in4.duty(0)
        print("Поворот влево")

    elif direction == "right_forward":
        # Правый мотор медленнее → поворот вправо
        in1.duty(0)
        in2.duty(spud)
        in3.duty(slow_speed)
        in4.duty(0)
        print("Поворот вправо")
    elif direction == "left_backward":
        # Левый мотор медленнее → поворот влево
        in1.duty(slow_speed)
        in2.duty(0)
        in3.duty(0)
        in4.duty(spud)
        print("Поворот влево")

    elif direction == "right_backward":
        # Правый мотор медленнее → поворот вправо
        in1.duty(spud)
        in2.duty(0)
        in3.duty(0)
        in4.duty(slow_speed)
        print("Поворот вправо")

def on_rx():
    global comand, on
    try:
        received = uart.read().decode().strip()
        print("Получено:", received)

        if received.startswith("AT+"):
            comand = received[2:]
        else:
            comand = received
        on = 1
    except Exception as e:
        print("Ошибка приёма:", e)    

def map(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def servo(pin, angle):
    pin.duty(map(angle, 0, 180, 20, 120))

async def do_it(int_ms):
    global an, on
    cmd = ""
    spud = 0

    while True:
        await asio.sleep_ms(int_ms)

        if ':' in comand:
            part = comand.split(':')
            cmd = part[0]
            if cmd == "SERVO":
                spud = int(part[1])
            else:
                spud = (sp * int(part[1])) // 100

        if cmd == "FORWARD":
            move_forward(spud)
        elif cmd == "BACKWARD":
            move_backward(spud)
        elif cmd == "STOP":
            stop_motor()
        elif cmd == "FORWARDLEFT":
            turn(spud, "left_forward")
        elif cmd == "FORWARDRIGHT":
            turn(spud, "right_forward")
        elif cmd == "BACKWARDLEFT":
            turn(spud, "left_backward")
        elif cmd == "BACKWARDRIGHT":
            turn(spud, "right_backward")
        elif cmd == "LEFT":
            move_left(spud)
        elif cmd == "RIGHT":
            move_right(spud)
        elif cmd == "SERVO":
            an = spud
            servo(pwm, an)

  
# Запуск асинхронного цикла
loop = asio.get_event_loop()
loop.create_task(do_it(5))
loop.run_forever()