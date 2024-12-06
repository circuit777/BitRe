
Описание системы

Система состоит из двух частей: передатчика (Transmitter) на Java и приёмника (Receiver) на Python.
Идея передачи
Передатчик генерирует звуковой сигнал определённой частоты (например, 440 Гц) для передачи двоичных данных. Данные кодируются в длительности звукового импульса:
Бит '0': посылается тон 0,5 с, затем пауза 0,5 с (итого 1,0 с на бит).
Бит '1': посылается тон 1,0 с, затем пауза 0,5 с (итого 1,5 с на бит).
Перед передачей данных отправляется три длинных «синхроимпульса» по 2,0 с каждый (с паузой 0,5 с между ними). Это необходимо для того, чтобы приёмник мог «калиброваться» — понять, сколько времени длится импульс синхронизации, и на основе этого определить пропорциональную длительность бит '0' и '1'.
Схематично:
Синхронизация: 3 импульса по 2 с каждый + паузы по 0,5 с.
Передача данных: для каждого бита подаётся тон определенной длительности (0,5 с для '0', 1,0 с для '1') и затем пауза (0,5 с).
Приёмник
Приёмник (Python, PyQt5, PyAudio, numpy, pyqtgraph) «слушает» микрофонный вход в реальном времени. Он производит следующие операции:
Считывает аудиосэмплы с микрофона.
Вычисляет RMS (среднеквадратичное) значение сигнала для обнаружения наличия тона.
Нормализует данные и отображает их на графике в реальном времени.
Использует скользящее окно и порог для определения начала и конца импульсов.
Изначально приёмник находится в состоянии ожидания синхросигналов:
Если обнаруживает три длинных импульса, выполняет калибровку временных интервалов под бит '0' и бит '1'.
После калибровки переходит к состоянию приёма данных:
Каждый короткий импульс классифицируется либо как '0', либо как '1' исходя из его длительности.
Набирает 8 бит, декодирует их в символ ASCII и формирует исходное сообщение.
При повторном обнаружении синхроимпульсов приёмник может перестроиться и начать приём нового сообщения.
На интерфейсе приёмника отображаются:
Последний зафиксированный импульс и его длительность.
Накопленная последовательность бит.
Декодированное сообщение.
Также есть слайдер для динамического изменения порога амплитуды, по которому решается, что сигнал «есть» или «нет».
Как запустить

Передатчик (Java):
Убедитесь, что у вас установлен JDK.
Скомпилируйте и запустите Transmitter.java:
javac Transmitter.java
java Transmitter
Программа начнёт выводить звуковой сигнал через стандартное аудиоустройство.
Приёмник (Python):
Установите необходимые зависимости (PyAudio, PyQt5, pyqtgraph, numpy).
pip install pyqt5 pyqtgraph pyaudio numpy
Запустите Receiver.py:
python Receiver.py
Откроется окно с графиком, уровнем сигнала, индикаторами бит и сообщением.
Проведение эксперимента:
Запустите передатчик. Он будет генерировать три длинных синхроимпульса, затем передавать сообщение.
Приёмник после некоторого времени «схватит» три длинных импульса, калибруется и начнёт распознавать биты.
По окончании вы увидите полученное сообщение на экране приёмника.
Пример сообщения

В примере передаётся текст «kek». В ASCII это:
'k' = 0x6B = двоично: 01101011
'e' = 0x65 = двоично: 01100101
'k' = 0x6B = двоично: 01101011
Итого сообщение: 01101011 01100101 01101011 (24 бита).
Расчёт скорости передачи данных

Для оценки скорости рассмотрим интервалы, заявленные в коде:
Синхроимпульс: 2,0 с тон + 0,5 с пауза = 2,5 с на один импульс синхронизации. Для трёх импульсов: 3 * 2,5 с = 7,5 с.
Бит '0': 0,5 с тон + 0,5 с пауза = 1,0 с на бит.
Бит '1': 1,0 с тон + 0,5 с пауза = 1,5 с на бит.
Для нашего примера: «kek» = 24 бита.
Посчитаем количество нулей и единиц для «kek»:
'k' (01101011): нулей = 3, единиц = 5
'e' (01100101): нулей = 4, единиц = 4
'k' (01101011): нулей = 3, единиц = 5
Итого: нулей = 3+4+3 = 10, единиц = 5+4+5 = 14.
Общая длительность:
Для нулей (10 шт): 10 * 1,0 с = 10 с
Для единиц (14 шт): 14 * 1,5 с = 21 с
Итого на все данные: 10 с + 21 с = 31 с.
Плюс синхронизация: 7,5 с + 31 с = 38,5 с на всю передачу сообщения из 24 бит.
Скорость передачи:
Без учёта синхронизации: 24 бита / 31 с ≈ 0,77 бита/с
С учётом синхронизации: 24 бита / 38,5 с ≈ 0,62 бита/с
Таким образом, скорость крайне низкая, но для демонстрационного эксперимента или простейшего протокола – это допустимо.
Итоги

Данный код демонстрирует принципиальную возможность передачи данных с помощью длительности тональных импульсов, их обнаружения, синхронизации и последующего декодирования. Он может служить примером или учебным прототипом для более сложных систем акустической стеганографии, акустического модема или просто обучения принципам демодуляции сигнала по длительности импульсов.
Плюсы: простота реализации, наглядность, понятный протокол.
Минусы: очень низкая скорость передачи, чувствительность к шумам и настройкам порога.
Можно улучшать код, оптимизируя методы обнаружения сигнала, применяя фильтрацию, повышая частоту тона, сокращая паузы или кодировать не в длительности, а, например, в частоте или фазе, что потенциально увеличит скорость.
