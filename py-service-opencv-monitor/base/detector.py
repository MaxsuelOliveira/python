"""Módulo com DogDetector usando MobileNet-SSD (Caffe).

Se os arquivos do modelo não existirem, o detector tenta baixá-los.
"""
import os
from pathlib import Path
import cv2
import numpy as np
import requests


class DogDetector:
    # classes do MobileNet-SSD treinado no VOC (21 classes)
    CLASSES = [
        "background", "aeroplane", "bicycle", "bird", "boat",
        "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
        "dog", "horse", "motorbike", "person", "pottedplant",
        "sheep", "sofa", "train", "tvmonitor"
    ]

    # Tentativas de URL para baixar os modelos (ordem de preferência)
    PROTOTXT_URLS = [
        "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/MobileNetSSD_deploy.prototxt",
        "https://raw.githubusercontent.com/opencv/opencv_extra/master/testdata/dnn/MobileNetSSD_deploy.prototxt",
    ]
    CAFFEMODEL_URLS = [
        "https://github.com/chuanqi305/MobileNet-SSD/raw/master/MobileNetSSD_deploy.caffemodel",
        "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_mobilenet_ssd/MobileNetSSD_deploy.caffemodel",
    ]

    def __init__(self, model_dir: str = 'models'):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.prototxt_path = self.model_dir / 'MobileNetSSD_deploy.prototxt'
        self.model_path = self.model_dir / 'MobileNetSSD_deploy.caffemodel'

        self._ensure_models()
        self.net = cv2.dnn.readNetFromCaffe(str(self.prototxt_path), str(self.model_path))

    def _download(self, url: str, dest: Path) -> bool:
        """Tenta baixar a url para o destino. Retorna True se OK, False caso contrário."""
        try:
            print(f"Baixando {url} -> {dest}")
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            with open(dest, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            print(f"Falha ao baixar {url}: {e}")
            # garante que arquivo parcial seja removido
            try:
                if dest.exists():
                    dest.unlink()
            except Exception:
                pass
            return False

    def _ensure_models(self):
        # prototxt
        if not self.prototxt_path.exists():
            ok = False
            for url in self.PROTOTXT_URLS:
                if self._download(url, self.prototxt_path):
                    ok = True
                    break
            if not ok and not self.prototxt_path.exists():
                raise RuntimeError(
                    "Não foi possível baixar o arquivo prototxt do modelo.\n"
                    "Por favor, baixe manualmente 'MobileNetSSD_deploy.prototxt' e coloque em: {}\n"
                    "URLs sugeridas:\n  {}\n".format(self.prototxt_path, '\n  '.join(self.PROTOTXT_URLS))
                )

        # caffemodel
        if not self.model_path.exists():
            ok = False
            for url in self.CAFFEMODEL_URLS:
                if self._download(url, self.model_path):
                    ok = True
                    break
            if not ok and not self.model_path.exists():
                raise RuntimeError(
                    "Não foi possível baixar o arquivo caffemodel do modelo.\n"
                    "Por favor, baixe manualmente 'MobileNetSSD_deploy.caffemodel' e coloque em: {}\n"
                    "URLs sugeridas:\n  {}\n".format(self.model_path, '\n  '.join(self.CAFFEMODEL_URLS))
                )

    def detect(self, image, conf_threshold: float = 0.5):
        """Detecta objetos na imagem.

        Parâmetros:
        - image: caminho para arquivo de imagem (str) ou um numpy.ndarray (BGR)
        - conf_threshold: confiança mínima

        Retorna: lista de dicts: {class, confidence, box} onde
        box = (startX, startY, endX, endY) em pixels.
        """
        # Suporte para receber diretamente um frame (numpy.ndarray)
        if isinstance(image, (bytes, bytearray)):
            # bytes image -> decodifica
            arr = np.frombuffer(image, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        elif hasattr(image, 'shape'):
            img = image
        else:
            img = cv2.imread(image)

        if img is None:
            raise ValueError(f"Não foi possível abrir/processar a imagem fornecida")

        (h, w) = img.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 0.007843, (300, 300), 127.5)
        self.net.setInput(blob)
        detections = self.net.forward()

        results = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < conf_threshold:
                continue
            idx = int(detections[0, 0, i, 1])
            if idx < 0 or idx >= len(self.CLASSES):
                continue
            class_name = self.CLASSES[idx]
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype('int')
            results.append({
                'class': class_name,
                'confidence': confidence,
                'box': (int(startX), int(startY), int(endX), int(endY))
            })
        return results
