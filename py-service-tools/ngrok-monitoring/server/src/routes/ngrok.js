// server/src/routes/ngrok.js
import express from 'express';
import prisma from '../../prismaClient.js';
import { clientAuthMiddleware } from '../middlewares/clientAuth.js';

const router = express.Router();

// Cliente envia sua URL ngrok
router.post('/', clientAuthMiddleware, async (req, res) => {
  const { cliente_id, url } = req.body;

  if (!cliente_id || !url) {
    return res.status(400).json({ error: 'cliente_id e url são obrigatórios' });
  }

  try {
    const cliente = await prisma.cliente.findUnique({ where: { id: cliente_id } });
    if (!cliente) return res.status(404).json({ error: 'Cliente não encontrado' });

    const atual = await prisma.urlNgrok.upsert({
      where: { clienteId: cliente_id },
      update: { url },
      create: { clienteId: cliente_id, url },
    });

    res.json({ success: true, data: atual });
  } catch (error) {
    console.error('Erro ao atualizar URL:', error);
    res.status(500).json({ error: 'Erro interno' });
  }
});

// Consulta URL atual por cliente
router.get('/:id', async (req, res) => {
  const { id } = req.params;

  try {
    const url = await prisma.urlNgrok.findFirst({
      where: { clienteId: id },
      orderBy: { updatedAt: 'desc' },
    });
    if (!url) return res.status(404).json({ error: 'Nenhuma URL encontrada' });

    res.json(url);
  } catch (error) {
    console.error('Erro ao consultar URL:', error);
    res.status(500).json({ error: 'Erro interno' });
  }
});

export default router;
