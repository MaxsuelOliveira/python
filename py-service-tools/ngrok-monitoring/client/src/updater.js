import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const NGROK_API = 'http://127.0.0.1:4040/api/tunnels';

async function getNgrokUrl() {
  try {
    const response = await axios.get(NGROK_API);
    const tunnels = response.data.tunnels;

    const httpTunnel = tunnels.find(t => t.proto === 'https') || tunnels[0];
    return httpTunnel?.public_url || null;
  } catch (error) {
    console.error('Erro ao acessar a API local do ngrok:', error.message);
    return null;
  }
}

async function sendUrlToServer(url) {
  try {
    const response = await axios.post(
      process.env.SERVER_URL,
      {
        cliente_id: process.env.CLIENTE_ID,
        url: url,
      },
      {
        headers: {
          Authorization: `Bearer ${process.env.CLIENT_TOKEN}`,
        },
      }
    );

    console.log(`[${new Date().toISOString()}] ✅ URL enviada: ${url}`);
  } catch (error) {
    console.error('❌ Erro ao enviar URL para o servidor:', error.message);
  }
}

async function monitorLoop() {
  console.log('Iniciando monitor de URL ngrok...');
  const intervalo = parseInt(process.env.INTERVALO || '60000');

  while (true) {
    const url = await getNgrokUrl();
    if (url) {
      await sendUrlToServer(url);
    } else {
      console.log('⚠️ URL do ngrok não encontrada. Retentando...');
    }

    await new Promise(resolve => setTimeout(resolve, intervalo));
  }
}

monitorLoop();
