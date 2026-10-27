# 雅思听力、阅读、写作练习与当期资料索引

面向中国大陆考生的独立练习系统。仓库包含可离线使用的原创听力、阅读、写作练习，以及联网更新的公开考后回忆和重建练习**链接目录**。第三方试题正文、音频和答案仍在原网站，本仓库只保存来源、日期、简短标题和链接。它不是雅思官方题库，也无法证明收录了全国每个考点的试卷。

## 使用

```bash
git clone https://github.com/RoystonZheng/-.git ielts-practice-desk
cd ielts-practice-desk
python3 bank_update.py --serve
```

打开终端提示的 `http://127.0.0.1:8766/app/index.html`。启动时会立即联网更新；保持这个命令运行，每天北京时间 08:00 起再检查一次。网络失败时会保留**同一资料期**已经收录的链接。只想更新文件时运行 `python3 bank_update.py --once`；不联网时可以直接打开 `app/index.html`，使用仓库内最近一次提交的目录和原创练习。

GitHub Actions 每天北京时间 08:00 运行更新程序并把有变化的目录提交到 `main`。因此正常 `git clone` 或 `git pull` 会拿到仓库最近一次公开更新；Git 本身不会在拉取时执行程序。也可以在 GitHub 的 Actions 页面手动运行 **Update current IELTS source index**。本地更新不会自动推回 GitHub。

## 资料期与换期

本系统用 **1—4 月、5—8 月、9—12 月**三个四个月区间管理链接。跨到新区间时，`question-bank/current/` 和应用中的当前目录会用**新区间数据重建**，旧期资料不再出现在当前目录；如果新期的源站暂时没有资料，当前目录会显示为空，不会把上期内容冒充新题。仓库的 Git 历史仍保留旧提交，可供追溯。

这只是本项目的归档规则，**不是**听力、阅读、写作有官方固定换题日的声明。每天新增的考后资料按实际可公开查到的内容更新，未来月份不会提前列为考后真题。

## 当前目录和来源

- [`question-bank/current/`](question-bank/current/)：本期各科 CSV 和 `manifest.json`；`app/data/public-index.json` 是网页读取的同一索引。
- [官方免费练习入口](question-bank/official-free-practice.md)：不属于当期考后回忆。
- [原创阅读、听力、写作练习](app/index.html)：阅读 3 篇、40 题；听力 4 个原创合成音频场景、40 题；写作 Task 1 / Task 2。作答保存在本机浏览器，写作由用户自评。

更新程序读取公开的月度听读重建练习、日期和考点标注的写作话题，以及国内机构的考情文章。每条链接标明来源和地域证据：`global_unattributed` 表示没有核验国内考点，`site_reported_venue` 表示考点是第三方网站自述，文章类线索需回原文确认。**这些条目不能拼接成一套中国考场原卷，也不能保证覆盖所有城市或场次。** 来源短时失败、未发布月份和未来月份会在网页及 `manifest.json` 中显示。

来源目录目前接入 [IELTS Actual Tests 月度回忆](https://ieltsactualtests.com/recalls/2026-10)、[雅圈写作日期目录](https://www.yaquan.site/ielts/writing)、[AI IELTS Mentor 考后文章](https://aiieltsmentor.com/jijing.html)、[新航道考情目录](https://cq.xhd.cn/ielts/ysjj/)、[托你的福周度考情目录](https://tuonidefu.com.cn/blogs)；官网样题见[雅思中文官网](https://www.chinaielts.org/prepare/ielts-practice-tests/mocks-academic)。第三方链接可能失效或更正，详情以源站为准。

## 检查和扩展

运行以下命令检查本期索引和原创练习数据：

```bash
python3 app/scripts/check_data.py
python3 -m unittest discover -s tests -v
```

更新和解析代码在 [`bank_update.py`](bank_update.py)；要接入新的公开目录，可添加解析函数并在 `collect()` 中调用 `run_source()`。不要把未经许可的第三方完整试卷、录音或答案提交到仓库。
