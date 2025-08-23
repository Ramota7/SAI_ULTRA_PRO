SECURITY_GUIDELINES

Resumen rápido:
- No almacenar secretos en el repositorio. Use un Secret Manager (Azure KeyVault, AWS Secrets Manager, Hashicorp Vault) o variables de entorno.
- Mantenga `sai_ultra_pro/config/config.json` sin claves sensibles en el repositorio. Use `sai_ultra_pro/config/secrets.example.json` como plantilla.
- Forzar `modo_observacion=true` en entornos de CI y pruebas.

Checklist mínimo para despliegue 24/7:
- Revisar y rotar API keys antes de activar modo LIVE.
- Configurar alertas (Telegram / email) y validar envío con healthcheck.
- Configurar backups de logs y retención.

Cómo inyectar secretos en runtime:
- Preferible: usar managed identity + Secret Manager.
- Alternativa: exportar variables de entorno antes de iniciar el proceso:
  - TELEGRAM_BOT_TOKEN
  - TELEGRAM_CHAT_ID
  - BINANCE_API_KEY
  - BINANCE_API_SECRET
  - EXNESS_API_KEY
  - EXNESS_API_SECRET

Notas:
- Nunca subir `sai_ultra_pro/config/config.json` con valores reales de API.
- Para pruebas locales, use `secrets.example.json` como guía.
