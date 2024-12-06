package circuit;
import javax.sound.sampled.*;

public class Transmitter {
    public static void main(String[] args) throws LineUnavailableException {
        // Задаем текст для передачи
        String message = "kek"; // Можно изменить на любой текст

        // Преобразуем текст в двоичную последовательность
        String sequence = textToBinarySequence(message);
        System.out.println("Передаваемая битовая последовательность: " + sequence);

        float sampleRate = 44100;
        double frequency = 440.0; // Частота тона

        // Длительности в секундах для 0 и 1:
        double zeroDuration = 0.5;
        double oneDuration = 1.0;
        double pauseDuration = 0.5;

        // Добавим синхронизирующие импульсы (3 импульса по 2 с)
        double syncDuration = 2.0; // длительный импульс для синхронизации
        int syncCount = 3;

        AudioFormat format = new AudioFormat(
                AudioFormat.Encoding.PCM_SIGNED,
                sampleRate,
                16,
                1,
                2,
                sampleRate,
                false
        );
        SourceDataLine line = AudioSystem.getSourceDataLine(format);
        line.open(format);
        line.start();

        // Генерируем 3 длинных импульса
        for (int i = 0; i < syncCount; i++) {
            playTone(line, frequency, syncDuration, sampleRate);
            playSilence(line, pauseDuration, sampleRate);
        }

        // Теперь передаем основные данные
        for (char bit : sequence.toCharArray()) {
            double duration = (bit == '0') ? zeroDuration : oneDuration;
            // Генерируем тон для текущего бита
            playTone(line, frequency, duration, sampleRate);

            // Пауза между битами
            playSilence(line, pauseDuration, sampleRate);
        }

        line.drain();
        line.close();
    }

    /**
     * Преобразует текстовую строку в битовую последовательность (ASCII, 8 бит на символ).
     */
    private static String textToBinarySequence(String text) {
        StringBuilder sb = new StringBuilder();
        for (char c : text.toCharArray()) {
            int ascii = (int) c;
            // Форматируем в двоичную строку длиной 8 символов с ведущими нулями
            String binaryString = String.format("%8s", Integer.toBinaryString(ascii)).replace(' ', '0');
            sb.append(binaryString);
        }
        return sb.toString();
    }

    private static void playTone(SourceDataLine line, double freq, double duration, float sampleRate) {
        int length = (int) (duration * sampleRate);
        byte[] buffer = new byte[length * 2]; // 16-битный сигнал (2 байта на сэмпл)
        for (int i = 0; i < length; i++) {
            double angle = 2.0 * Math.PI * i * freq / sampleRate;
            short value = (short) (Math.sin(angle) * Short.MAX_VALUE);
            buffer[i * 2] = (byte) (value & 0xff);
            buffer[i * 2 + 1] = (byte) ((value >> 8) & 0xff);
        }
        line.write(buffer, 0, buffer.length);
    }

    private static void playSilence(SourceDataLine line, double duration, float sampleRate) {
        int length = (int) (duration * sampleRate);
        byte[] buffer = new byte[length * 2];
        // Заполнено нулями, значит тишина
        line.write(buffer, 0, buffer.length);
    }
}
