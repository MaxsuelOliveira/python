// ecosystem.config.js

export default {
  apps: [
    {
      name: 'ngrok-updater',
      script: './src/updater.js',
      watch: false,
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
