import asyncio
import os
import glob
import re
import shutil
from app.core.logger import logger
from app.core.config import settings
from app.utils.telegram_bot import send_telegram_message, send_error_alert

def resolve_ffmpeg_path() -> str:
    """
    FFmpeg 실행 파일 경로를 반환합니다.
    서버 시작 시 dependency_manager가 settings.FFMPEG_PATH를
    유효한 전체 경로로 갱신하므로 이를 우선 사용합니다.
    """
    configured = settings.FFMPEG_PATH
    
    # settings에 이미 절대 경로가 설정되어 있으면 바로 반환
    if os.path.isabs(configured) and os.path.isfile(configured):
        return configured
    
    # 혹시 모를 fallback
    found = shutil.which(configured)
    return found or configured

async def process_remuxing(input_path: str, channel_name: str):
    """
    녹화된 .ts 파일을 .mp4로 리먹싱(스트림 복사)합니다.
    FFmpeg -c copy를 사용하여 재인코딩 없이 빠르게 변환합니다.
    """
    if not os.path.exists(input_path):
        logger.error(f"Remuxing 파일 누락: {input_path}")
        return

    dirname = os.path.dirname(input_path)
    basename = os.path.basename(input_path)
    name_without_ext = os.path.splitext(basename)[0]
    
    # .ts → .mp4 변환 (리먹싱)
    mp4_path = os.path.join(dirname, f"{name_without_ext}.mp4")

    logger.info(f"[{channel_name}] Remuxing 시작 (.ts → .mp4): {input_path} -> {mp4_path}")
    
    cmd = [
        resolve_ffmpeg_path(),
        "-y", "-nostdin",
        "-i", input_path,
        "-c:v", "copy",
        "-c:a", "copy",
        "-movflags", "+faststart",
        mp4_path
    ]

    try:
        import subprocess
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        def _wait_proc():
            return proc.wait()
            
        returncode = await asyncio.to_thread(_wait_proc)

        if returncode == 0:
            logger.info(f"[{channel_name}] Remuxing 성공 (.mp4 생성). 원본 .ts 파일을 삭제합니다.")
            os.remove(input_path)
            await send_telegram_message(f"<b>{channel_name}</b> 파일 후처리(Remuxing) 완료. (.mp4)")
            
            # 클라우드 자동 업로드 트리거 연동
            from app.services.uploader import upload_file
            asyncio.create_task(upload_file(mp4_path, channel_name))
        else:
            logger.error(f"[{channel_name}] Remuxing 실패 (Return Code: {returncode})")
            await send_error_alert(channel_name, "FFmpeg Remuxing (.ts → .mp4)", f"Return Code: {returncode}")
            
    except Exception as e:
        logger.error(f"[{channel_name}] Remuxing 중 예외 발생: {str(e)}")
        await send_error_alert(channel_name, "FFmpeg Remuxing 예외", str(e))


async def process_soop_concat(chunks_dir: str, base_filename: str, channel_name: str):
    """
    SOOP(숲) 등 분할(Chunk) 다운로드된 .webm 또는 .ts 파일들을
    ffmpeg concat demuxer를 이용해 하나의 파일로 병합하는 전용 서비스.
    """
    import glob
    import os
    import asyncio
    
    logger.info(f"[{channel_name}] SOOP 조각 병합 검토 시작 (Target: {base_filename})")
    
    # base_filename 에 매칭되는 원본 파일들 찾기 (예: [260306_0900] 이름_soop_part*.webm)
    search_pattern = os.path.join(chunks_dir, f"{base_filename}_part*.*")
    parts = glob.glob(search_pattern)
    
    if not parts:
        logger.warning(f"[{channel_name}] 병합할 파일이 발견되지 않았습니다: {base_filename}")
        return
        
    # 파일 정렬 (part 숫자 기준)
    def extract_part_num(filepath):
        # ..._part1.webm 형식에서 숫자 추출
        basename = os.path.basename(filepath)
        import re
        match = re.search(r"_part(\d+)", basename)
        return int(match.group(1)) if match else 0
        
    parts.sort(key=extract_part_num)
    
    # 확장자 결정 (가장 첫번째 파일 기준)
    ext = os.path.splitext(parts[0])[1]
    final_output = os.path.join(chunks_dir, f"{base_filename}{ext}")
    
    # 파일이 1개 뿐이라면 리네임으로 종료
    if len(parts) == 1:
        logger.info(f"[{channel_name}] 병합 대상이 1개뿐이므로, 이름만 변경합니다.")
        os.rename(parts[0], final_output)
        await send_telegram_message(f"<b>{channel_name}</b> 단일 파일 처리 완료.")
        
        # 클라우드 자동 업로드 훅
        from app.services.uploader import upload_file
        asyncio.create_task(upload_file(final_output, channel_name))
        return
        
    # 파일이 2개 이상이면 concat 수행
    list_txt_path = os.path.join(chunks_dir, f"concat_list_{base_filename.replace(' ', '_')}.txt")
    try:
        with open(list_txt_path, "w", encoding="utf-8") as f:
            for filepath in parts:
                # ffmpeg 안전을 위해 백슬래시/따옴표 처리
                safe_path = filepath.replace('\\', '/')
                f.write(f"file '{safe_path}'\n")
                
        logger.info(f"[{channel_name}] 총 {len(parts)}개의 조각을 병합합니다.")
        
        cmd = [
            resolve_ffmpeg_path(),
            "-y", "-nostdin",
            "-f", "concat",
            "-safe", "0",
            "-i", list_txt_path,
            "-c", "copy",
            final_output
        ]
        
        import subprocess
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        def _wait_proc():
            return proc.wait()
            
        returncode = await asyncio.to_thread(_wait_proc)
        
        if returncode == 0:
            logger.info(f"[{channel_name}] 병합(Concat) 성공. 원본 및 리스트 파일 삭제")
            for filepath in parts:
                os.remove(filepath)
            os.remove(list_txt_path)
            
            # 최종 알림 전송
            file_size_mb = round(os.path.getsize(final_output) / (1024 * 1024), 1)
            msg = f"✅ <b>{channel_name}</b> 방송 녹화/병합이 완료되었습니다.\n- 총 {len(parts)}개 조각 병합됨\n- 파일 크기: {file_size_mb} MB"
            await send_telegram_message(msg)
            
            # 클라우드 자동 업로드 훅
            from app.services.uploader import upload_file
            asyncio.create_task(upload_file(final_output, channel_name))
        else:
            logger.error(f"[{channel_name}] 병합 실패 (Return Code: {returncode})")
            await send_telegram_message(f"❌ <b>{channel_name}</b> 병합 중 오류가 발생했습니다. 원본 청크 파일들을 유지합니다.")
            await send_error_alert(channel_name, "SOOP FFmpeg Concat (다중 병합)", f"Return Code: {returncode}")
            
    except Exception as e:
        logger.error(f"[{channel_name}] 병합 로직 에러: {e}")
        await send_error_alert(channel_name, "SOOP FFmpeg Concat 로직 내부 에러", str(e))
    finally:
        # 혹시 모를 list_txt_path 찌꺼기 삭제
        if os.path.exists(list_txt_path):
            try:
                os.remove(list_txt_path)
            except Exception:
                pass
