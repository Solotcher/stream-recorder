import os
from typing import Dict
from app.core.config import settings

def update_env_file(updates: Dict[str, str]):
    """
    주어진 딕셔너리를 기반으로 .env 파일을 업데이트합니다.
    기존 주석이나 다른 라인들은 최대한 보존합니다.
    """
    env_path = os.path.join(settings.BASE_DIR, ".env")
    
    # 기존 내용 읽기
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    updated_keys = set()
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
            
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    # 새롭게 추가된 키들 병합
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")
            
    # 파일 쓰기
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    # 메모리(settings 객체) 동기화
    for k, v in updates.items():
        if hasattr(settings, k):
            setattr(settings, k, v)
