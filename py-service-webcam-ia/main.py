"""Detector simples de cachorro usando OpenCV DNN + notificação via WebSocket.

Uso básico (PowerShell):
  python main.py --images picture/ --ws ws://localhost:8765

O programa procura por imagens na pasta `picture/` (por padrão), detecta
objetos usando MobileNet-SSD e, se um cachorro for detectado com confiança
acima do limiar, envia uma notificação JSON para o WebSocket informado.
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from base.detector import DogDetector
from base.websocket_client import send_notification
from base.camera_monitor import CameraMonitor


def gather_images(path: Path):
	if path.is_dir():
		for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):
			for p in path.glob(ext):
				yield p
	elif path.is_file():
		yield path


async def main_async(args):
	detector = DogDetector()

	images_path = Path(args.images)
	ws_url = args.ws

	any_detection = False
	for img_path in gather_images(images_path):
		print(f"Processando: {img_path}")
		detections = detector.detect(str(img_path), conf_threshold=args.conf)
		# Filtra por classe 'dog'
		dogs = [d for d in detections if d['class'] == 'dog']
		if dogs:
			any_detection = True
			best = max(dogs, key=lambda d: d['confidence'])
			msg = {
				'event': 'dog_detected',
				'image': str(img_path.name),
				'confidence': float(best['confidence'])
			}
			print(f"Cachorro detectado em {img_path.name} (conf={best['confidence']:.2f}) -> enviando notificação")
			try:
				# send_notification é síncrono (usa asyncio internamente), portanto não usar await
				send_notification(ws_url, msg)
			except Exception as e:
				print(f"Falha ao enviar notificação: {e}")
		else:
			print("Nenhum cachorro detectado nesta imagem.")

	if not any_detection:
		print("Nenhuma imagem com cachorro detectado.")


def main():
	parser = argparse.ArgumentParser(description='Detecta cachorro em imagens e envia notificação via WebSocket')
	parser.add_argument('--images', '-i', default='picture/', help='Arquivo de imagem ou pasta com imagens')
	parser.add_argument('--ws', default='ws://localhost:8765', help='URL do WebSocket para enviar notificações')
	parser.add_argument('--conf', type=float, default=0.5, help='Limiar mínimo de confiança (0..1)')
	parser.add_argument('--camera', action='store_true', help='Ativa monitoramento em tempo real pela webcam')
	parser.add_argument('--background', action='store_true', help='Executa o monitor em background (desanexa)')
	parser.add_argument('--show', action='store_true', help='Mostra janela com vídeo e caixas (apenas para debug)')
	parser.add_argument('--no-detach', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	# Se pediram monitor por câmera em background, relança processo desanexado
	if args.camera and args.background and not args.no_detach:
		# Reconstrói argumentos sem --background e adiciona --no-detach
		new_args = [sys.executable, os.path.abspath(__file__)]
		for a in sys.argv[1:]:
			if a == '--background' or a == '-b':
				continue
			new_args.append(a)
		new_args += ['--no-detach']

		# Tenta usar pythonw para esconder janela, se disponível
		pythonw = None
		base_exec = Path(sys.executable)
		pythonw_path = base_exec.with_name('pythonw.exe')
		if pythonw_path.exists():
			pythonw = str(pythonw_path)

		if pythonw:
			cmd = [pythonw] + new_args[1:]
			subprocess.Popen(cmd, close_fds=True)
		else:
			# fallback: cria processo sem janela
			CREATE_NO_WINDOW = 0x08000000
			subprocess.Popen(new_args, close_fds=True, creationflags=CREATE_NO_WINDOW)

		print('Monitor em background iniciado. Saindo do processo pai.')
		return

	# Executa o fluxo assíncrono ou modo câmera
	if args.camera:
		detector = DogDetector()
		monitor = CameraMonitor(detector, args.ws, conf_threshold=args.conf, show=args.show)
		import time
		try:
			print('Iniciando monitor de câmera (pressione Ctrl+C para parar)...')
			monitor.start()
			while True:
				# Mantém o processo vivo
				time.sleep(1)
		except KeyboardInterrupt:
			print('Parando monitor...')
			monitor.stop()
		return

	# Executa o fluxo assíncrono para imagens em disco
	asyncio.run(main_async(args))


if __name__ == '__main__':
	main()