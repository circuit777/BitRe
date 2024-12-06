import sys
import pyaudio
import numpy as np
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

class Receiver(QtWidgets.QWidget):
    def __init__(self, rate=44100, chunk=512, window_duration=15):
        super().__init__()
        
        self.rate = rate
        self.chunk = chunk
        self.window_duration = window_duration
        
        # Количество точек в окне
        self.num_points = int((self.rate / self.chunk) * self.window_duration)
        
        # Массив уровней (RMS)
        self.level_data = np.zeros(self.num_points, dtype=np.float32)
        self.time_axis = np.linspace(-self.window_duration, 0, self.num_points)
        
        # Настройка аудио
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=self.rate,
                                  input=True,
                                  frames_per_buffer=self.chunk)
        
        pg.setConfigOption('background', 'k')
        pg.setConfigOption('foreground', 'w')
        pg.setConfigOptions(antialias=True)

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)

        self.plot_widget.setYRange(0, 1)
        self.plot_widget.setXRange(-self.window_duration, 0)
        self.plot_widget.setLabel('left', 'Normalized Level')
        self.plot_widget.setLabel('bottom', 'Time', 's')
        self.plot_widget.setTitle(f'Приём с синхронизацией')

        self.curve = self.plot_widget.plot(self.time_axis, self.level_data, pen=pg.mkPen('g', width=2))
        
        # Начальный порог
        self.threshold = 0.5
        self.threshold_line = self.plot_widget.addLine(y=self.threshold, pen=pg.mkPen('r', width=2, style=pg.QtCore.Qt.DashLine))
        
        # Метки интерфейса
        self.impulse_label = QtWidgets.QLabel("Последний импульс: - с")
        self.bits_label = QtWidgets.QLabel("Биты: ")
        self.message_label = QtWidgets.QLabel("Сообщение: ")
        main_layout.addWidget(self.impulse_label)
        main_layout.addWidget(self.bits_label)
        main_layout.addWidget(self.message_label)

        # Слайдер для настройки порога
        self.threshold_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(int(self.threshold * 100))
        self.threshold_slider.valueChanged.connect(self.update_threshold)
        main_layout.addWidget(QtWidgets.QLabel("Порог:"))
        main_layout.addWidget(self.threshold_slider)

        # Сглаживание RMS
        self.alpha = 0.1  
        self.prev_rms = 0.0

        # Состояния приёмника
        self.STATE_WAITING_FOR_SYNC = 0
        self.STATE_RECEIVING = 1
        self.state = self.STATE_WAITING_FOR_SYNC

        # Переменные для импульсов
        self.is_above = False
        self.impulse_start_index = None
        self.frame_counter = 0
        
        # Глобальный максимум для нормализации
        self.global_max = 1e-9

        # Хранилище бит
        self.received_bits = ""
        # Декодированное сообщение
        self.decoded_message = ""

        # Для синхронизации
        self.sync_pulses = []  # храним длительности 3 синхроимпульсов
        self.sync_count_needed = 3
        # После синхронизации определим длительности бит
        self.bit_zero_duration = None
        self.bit_one_duration = None
        self.duration_split = None

        # Таймер обновления
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10)
        
    def update_threshold(self, value):
        # Пересчитываем порог из значения слайдера (0-100) в (0.0 - 1.0)
        self.threshold = value / 100.0
        # Перемещаем линию порога
        self.threshold_line.setValue(self.threshold)

    def calibrate_from_sync(self):
        avg_sync = sum(self.sync_pulses)/len(self.sync_pulses)
        # Калибровка
        # Известно: 0 ~ 0.5с, 1 ~ 1.0с, sync ~2.0с
        self.bit_zero_duration = avg_sync * (0.5/2.0)   # ~0.5с
        self.bit_one_duration  = avg_sync * (1.0/2.0)   # ~1.0с
        self.duration_split    = (self.bit_zero_duration + self.bit_one_duration)/2.0

    def start_receiving(self):
        self.state = self.STATE_RECEIVING
        print("Синхронизация завершена. Начинаем прием данных.")

    def update_plot(self):
        data = self.stream.read(self.chunk, exception_on_overflow=False)
        signal = np.frombuffer(data, dtype=np.int16)
        
        # RMS
        rms_current = np.sqrt(np.mean(signal.astype(np.float32)**2))
        
        rms_smoothed = self.alpha * rms_current + (1 - self.alpha) * self.prev_rms
        self.prev_rms = rms_smoothed
        
        self.level_data = np.roll(self.level_data, -1)
        self.level_data[-1] = rms_smoothed
        
        if rms_smoothed > self.global_max:
            self.global_max = rms_smoothed
        
        normalized_data = self.level_data / self.global_max
        self.curve.setData(self.time_axis, normalized_data)

        current_val = normalized_data[-1]
        current_above = (current_val > self.threshold)

        # Обработка импульсов
        if not self.is_above and current_above:
            # Начался импульс
            self.is_above = True
            self.impulse_start_index = self.frame_counter
        elif self.is_above and not current_above:
            # Импульс закончился
            self.is_above = False
            impulse_length_frames = self.frame_counter - self.impulse_start_index
            impulse_length_sec = impulse_length_frames * (self.chunk / self.rate)
            self.impulse_label.setText(f"Последний импульс: {impulse_length_sec:.3f} с")

            # Проверка на длинный импульс (кандидат на синхроимпульс)
            is_long_impulse = (impulse_length_sec > 1.5)

            if self.state == self.STATE_WAITING_FOR_SYNC:
                if is_long_impulse:
                    self.sync_pulses.append(impulse_length_sec)
                    if len(self.sync_pulses) == self.sync_count_needed:
                        # Получили три синхроимпульса - калибровка и переход к приёму
                        self.calibrate_from_sync()
                        self.sync_pulses.clear()
                        self.start_receiving()
                else:
                    # Короткий импульс при ожидании синхры - сброс
                    self.sync_pulses.clear()
            else:
                # STATE_RECEIVING
                if is_long_impulse:
                    # Добавляем в sync_pulses для проверки на новую синхру
                    self.sync_pulses.append(impulse_length_sec)
                    if len(self.sync_pulses) == self.sync_count_needed:
                        # Получили 3 длинных импульса в режиме приёма - значит начало новой синхры
                        self.calibrate_from_sync()
                        self.sync_pulses.clear()

                        # Очищаем предыдущие данные сообщения для нового приёма
                        self.received_bits = ""
                        self.decoded_message = ""
                        self.bits_label.setText("Биты: ")
                        self.message_label.setText("Сообщение: ")
                        print("Повторная синхронизация. Начинаем приём нового сообщения.")
                        # Оставляем состояние RECEIVING, так как мы сразу готовы принимать новое сообщение.
                else:
                    # Короткий импульс в режиме приёма - бит данных
                    # Если были накопленные длинные импульсы, но не три, сбросим их
                    self.sync_pulses.clear()

                    if self.duration_split is not None:
                        bit = '0' if impulse_length_sec < self.duration_split else '1'
                        self.received_bits += bit
                        self.bits_label.setText("Биты: " + self.received_bits)
                        # Если набрали 8 бит — декодируем символ
                        if len(self.received_bits) >= 8:
                            byte_str = self.received_bits[:8]
                            self.received_bits = self.received_bits[8:]
                            char = chr(int(byte_str, 2))
                            self.decoded_message += char
                            self.message_label.setText("Сообщение: " + self.decoded_message)

        self.frame_counter += 1

    def closeEvent(self, event):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = Receiver()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
