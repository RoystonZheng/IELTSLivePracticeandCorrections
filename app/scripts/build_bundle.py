"""Embed app data so the local HTML also opens without a web server."""
from pathlib import Path
import json
import os
APP=Path(__file__).resolve().parents[1]
def write_bundle(path, text):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(text,encoding='utf-8')
    os.replace(temporary,path)
bundle={name:json.loads((APP/'data'/file).read_text(encoding='utf-8')) for name,file in [('publicIndex','public-index.json'),('readingTest','demo-test.json'),('listeningTest','listening-test.json'),('writingTest','writing-test.json')]}
write_bundle(APP/'bank.js','window.IELTS_BANK = '+json.dumps(bundle,ensure_ascii=False,separators=(',',':'))+';\n')
print('bank.js',(APP/'bank.js').stat().st_size,'bytes')
season_content=json.loads((APP/'data'/'season-content.json').read_text(encoding='utf-8'))
write_bundle(APP/'season-content.js','window.IELTS_SEASON_CONTENT = '+json.dumps(season_content,ensure_ascii=False,separators=(',',':'))+';\n')
print('season-content.js',(APP/'season-content.js').stat().st_size,'bytes')
