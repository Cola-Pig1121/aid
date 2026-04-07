# hooks/hook-gradio.py
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules
import os

datas = collect_data_files('gradio')
hiddenimports = collect_submodules('gradio')

datas += collect_data_files('gradio_client')
hiddenimports += collect_submodules('gradio_client')
hiddenimports += collect_submodules('groovy')

runtime_hooks = []

hook_code = """
import os
import sys

os.environ['GRADIO_SKIP_PYI_GENERATION'] = 'True'

if 'gradio.component_meta' in sys.modules:
    mod = sys.modules['gradio.component_meta']
    if hasattr(mod, 'create_or_modify_pyi'):
        mod.create_or_modify_pyi = lambda *a, **k: None
"""

print("Gradio hook loaded: Disabled pyi generation and collected all files.")