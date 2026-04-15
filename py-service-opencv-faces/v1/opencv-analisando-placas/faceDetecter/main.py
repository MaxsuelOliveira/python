import cv2

# Carregue o classificador Haar para detecção de rostos
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Inicie a captura de vídeo
cap = cv2.VideoCapture('video.mp4')

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()

    # Se não houver mais frames, encerre o loop
    if not ret:
        break

    # Converta o frame para escala de cinza
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detecte rostos no frame
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Desenhe retângulos em volta dos rostos detectados
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Mostre o frame resultante
    cv2.imshow('Video', frame)

    # Interrompa o loop se a tecla 'q' for pressionada
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Encerre a captura de vídeo
cap.release()
cv2.destroyAllWindows()
