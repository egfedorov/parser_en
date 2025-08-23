import os
import importlib

def main():
    feeds_dir = 'backend'
    for fname in os.listdir(backend_dir):
        # Игнорируем не-Python-файлы, скрытые файлы, __init__.py и всё, что начинается с "_"
        if (
            not fname.endswith('.py')
            or fname.startswith('_')
            or fname == '__init__.py'
            or fname.startswith('.')
        ):
            continue
        modname = fname[:-3]
        try:
            module = importlib.import_module(f'{backend_dir}.{modname}')
            if hasattr(module, 'generate'):
                print(f'⚙️  Generating via generate(): {modname}')
                module.generate()
            elif hasattr(module, 'main'):
                print(f'⚙️  Generating via main(): {modname}')
                module.main()
            else:
                print(f'⚠️  {modname}: нет функций generate() или main()')
        except Exception as e:
            print(f'❌ Ошибка при генерации {modname}: {e}')

if __name__ == '__main__':
    main()
