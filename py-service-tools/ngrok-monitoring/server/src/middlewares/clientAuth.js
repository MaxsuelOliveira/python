export function clientAuthMiddleware(req, res, next) {
  const token = req.headers['authorization']?.split(' ')[1]; // Bearer TOKEN

  if (!token || token !== process.env.CLIENT_TOKEN) {
    return res.status(401).json({ error: 'Token inválido ou ausente' });
  }

  next();
}
