const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");

// Captura o vídeo da câmera e o áudio do microfone
navigator.mediaDevices
  .getUserMedia({ video: true, audio: true })
  .then((stream) => {
    localVideo.srcObject = stream;

    // Cria uma conexão WebSocket
    const socket = new WebSocket("ws://192.168.3.19:8765");
    socket.binaryType = "arraybuffer";

    // Envia os dados de vídeo e áudio para o servidor
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: "video/webm; codecs=vp8,opus",
    });
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        socket.send(event.data);
      }
    };
    mediaRecorder.start(100); // Envia dados a cada 100ms

    // Recebe os dados de vídeo e áudio do servidor
    socket.onmessage = (event) => {
      const videoBlob = new Blob([event.data], { type: "video/webm" });
      const videoUrl = URL.createObjectURL(videoBlob);
      remoteVideo.src = videoUrl;
    };
  })
  .catch((error) => {
    console.error("Erro ao acessar a câmera e o microfone: ", error);
  });
