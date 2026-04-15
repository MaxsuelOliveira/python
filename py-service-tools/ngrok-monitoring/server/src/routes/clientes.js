// server/src/routes/clientes.js
import express from 'express';
import prisma from '../../prismaClient.js';

const router = express.Router();

// Lista todos os clientes
router.get('/', async (req, res) => {
  try {
    const clientes = await prisma.cliente.findMany();
    res.json(clientes);
  } catch (error) {
    console.error('Erro ao listar clientes:', error);
    res.status(500).json({ error: 'Erro interno' });
  }
});

// Cria novo cliente
router.post('/', async (req, res) => {
  const { nome, token } = req.body;
  if (!nome || !token) return res.status(400).json({ error: 'nome e token são obrigatórios' });

  try {
    const novo = await prisma.cliente.create({ data: { nome, token } });
    res.json(novo);
  } catch (error) {
    console.error('Erro ao criar cliente:', error);
    res.status(500).json({ error: 'Erro interno' });
  }
});

// Deleta cliente por ID
router.delete('/:id', async (req, res) => {
  const { id } = req.params;
  try {
    await prisma.cliente.delete({ where: { id } });
    res.json({ success: true });
  } catch (error) {
    console.error('Erro ao deletar cliente:', error);
    res.status(500).json({ error: 'Erro interno' });
  }
});

export default router;
