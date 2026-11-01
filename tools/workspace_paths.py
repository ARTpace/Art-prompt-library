"""采集维护使用仓库本地工作目录，不读取或修改 Art Canvas 用户数据。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def asset_data_dir():
    return str(ROOT / 'artifacts' / 'assets')
