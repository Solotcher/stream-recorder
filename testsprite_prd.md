# Stream Recorder - Product Requirements Document (PRD)

본 문서는 Stream Recorder 프로젝트의 워크로그(Phase 1 ~ Phase 8)를 기반으로 TestSprite 자동화 테스트를 위해 작성된 표준 PRD입니다.

## 1. 프로젝트 개요 (Product Overview)
Stream Recorder는 4개 주요 인터넷 방송 플랫폼(치지직, SOOP, 트위치, 유튜브)의 실시간 스트리밍을 감지하고 자동으로 녹화하는 크로스 플랫폼(Windows/Linux) 백그라운드 레코딩 서비스입니다. Python(FastAPI) 백엔드와 Vanilla JS 기반의 프론트엔드(SPA)로 구성되어 있으며, Streamlink와 yt-dlp 엔진을 활용해 녹화를 수행합니다.

## 2. 주요 기능 요구사항 (Core Functional Requirements)

### 2.1 다중 플랫폼 실시간 녹화 모니터링
- **대상 플랫폼**: 치지직(Chzzk), 숲(SOOP), 트위치(Twitch), 유튜브 라이브(YouTube Live).
- **자동 감지**: APScheduler를 통해 예약된 채널의 라이브 여부를 모니터링하여 방송 시작 즉시 녹화(RecorderManager)를 실행합니다.
- **메타데이터 파싱**: 채널명, 방송제목, 방송 카테고리, 해상도를 추출하여 UI 및 파일 시스템에 반영합니다.

### 2.2 후처리 및 파일 생성 로직
- **파일명 동적 생성**: `{date}_{streamer}_{title}_{quality}` 패턴 등 사용자가 지정한 형식으로 동적 MP4/TS 파일명을 생성합니다.
- **영상 리먹싱 및 병합**: 
  - 녹화 종료 후 `.ts` 파일을 `.mp4` 형식으로 자동 리먹싱(faststart)합니다.
  - SOOP (아프리카TV) 환경 등에서 발생하는 세션 끊김으로 인한 분할 파일을 `ffmpeg concat`으로 자동 병합하고 자투리 파일을 제거합니다.
- **파일 무결성 검증**: 리먹싱, 병합 후 산출물 용량(최소 1KB)을 검증하여 이상 생성 시 원본 파일의 훼손을 방지합니다.

### 2.3 프론트엔드 SPA 및 수동 컨트롤
- **단일 페이지 애플리케이션(SPA)**: 실시간 녹화 현황 관리, 수동 즉시 녹화, 예약/설정 관리 뷰로 분리된 시스템을 제공합니다.
- **수동 녹화 및 관리 접근**: 브라우저 URL 복사 시 자동 플랫폼 파싱, 일회성 비밀번호 방 비밀번호 동적 주입을 지원합니다.
- **실시간 소켓 연동**: WebSocket(Event Bus)을 통하여 채널 갱신 시 녹화(런타임) 진행 상태, 품질 및 UI 데이터의 실시간 동기화를 구축합니다.

### 2.4 부가 및 안정화 서비스
- **텔레그램 알림**: 시스템 에러, 녹화 시작 및 정상 종료 시 Telegram 봇을 통해 사용자에게 푸시 알림을 발송합니다.
- **클라우드 자동 업로드**: 병합 및 모든 처리가 완료된 영상 자산을 `uploader.py` 모듈을 통해 rclone (Google Drive 등 클라우드 스토리지 시스템)으로 자동 업로드합니다.
- **자동 환경 구축**: 구동 시 `dependency_manager.py` 모듈이 FFmpeg, yt-dlp 등 서드파티 바이너리의 유무를 자동 스캔하여, 부족할 시 GitHub 등으로부터 알맞은 패키지를 다운로드해 세팅합니다.
- **프로세스 무중단 재부착**: 서버 재시작 등 상황 발생 시, 프로세스 라이프사이클(`psutil` 기반) 상태 목록과 `active_pids.json`을 바탕으로 구동 중이던 FFmpeg(Streamlink/yt-dlp) 세션의 권한을 복구(Re-attach)하여 중단을 원천 배제합니다.

## 3. UI, 데이터 및 인증 요구사항
- **쿠키 파서 연계 적용**: 클립보드 문자열(Netscape, JSON 포맷) 파싱을 통한 강력한 쿠키 적용 및 유지 시스템 적용. 각 플랫폼 컴포넌트 내에 쿠키 유효 상태를 의미하는 뱃지(Live Status)를 노출합니다.
- **유튜브 라이브 지원 추가**: yt-dlp 덤프 API 메타 데이터 조회 및 YouTube Extractor 모듈 병기.
- **환경 변수 UI 변경 제어기**: `.env` 설정값(Output Directory 제반 제어, 해상도 선택)을 런타임 및 SPA 다이얼로그 모달을 통해 변경할 수 있는 권한 제공.

## 4. 아키텍처 및 에러 핸들링
- **외부 I/O 비동기 프로세스 처리**: 멀티 스레드(`subprocess.Popen` + `asyncio.to_thread`) 백그라운드 워커를 도입하여 메인 프로세스(이벤트 루프)의 파이프라인 블로킹 우회 및 비동기 안정성을 확보하였습니다.
- **보안/감사 최적화**: 텔레그램 토큰 로깅 및 설정 파일 데이터 반환 시 마스킹 제어, 웹 UI 로드 시 CORS 이슈 방지(단일 오리진 제어), 포트(8000, 51820 VPN 관련) 등 보안 지침 사항이 적용되어 있습니다.

## 5. TestSprite 대상 테스트 픽스처(Fixture) 가이드
자동화된 QA 및 TestSprite 테스트를 위한 중점 점검 픽스처 항목입니다:
1. **Extractor 모듈 검증**: 4개의 플랫폼 Extractors(수집기 모듈)가 API 또는 HTML 파싱을 통해 추출하는 JSON 데이터 구조의 정확도와 Live Status를 정상적으로 True/False로 식별하는지를 Mocking 테스트합니다.
2. **Subprocess 구동 체계(Recorder/Merger) 유효성**: Streamlink, yt-dlp 커맨드 조립식 명령어가 적절히 실행되며 ffmpeg 리먹싱/병합 커맨드 또한 에러 없이 구동 및 무결성 검증 로직으로 전달되는지(Dummy File을 거점 삼아) 검증이 요구됩니다.
3. **Scheduler 파이프라인 무결성**: 1분 주기 APScheduler 타이머 루프, 설정 데이터 연동 조회 및 RecorderManager 정상 트리거, `active_pids.json` 을 통한 프로세스 재부착 알고리즘 순환이 요구사항대로 동작하는가 확인이 필요합니다.
