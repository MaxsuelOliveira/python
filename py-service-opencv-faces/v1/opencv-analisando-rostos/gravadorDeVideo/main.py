import cv2
import numpy as np
import time

# Inicializa o objeto de captura de tela
screen_capture = cv2.VideoCapture(0)

# Defina as dimensões da tela
screen_width = int(screen_capture.get(3))
screen_height = int(screen_capture.get(4))

# Defina o codec do vídeo e o nome do arquivo
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('output.avi', fourcc, 20.0, (screen_width, screen_height))

start_time = time.time()

# Enquanto o tempo de gravação não é alcançado
while time.time() - start_time < 10:
    ret, frame = screen_capture.read()
    if ret:
        # Converte a tela para escala de cinza
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Grava o quadro atual
        out.write(frame)

        # Exibe a tela capturada
        cv2.imshow('Screen capture', gray)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Limpa as janelas e libera o objeto de captura de tela
screen_capture.release()
out.release()
cv2.destroyAllWindows()