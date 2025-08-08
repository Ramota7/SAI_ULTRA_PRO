# Tests oficiales SAI_UNICORNIO

- `test_alertas_telegram.py`: Valida el flujo completo de alertas Telegram para todos los eventos críticos del sistema.
- `test_imports.py`: Verifica que todos los módulos principales del sistema se pueden importar correctamente (sanity check de dependencias y estructura).
- `test_funcional_ciclo.py`: Simula un ciclo de trading en modo simulación y valida el flujo principal.
- `test_errores.py`: Fuerza errores en módulos críticos (Telegram, imports, ciclo de trading) y valida que el sistema los maneja de forma segura y controlada.

## Integración continua (CI)

Agrega estos tests a tu pipeline de CI para asegurar que las alertas Telegram funcionen correctamente, que la estructura del proyecto sea válida y que los errores sean manejados correctamente en cada despliegue.

### Ejemplo de integración (GitHub Actions):

```yaml
- name: Test alertas Telegram
  run: |
    python -u tests/test_alertas_telegram.py
- name: Test imports principales
  run: |
    python -u tests/test_imports.py
- name: Test funcional de ciclo de trading
  run: |
    python -u tests/test_funcional_ciclo.py
- name: Test de cobertura de errores
  run: |
    python -u tests/test_errores.py
```

> ⚠️ Requiere que las credenciales de Telegram estén configuradas en `config.json` y que el bot tenga acceso al chat.
