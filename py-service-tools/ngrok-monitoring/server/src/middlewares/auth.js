import basicAuth from 'basic-auth';

export function basicAuthMiddleware(req, res, next) {
  const user = basicAuth(req);

  if (!user || !user.name || !user.pass) {
    res.set('WWW-Authenticate', 'Basic realm="ngrok-monitoring"');
    return res.status(401).json({ error: 'Autenticação necessária' });
  }

  if (
    user.name !== process.env.API_USER ||
    user.pass !== process.env.API_PASS
  ) {
    return res.status(403).json({ error: 'Usuário ou senha inválidos' });
  }

  next();
}

export function ipFilterMiddleware(req, res, next) {
  const allowedIps = process.env.ALLOWED_IPS?.split(',') || [];
  const requestIp = req.ip || req.connection.remoteAddress;

  if (!allowedIps.includes(requestIp)) {
    return res.status(403).json({ error: 'IP não autorizado' });
  }
  next();
}
