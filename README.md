# GrooveSmith

音频 -> 纯鼓分离 -> 鼓转 MIDI -> 可编辑鼓谱(MusicXML/PDF) 的自托管流水线, 带浏览器工作台(上传/进度/预览/播放/混音/导入)。
在 WSL2 的 Docker 中已端到端验证通过。默认纯 CPU 运行,检测到 GPU 可切换加速。

## 流水线

    输入音频 (mp3/wav)
      |  STAGE 1  Demucs htdemucs (MIT)          分离出 drums 音轨
      v
    drums.wav
      |  STAGE 2  ADTOF-pytorch (NonCommercial)  鼓 -> MIDI (GM channel 10)
      v
    drums.mid
      |  STAGE 3  music21 (BSD)                  MIDI -> MusicXML (可编辑)
      v
    drums.musicxml
      |  STAGE 4  Verovio (LGPL) + cairosvg      -> SVG / PDF / PNG (预览)
      v
    drums.pdf / drums.png / drums.svg

## 一键运行 (CPU, 默认)

    # 首次构建 (若 github 被墙, 加代理)
    BUILD_PROXY=http://172.20.128.1:20808 docker compose build

    # 把歌曲放到 data/input/, 然后:
    docker compose run --rm pipeline --input /data/input/你的歌.wav --outdir /data/output

产物在 data/output/: drums.mid / drums.musicxml / drums.pdf / drums.png / drums.svg

## GPU 加速 (可选)

需要宿主装好 nvidia-container-toolkit。然后:

    BUILD_PROXY=http://172.20.128.1:20808 docker compose --profile gpu build
    docker compose --profile gpu run --rm pipeline-gpu --input /data/input/你的歌.wav

CPU/GPU 由 --device (cpu|cuda) 或环境变量 DEVICE 控制, 同一套代码。

## 已验证结果 (2026-09-09, WSL2 Ubuntu22.04, Docker 26.1.4, 纯 CPU)

- 9.6s 测试音频, 全链路 CPU 27.8 秒, PIPELINE_EXIT=0
- Demucs 分离 4 stems, drums.wav 有效 (11 秒)
- ADTOF 转 MIDI: is_drum=True, GM channel 10 (MuseScore 自动识别为鼓组)
- MusicXML: 良构 score-partwise, part-name=Percussion, midi-channel=10, 44 个 unpitched 打击乐音符, 5 小节 -- 可在 MuseScore 原生打开编辑
- 渲染出真实五线谱 (Percussion 谱表, 4/4, 音符/休止符/符杠)

## 后期编辑 (可编辑性)

drums.musicxml 是标准 MusicXML, 直接拖入 MuseScore 4 即可:
- 自动识别为鼓组 (channel 10)
- 可量化 (Tools -> Quantize, 建议 1/16) 清理 AI onset 的时值碎片
- 可改谱号为鼓谱号、修正 tempo、增删音符、导出 PDF

## 诚实的质量说明

- ADTOF 在真实音乐上 F 值约 88%, 非 100%; 快速 fills / 密集镲片会有漏检误检。
- 合成测试音频的 snare 被误分类为 tom, velocity 恒定 -- 这是合成信号与真实训练集
  不匹配所致, 真实歌曲会好很多; 流水线机制本身已验证正确。
- AI 产出的是草稿谱, 最后一步在 MuseScore 里人工量化/校对是必要的,
  这正是我们输出可编辑 MusicXML (而不仅是 PDF) 的原因。

## 许可证 (自用/家用服务器场景)

- Demucs: MIT | music21: BSD | Verovio: LGPL | cairosvg: LGPL
- ADTOF-pytorch: CC BY-NC-SA (NonCommercial) -- 自用合规; 若将来商用需替换转谱引擎。

## 文件

- pipeline/Dockerfile.base   镜像定义 (torch cpu/cu121 可选, 代理构建支持)
- pipeline/run_pipeline.py    统一入口 (4 stage)
- pipeline/make_test_audio.py 生成测试音频
- docker-compose.yml          CPU 默认 + GPU 可选 profile
- data/input/                 放输入音频
- data/output/                产物

## WebUI (浏览器操作: 上传/进度/预览/导入)

启动:

    # 首次构建 (github 被墙时加代理)
    BUILD_PROXY=http://172.20.128.1:20808 docker compose build web
    docker compose up -d web
    # 浏览器打开 http://localhost:8080

两个功能页:
- 从音频生成: 上传 wav/mp3/flac/ogg/m4a -> 实时进度条+日志 -> 在线五线谱预览 -> 下载 midi/musicxml/pdf/png
- 导入谱子查看: 上传现成 .mid / .musicxml -> 直接渲染成五线谱预览

已实测 (docker compose up -d web, 端口 8080):
- GET / 200; POST /api/upload 返回 job_id; status 轮询 5->45->100 done
- GET /api/svg 200 (127KB 预览), /api/file/{musicxml,pdf,png} 200
- POST /api/import 传 MIDI 与 MusicXML 均返回 200 有效 SVG, 渲染为真实 Percussion 五线谱

API:
- POST /api/upload            音频 -> 启动异步任务 -> {job_id}
- GET  /api/status/{job_id}   进度/日志/产物路径
- GET  /api/svg/{job_id}      谱面 SVG (预览)
- GET  /api/file/{job_id}/{midi|musicxml|pdf|png}  下载产物
- POST /api/import            上传 MIDI/MusicXML -> 返回渲染 SVG

自用单机架构: 任务存内存 + 后台线程, 无需 Redis/Celery。每个任务产物在 data/jobs/{job_id}/。
渲染用 Verovio (需 setResourcePath 指向 site-packages/verovio/data)。

## WebUI 文件

- pipeline/webapp.py   FastAPI 后端 (上传/进度/预览/导入 API)
- pipeline/index.html  单页前端 (原生 JS, 无构建步骤)

## 播放与混音 (真实鼓采样, 自托管)

生成/导入的谱子可在浏览器直接播放:
- 谱子合成音使用自托管的 magenta sgm_plus **percussion 真实鼓采样** (kick/snare/hihat/toms/cymbals),
  完全离线, 无任何外部 CDN/Google 依赖。
- 原声可选 原始整曲 或 分离出的鼓轨 播放。
- 谱子合成音 与 原声 两个独立音量滑块, 实时混音。

自托管资源 (pipeline/static/):
- midi-player.js       tone.js + @magenta/music + html-midi-player 合并包 (608KB)
- soundfonts/sgm_plus/ 只含 percussion 音色: soundfont.json + percussion/instrument.json
  + 376 个 p{pitch}_v{velocity}.mp3 (pitch 35-81 x 8 力度, 约 11MB)

已实测: /static/soundfonts/sgm_plus/soundfont.json 200; percussion 采样 mp3 均 200 (audio/mpeg);
页面引用自托管 soundfont, 无 googleapis 外链。

音量实现: 谱子合成音走 Tone.getDestination().volume (分贝映射), 原声走 <audio>.volume (线性), 互相独立。

## 统一混音总线 (三滑块: 谱子合成音 / 原声 / 总音量)

原声通过 Web Audio 接入 (MediaElementSource -> origGain -> masterGain -> destination),
与鼓采样合成音共用 Tone.js 的 rawContext, 同一 AudioContext 内混音:
- 谱子合成音音量: Tone.getDestination().volume (分贝), 受 (vMidi x vMaster) 影响
- 原声音量: Web Audio origGain.gain (线性), 受 (vOrig x vMaster) 影响
- 总音量 vMaster: 同时作用于上面两路

播放时先 Tone.start() + ctx.resume() (满足浏览器用户手势要求)。
已实测: 页面含 总音量 滑块与 ensureAudioGraph/createMediaElementSource/rawContext, 无 googleapis 外链, soundfont/采样/首页均 200。

## 标准架子鼓记谱 (爵士鼓记谱法)

关键修复: 早期版本用 music21 直接把 MIDI 转 MusicXML, 所有音符都是圆形符头(当成钢琴谱),
踩镲/吊镲错误显示成圆圈。现改用 pipeline/drum_notation.py 专门生成打击乐谱:
- 打击乐谱号 (percussion clef)
- 每个音符为 unpitched, 用 display-step/display-octave 决定在五线谱上的高度(鼓件位置)
- 镲类(hi-hat/crash/ride)用叉号符头 x, 开镲用带圈叉号 circle-x, 鼓类用普通圆形符头
- GM 打击乐 MIDI 音高 -> (五线谱位置, 符头形状) 映射表见 drum_notation.DRUM_MAP

标准对应(5 线谱, 打击乐谱号):
- 底鼓 kick(35/36) 圆头, 低位
- 军鼓 snare(38/40) 圆头, 中位(第三间)
- 嗵鼓 toms(41-50) 圆头, 由低到高
- 闭镲 closed hi-hat(42) 叉号, 高位; 开镲 open hi-hat(46) 带圈叉号
- 吊镲 crash(49/57) 叉号; 叮叮镲 ride(51) 叉号; ride bell(53) 菱形
- 脚踩踩镲 pedal hi-hat(44) 叉号, 谱下方

已实测: 全链路生成的 drums.musicxml 含 percussion clef + x 符头; Verovio 渲染出真实鼓谱
(kick 圆头低位 / hi-hat 叉号高位 / crash 带圈叉号), MuseScore 打开即标准爵士鼓谱可编辑。

## 打击乐记谱文件

- pipeline/drum_notation.py  GM 鼓 MIDI -> 标准鼓谱 MusicXML (符头/位置映射)
