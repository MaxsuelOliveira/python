# Starting

## 3. Iniciar o processo com PM2

```bash
pm2 start ecosystem.config.js
```

## 4. Salvar os processos para reiniciar com o sistema

```bash
pm2 save
pm2 startup
```

## Comandos úteis

````bash
pm2 list              # Ver todos os serviços
pm2 logs              # Ver os logs em tempo real
pm2 restart all       # Reiniciar todos
pm2 stop all          # Parar todos
pm2 delete all        # Remover todos
```