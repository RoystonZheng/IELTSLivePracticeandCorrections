# 雅思当季考情来源与本地练习

给中国大陆考生用的本地雅思资料索引与练习系统。克隆仓库后，公开题库页可查看最近一次提交的当季听、说、读、写来源记录。主页保留四科模考入口；各科页选择整套或 Part / Section 后，只显示有完整内容、出现证据和公开分发权的题组。**目前没有这样的完整当季题组，因此模考入口显示暂无可作答题目。**更新器只检索并保存简短来源记录和链接，不编造、改写或自动生成试题。自己的、有权使用的 PDF 试卷可导入本地作答。可选的本机 Codex CLI 只用于用户主动请求的练习反馈。

## 这个项目的优势

- **当期资料会继续更新。** GitHub Actions 安排每天北京时间 08:00 检查公开来源，并在 08:17 备用重试；有变化才提交目录。本地服务启动时也会检查，保持运行后每天再检查。跨到新的四个月资料期，当前目录按新期资料重建。`git clone` 或 `git pull` 可以取得仓库最近一次已提交的目录。
- **每条记录说明证据。** 写作记录附来源标注的考试日期、考点和原网页；口语话题标注来源所称的中国大陆范围。当前听读只有一篇明确涉及这两科的考后文章入口，具体场次、考点和 Part 尚未核实。标题可能是话题摘要，不等同于完整原题。
- **自己的 PDF 可以变成题目。** 上传带文字层的试卷，系统提取题干和选项；先核对、修改，再保存为可作答的个人练习。填入标准答案后，导入的阅读和听力题可以自动核对、筛选错题。这比只把 PDF 当作阅读文件多了一步实际做题和复盘。
- **没接 AI 也能练习自己的试卷。** 导入有权使用的阅读、听力 PDF 和答案后，可以作答、核对、订正并查看记录。当前公开来源没有可打包的完整试卷时，系统不会拿自编题填充模考入口。
- **阅读和听力可以直接标注。** 在导入的听读 PDF 练习中，选中一段文字或双击单词，会显示黄色、绿色、粉色高光选项与选词笔记。单击已有标注会打开操作菜单，再选择取消或删除。右侧“全部笔记”窗口可展开、收起和上下滚动。标注保存在当前浏览器。
- **AI 由每位使用者自己决定。** 本地运行时可接自己登录的 Codex CLI，获取写作与口语文字练习反馈，以及听读错题解释。仓库不保存共享密钥；不接 CLI，题目和客观题核对照常使用。

### 和相似开源工具怎么比

以下按这些项目在 2026-10-27 的 README 公开说明比较使用场景，不代表对它们全部代码的审计。

| 项目 | README 侧重 | 本项目更适合的需求 |
| --- | --- | --- |
| [BandReady](https://github.com/Luxshan2000/ielts-prep) | 四科离线练习、实时 AI 口语考官 | 跟踪按资料期更新的公开来源，再把自己手头的文字版 PDF 提取为可编辑练习 |
| [IELTS-Study](https://github.com/iFralex/IELTS-Study) | 内置听读写练习、整套模考和学习分析 | 想查看持续更新的大陆相关考情入口，同时练习个人 PDF 试卷 |
| [easyIELTS](https://github.com/thinkall/easyIELTS) | 四科练习、AI 生成题目和私有 PDF 阅读库 | 想从自己的 PDF 直接提取题目、核对答案后作答，并使用当期资料链接目录 |

公开考后资料在仓库中是**带证据的来源目录**，不是未经授权转载的试卷。第三方题目、音频和答案需到原站查看。PDF 转题只处理使用者自行上传的文件。本项目不是雅思官方题库，也无法证明覆盖全国每个考点。站内“当季题组”只有在取得可分发的真实题目材料并核对来源后才会上架；没有就显示为空。

## 使用

```bash
git clone https://github.com/RoystonZheng/IELTSLivePracticeandCorrections.git ielts-practice-desk
cd ielts-practice-desk
python3 bank_update.py --serve
```

打开终端提示的 `http://127.0.0.1:8766/app/index.html`。启动时会立即联网更新；保持这个命令运行，每天北京时间 08:00 起再检查一次。页面打开期间会定期读取更新后的目录。网络失败时会保留**同一资料期**已经收录的记录。只想更新文件时运行 `python3 bank_update.py --once`；不联网时可以直接打开 `app/index.html`，使用仓库内最近一次提交的目录。需要可选的本机评分时必须用 `bank_update.py --serve` 启动；直接打开 HTML 文件或使用普通静态服务器只会显示无 AI 模式。

## 可选 Codex CLI 反馈

这项功能由**每个使用者自己的电脑**提供，不依赖仓库作者的 CLI 或账号。按 [OpenAI 的 Codex CLI 安装说明](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)安装较新版本，例如 `npm install -g @openai/codex@latest`，然后在同一台电脑运行 `codex login` 和 `codex login status`。确认已登录后启动 `python3 bank_update.py --serve`。页面会显示是否连上本机 CLI。若 CLI 不在 `PATH`，启动服务前可以设置 `IELTS_CODEX_BIN` 为其可执行文件的绝对路径；设置 `IELTS_CODEX_ENABLED=0` 可关闭 AI 功能。

题库更新**不会调用 AI**。只有用户主动点击“获取 AI 练习评分”或“用 Codex 解释这道错题”等按钮，才会使用本机 CLI。导入有权使用的 PDF 后可作答；听读题需要填入答案才能自动核对。没有 CLI 时，已导入题目的客观题核对照常使用。评分使用本机 Codex CLI 的登录态，不在仓库保存密钥；生成反馈会使用登录账户的模型额度，作答文字会发送给对应模型服务。

阅读/听力的客观题由本地答案核对；AI 可以进一步解释错题。写作的四项维度和总分是练习估计，不是雅思官方成绩。

口语支持两种入口：手动输入文字评分，或录音后点击“评分这段录音”。后者需要在**运行本地服务的那台电脑、同一个 Python 环境**额外安装转写组件。例如在 macOS/Linux 仓库目录运行 `python3 -m venv .venv`、`.venv/bin/python -m pip install -r requirements-speech.txt`，再用 `.venv/bin/python bank_update.py --serve` 启动；Windows 对应使用 `.venv\Scripts\python.exe`。首次使用会下载 `base.en` 本地语音模型；可以通过 `IELTS_WHISPER_MODEL` 指定其他 faster-whisper 模型或本地模型目录。浏览器把本次录音发给同源的本地服务，本地模型生成英文转写、时长、语速和近似停顿次数；Codex CLI 收到这些文字和节奏数据后给出流利度与连贯性、词汇、语法的**部分练习估计**。原始音频只供本地转写，不发送给 Codex。模型并未听到原音，**发音维度不评分**，整体估计也不是正式口语总分。转写可能有误，节奏数据仅供参考。录音及其反馈刷新页面后消失；手动文字作答和文字 AI 反馈保存在当前浏览器。未安装本地转写组件时，仍可录音回放和使用文字评分。

GitHub Actions 设置了每天北京时间 08:00 和 08:17 两个检查时点；第二次用于补上整点任务可能被 GitHub 延迟或跳过的情况。同一天重复执行不会重复提交相同目录。GitHub 的定时触发仍可能延迟或缺席，请在 [Actions 运行记录](https://github.com/RoystonZheng/IELTSLivePracticeandCorrections/actions/workflows/update-bank.yml)确认当天确实有运行记录；没有记录时可手动运行 **Update current IELTS source index**。有变化的目录会提交到 `main`。克隆者打开网页就能看到最近一次提交的记录；以后要取得仓库的新提交，仍需 `git pull`。本地更新不会自动推回 GitHub。

你也可以每天自己运行并发布：

```bash
python3 bank_update.py --once
python3 app/scripts/check_data.py
git add -A -- app/data/public-index.json app/bank.js app/data/season-content.json app/season-content.js app/audio/season question-bank/current
git commit -m "Update current IELTS source records"
git push origin main
```

没有变化时，`git commit` 会提示无可提交内容。更新命令只收录来源记录，不会下载第三方完整试卷。

## 资料期与换期

本系统用 **1—4 月、5—8 月、9—12 月**三个四个月区间管理链接。跨到新区间时，`question-bank/current/` 和应用中的当前目录会用**新区间数据重建**，旧期资料不再出现在当前目录；如果新期的源站暂时没有资料，当前目录会显示为空，不会把上期内容冒充新题。仓库的 Git 历史仍保留旧提交，可供追溯。

换期时，程序会清空上期当季题组和相关音频，并重建当前来源目录。如果新区间尚无可核实的记录，就保持为空；不会沿用旧季题目，也不会自动写出模拟题。仓库 Git 历史仍保留旧提交。

这只是本项目的归档规则，**不是**听力、阅读、写作有官方固定换题日的声明。每天新增的考后资料按实际可公开查到的内容更新，未来月份不会提前列为考后真题。

## 当前目录和来源

- [`question-bank/current/`](question-bank/current/)：本期各科 CSV 和 `manifest.json`；`app/data/public-index.json` 是网页读取的同一索引。
- [当季站内题组数据](app/data/season-content.json)：目前为空；此前按话题自编和自动生成的当季题组、音频已移除。只有取得可分发的来源题并核对出现记录后才会收录。
- [官方免费练习入口](question-bank/official-free-practice.md)：不属于当期考后回忆。
- [网页入口](app/index.html)：主页四科模考入口、各科 Part / Section 选择、公开题库四科页内切换、练习记录四科页内切换。旧版原创练习数据暂保留以便查看已有历史记录，不在当前模考入口展示。

更新程序读取日期和考点标注的写作话题、口语话题目录，以及国内机构的考情文章。明确标有听读的考后文章会出现在对应科目的索引中；文章不是完整题目。每条链接标明来源和地域证据：`site_reported_venue` 表示考点是第三方网站自述，文章类线索需回原文确认。**这些条目不能拼接成一套中国考场原卷，也不能保证覆盖所有城市或场次。** 来源短时失败、未发布月份和未来月份会在网页及 `manifest.json` 中显示。

来源目录目前接入 [雅圈写作日期目录](https://www.yaquan.site/ielts/writing)、[AI IELTS Mentor 考后文章](https://aiieltsmentor.com/jijing.html)、[新航道考情目录](https://cq.xhd.cn/ielts/ysjj/)、[托你的福周度考情目录](https://tuonidefu.com.cn/blogs)、[Joe Speaking 大陆口语话题目录](https://joespeaking.com/zh-CN/ielts-speaking-questions/2026-sep-dec)，口语主站不可用时使用 [ZipIELTS 话题目录](https://www.zipielts.com/library)；官网样题见[雅思中文官网](https://www.chinaielts.org/prepare/ielts-practice-tests/mocks-academic)。以前接入的 IELTS Actual Tests 在[使用条款](https://ieltsactualtests.com/terms-of-service)中明确禁止批量抓取和再分发，已移除自动采集及其条目。第三方链接可能失效或更正，详情以源站为准。

## 导入自己的 PDF 试卷

用本地服务启动项目后，先安装 PDF 解析依赖：

```bash
python3 -m pip install -r requirements-pdf.txt
python3 bank_update.py --serve
```

在网页右上角选择「导入 PDF」，选阅读、听力、写作或口语，再上传自己有权使用的 PDF。阅读、写作、口语可以一次选多份 PDF；单份中的多篇阅读、多个写作 Task 或口语 Part 会分组展示，同组内的重复题号需要在预览中核对。听力每次只选一份 PDF，必须同时选择对应音频（最多 100 MB）；音频保存在当前浏览器，并在练习页播放。系统提取文字和带题号的题目，展示可编辑的分组、题干、选项、标准答案与原文。核对后保存到**当前浏览器**，即可作答；有标准答案的听力和阅读题可自动核对并筛选错题。没有答案的题目只保存作答；写作和口语不会靠文字精确匹配给出分数。

目前支持**带可复制文字的 PDF**，单份最多 20 MB、80 页。扫描版请先做 OCR；图片、表格、双栏顺序、配对题和复杂题型可能无法完整还原，务必对照原 PDF 检查。PDF 原文件只在本机服务内存中解析，不写入仓库；解析后的原文与练习记录保存在当前浏览器，最多 5 份。导入音频不会自动生成逐句回放。

## 检查和扩展

运行以下命令检查本期索引、换期状态和原有练习数据：

```bash
python3 app/scripts/check_data.py
python3 -m unittest discover -s tests -v
node --test tests/test_annotations.js
```

更新和解析代码在 [`bank_update.py`](bank_update.py)；要接入新的公开目录，可添加解析函数并在 `collect()` 中调用 `run_source()`。不要把未经许可的第三方完整试卷、录音或答案提交到仓库。

如果在 macOS 上修改原创听力文字稿，可以运行 `python3 app/scripts/build_listening.py` 重新生成完整录音和逐句音频，然后运行 `python3 app/scripts/build_bundle.py` 重建浏览器数据包。其他系统克隆仓库后直接播放已提交的音频，无须运行 macOS 合成脚本。
