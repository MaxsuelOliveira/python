// server/src/index.js
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import ngrokRoutes from './routes/ngrok.js';
import clienteRoutes from './routes/clientes.js';
import { basicAuthMiddleware, ipFilterMiddleware } from './middlewares/auth.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Autenticacao para rotas administrativas
app.use('/api/clientes', basicAuthMiddleware, ipFilterMiddleware);

// Rotas API
app.use('/api/ngrok', ngrokRoutes);
app.use('/api/clientes', clienteRoutes);

app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});
