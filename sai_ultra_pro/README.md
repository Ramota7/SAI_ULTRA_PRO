# SAI ULTRA PRO — Seguridad y ejecución segura

Variables de entorno relevantes para ejecución segura y tests:

- `ALLOW_REAL_TRADES=1` : permite enviar órdenes reales; por defecto está deshabilitado y el sistema opera en modo observación.
- `TEST_FAST=1` : acelera sleeps y ciclos para ejecutar tests rápidamente en CI/local.
- `TEST_NO_NETWORK=1` o `NETWORK_DISABLED=1` : deshabilita llamadas HTTP salientes; ideal para tests que no deben tocar la red.

Recomendación: en CI y durante desarrollo mantener `ALLOW_REAL_TRADES` deshabilitado y usar `TEST_FAST` y `TEST_NO_NETWORK` para tests deterministas.
