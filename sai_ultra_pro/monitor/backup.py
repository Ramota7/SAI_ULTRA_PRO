import os
import datetime

def guardar_backup():
    try:
        fecha = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backups_dir = os.path.join(base_dir, 'backups')
        print(f'[DEBUG BACKUP] backups_dir: {backups_dir}')
        os.makedirs(backups_dir, exist_ok=True)
        # Diagnóstico: crear archivo dummy
        dummy_path = os.path.join(backups_dir, f'dummy_{fecha}.txt')
        with open(dummy_path, 'w', encoding='utf-8') as fdummy:
            fdummy.write('dummy test')
        print(f'[DEBUG BACKUP] Archivo dummy creado: {dummy_path}')
    except Exception as e:
        print(f'[DEBUG BACKUP][ERROR] {e}')