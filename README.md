# 雅思听说读写练习与当期资料索引

面向中国大陆考生的独立练习系统。仓库包含可离线使用的原创听力、阅读、写作练习、逐句听力音频，以及联网更新的口语话题和考后回忆**链接目录**。第三方试题正文、音频和答案仍在原网站，本仓库只保存来源、日期、简短标题和链接。它不是雅思官方题库，也无法证明收录了全国每个考点的试卷。

## 使用

```bash
git clone https://github.com/RoystonZheng/-.git ielts-practice-desk
cd ielts-practice-desk
python3 bank_update.py --serve
```

打开终端提示的 `http://127.0.0.1:8766/app/index.html`。启动时会立即联网更新；保持这个命令运行，每天北京时间 08:00 起再检查一次。网络失败时会保留**同一资料期**已经收录的链接。只想更新文件时运行 `python3 bank_update.py --once`；不联网时可以直接打开 `app/index.html`，使用仓库内最近一次提交的目录和原创练习。需要 AI 反馈时必须用 `bank_update.py --serve` 启动；直接打开 HTML 文件或使用普通静态服务器只会显示无 AI 模式。

## 可选 Codex CLI 反馈

这项功能由**每个使用者自己的电脑**提供，不依赖仓库作者的 CLI 或账号。按 [OpenAI 的 Codex CLI 安装说明](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)安装较新版本，例如 `npm install -g @openai/codex@latest`，然后在同一台电脑运行 `codex login` 和 `codex login status`。确认已登录后启动 `python3 bank_update.py --serve`。页面会显示是否连上本机 CLI。若 CLI 不在 `PATH`，启动服务前可以设置 `IELTS_CODEX_BIN` 为其可执行文件的绝对路径；设置 `IELTS_CODEX_ENABLED=0` 可关闭 AI 功能。

AI 调用只会在用户点击“获取 AI 练习评分”或“用 AI 解释这道错题”时发生。阅读和听力的 **40 题原始正确数、错题筛选、修正栏、听力逐句播放**始终可用。写作和口语没有 CLI 时不提供 AI 评分，但依然可以写作、修订、练口语、录音回放和保存文字。评分使用本机 Codex CLI 的登录态，不在仓库保存密钥；请求只从同源本地页面发往本机服务。生成 AI 反馈会使用登录账户的模型额度，作答文字会发送给对应模型服务。

阅读/听力的客观题由本地答案核对；AI 可以进一步解释错题。写作的四项维度和总分是练习估计，不是雅思官方成绩。口语 AI **只看手动输入的作答文字**；录音留在浏览器本地，仅供回放，不上传给 CLI。因此口语文本反馈不能评估发音、真实停顿和完整流利度，也不是正式口语总分。录音刷新页面后消失；文字作答和 AI 反馈保存在当前浏览器。

GitHub Actions 每天北京时间 08:00 运行更新程序并把有变化的目录提交到 `main`。因此正常 `git clone` 或 `git pull` 会拿到仓库最近一次公开更新；Git 本身不会在拉取时执行程序。也可以在 GitHub 的 Actions 页面手动运行 **Update current IELTS source index**。本地更新不会自动推回 GitHub。

## 资料期与换期

本系统用 **1—4 月、5—8 月、9—12 月**三个四个月区间管理链接。跨到新区间时，`question-bank/current/` 和应用中的当前目录会用**新区间数据重建**，旧期资料不再出现在当前目录；如果新期的源站暂时没有资料，当前目录会显示为空，不会把上期内容冒充新题。仓库的 Git 历史仍保留旧提交，可供追溯。

这只是本项目的归档规则，**不是**听力、阅读、写作有官方固定换题日的声明。每天新增的考后资料按实际可公开查到的内容更新，未来月份不会提前列为考后真题。

## 当前目录和来源

- [`question-bank/current/`](question-bank/current/)：本期各科 CSV 和 `manifest.json`；`app/data/public-index.json` 是网页读取的同一索引。
- [官方免费练习入口](question-bank/official-free-practice.md)：不属于当期考后回忆。
- [原创听说读写练习](app/index.html)：阅读 3 篇、40 题；听力 4 个原创合成音频场景、40 题，提交后可逐句回听；写作 Task 1 / Task 2；口语目录话题练习。作答保存在本机浏览器。

更新程序读取公开的月度听读重建练习、日期和考点标注的写作话题，以及国内机构的考情文章。每条链接标明来源和地域证据：`global_unattributed` 表示没有核验国内考点，`site_reported_venue` 表示考点是第三方网站自述，文章类线索需回原文确认。**这些条目不能拼接成一套中国考场原卷，也不能保证覆盖所有城市或场次。** 来源短时失败、未发布月份和未来月份会在网页及 `manifest.json` 中显示。

来源目录目前接入 [IELTS Actual Tests 月度回忆](https://ieltsactualtests.com/recalls/2026-10)、[雅圈写作日期目录](https://www.yaquan.site/ielts/writing)、[AI IELTS Mentor 考后文章](https://aiieltsmentor.com/jijing.html)、[新航道考情目录](https://cq.xhd.cn/ielts/ysjj/)、[托你的福周度考情目录](https://tuonidefu.com.cn/blogs)、[Joe Speaking 大陆口语话题目录](https://joespeaking.com/zh-CN/ielts-speaking-questions/2026-sep-dec)，口语主站不可用时使用 [ZipIELTS 话题目录](https://www.zipielts.com/library)；官网样题见[雅思中文官网](https://www.chinaielts.org/prepare/ielts-practice-tests/mocks-academic)。第三方链接可能失效或更正，详情以源站为准。

## 检查和扩展

运行以下命令检查本期索引和原创练习数据：

```bash
python3 app/scripts/check_data.py
python3 -m unittest discover -s tests -v
```

更新和解析代码在 [`bank_update.py`](bank_update.py)；要接入新的公开目录，可添加解析函数并在 `collect()` 中调用 `run_source()`。不要把未经许可的第三方完整试卷、录音或答案提交到仓库。

如果在 macOS 上修改原创听力文字稿，可以运行 `python3 app/scripts/build_listening.py` 重新生成完整录音和逐句音频，然后运行 `python3 app/scripts/build_bundle.py` 重建浏览器数据包。其他系统克隆仓库后直接播放已提交的音频，无须运行 macOS 合成脚本。
