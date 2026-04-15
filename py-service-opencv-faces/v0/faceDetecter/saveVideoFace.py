import cv2

# Carrega o vídeo
cap = cv2.VideoCapture('video.mp4')

# Carrega o classificador de detecção de faces
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Define o codec e a taxa de quadros do vídeo de saída
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('video2.mp4', fourcc, 30.0, (1200, 720))

# Loop para processar cada quadro do vídeo
while True:
    # Lê o quadro do vídeo
    ret, frame = cap.read()

    # Verifica se chegou ao final do vídeo
    if not ret:
        break

    # Converte o quadro para escala de cinza
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detecta as faces na imagem
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5)

    # Desenha um retângulo em volta de cada face detectada
    for (x, y, w, h) in faces:
        imagem = cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), -1)

        # Salva o quadro com as faces detectadas no arquivo de saída
        out.write(imagem)

    # Mostra o vídeo com os retângulos das faces detectadas
    cv2.imshow('Video', frame)

    # Aguarda a tecla 'q' ser pressionada para encerrar o vídeo
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Libera a captura de vídeo, fecha a janela e o arquivo de saída
cap.release()
out.release()
cv2.destroyAllWindows()
