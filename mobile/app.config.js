// Completa o app.json. No build do EAS, o google-services.json (chave do Firebase para as notificações) vem da
// variável de arquivo GOOGLE_SERVICES_JSON, porque o arquivo fica fora do git. Veja mobile/README.md.
module.exports = ({ config }) => ({
  ...config,
  android: {
    ...config.android,
    googleServicesFile: process.env.GOOGLE_SERVICES_JSON || config.android?.googleServicesFile,
  },
});
