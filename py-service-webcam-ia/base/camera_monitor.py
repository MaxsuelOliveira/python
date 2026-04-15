"""Monitor de câmera que detecta cães em tempo real e envia notificações.

Uso básico:
  from base.camera_monitor import CameraMonitor
  monitor = CameraMonitor(detector, ws_url)
  monitor.start()  # roda em thread em background
  monitor.stop()
"""
import threading
import time
from typing import Optional

import cv2


class CameraMonitor:
    def __init__(self, detector, ws_url: str, conf_threshold: float = 0.5, show: bool = False, fps_reduce: int = 5):
        """Inicializa o monitor.

        - detector: instância de DogDetector (tem método detect(frame, conf_threshold))
        - ws_url: URL do websocket para enviar notificações
        - conf_threshold: limiar de confiança
        - show: se True, mostra janela com deteções
        - fps_reduce: processa 1 a cada `fps_reduce` frames para aliviar CPU
        """
        self.detector = detector
        self.ws_url = ws_url
        self.conf_threshold = conf_threshold
        self.show = show
        self.fps_reduce = max(1, int(fps_reduce))

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _notify(self, data):
        # envio em thread separada para não travar o loop da câmera
        from base.websocket_client import send_notification
        try:
            threading.Thread(target=send_notification, args=(self.ws_url, data), daemon=True).start()
        except Exception:
            pass

    def _run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Erro: não foi possível abrir a câmera. Verifique permissões.")
            return

        frame_idx = 0
        try:
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                frame_idx += 1
                if frame_idx % self.fps_reduce == 0:
                    try:
                        detections = self.detector.detect(frame, conf_threshold=self.conf_threshold)
                    except Exception as e:
                        # não interrompe loop
                        print(f"Erro ao detectar frame: {e}")
                        detections = []

                    dogs = [d for d in detections if d['class'] == 'dog']
                    if dogs:
                        best = max(dogs, key=lambda d: d['confidence'])
                        msg = {
                            'event': 'dog_detected',
                            'confidence': float(best['confidence'])
                        }
                        self._notify(msg)

                    if self.show:
                        # desenha boxes
                        for d in detections:
                            (sX, sY, eX, eY) = d['box']
                            label = f"{d['class']}:{d['confidence']:.2f}"
                            color = (0, 255, 0) if d['class'] == 'dog' else (0, 0, 255)
                            cv2.rectangle(frame, (sX, sY), (eX, eY), color, 2)
                            cv2.putText(frame, label, (sX, sY - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        cv2.imshow('CameraMonitor', frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break

                # pequena pausa para deixar CPU respirar
                time.sleep(0.01)
        finally:
            cap.release()
            if self.show:
                cv2.destroyAllWindows()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
