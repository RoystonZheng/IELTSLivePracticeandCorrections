"""Embed app data so the local HTML also opens without a web server."""
from pathlib import Path
import json
APP=Path(__file__).resolve().parents[1]
bundle={name:json.loads((APP/'data'/file).read_text(encoding='utf-8')) for name,file in [('publicIndex','public-index.json'),('readingTest','demo-test.json'),('listeningTest','listening-test.json'),('writingTest','writing-test.json')]}
(APP/'bank.js').write_text('window.IELTS_BANK = '+json.dumps(bundle,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
print('bank.js',(APP/'bank.js').stat().st_size,'bytes')
