"""Build an original, shortened four-section listening practice and local speech audio."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
AUDIO=APP/'audio'
AUDIO.mkdir(exist_ok=True)
sections=[
 {'id':'L1','title':'Community centre booking','kind':'Everyday conversation','transcript':'''Receptionist: Good morning, Riverside Community Centre. How can I help? Caller: I would like to book a room for a neighbourhood photography club. The booking should be in my surname, Morris. That is M O R R I S. Receptionist: Thank you. We have Thursday the fourteenth of June available. Would you like the morning or evening? Caller: Evening, please. Our members finish work quite late. Receptionist: The room is free from six thirty until eight thirty. Caller: That works. We expect twelve people, though perhaps one or two might be absent. Receptionist: For twelve, I recommend Studio B, which has a long table and twelve chairs. The large hall costs more and would be unnecessary. The fee for Studio B is twenty five pounds for the whole two-hour session. Caller: May I pay in cash when I arrive? Receptionist: We ask for payment by card when you confirm the booking online. Cash is no longer accepted for room bookings. Caller: Fine. Do people enter from the main road? Receptionist: Please use the side entrance on Garden Lane. The main entrance closes at six. Caller: We will show photographs, so do you have a projector? Receptionist: Yes, a projector is included, but please bring your own laptop. Caller: I will. I would also like to visit before the meeting. Receptionist: Our coordinator can show you the studio on Tuesday afternoon. She is away on Monday. Caller: Great. Please email the form, and I will pay by card this evening. Receptionist: I have your details. We will hold the room until tomorrow at noon.''',
  'questions':[
   ('text','The booking surname is ______.','Morris','The caller spells the surname Morris.'),
   ('text','The meeting is on 14 ______.','June','The receptionist says the fourteenth of June.'),
   ('text','The booking begins at ______.','6:30','The room is free from six thirty.'),
   ('text','The group expects ______ people.','12','The caller expects twelve people.'),
   ('text','The recommended room is Studio ______.','B','The receptionist recommends Studio B.'),
   ('text','The room fee is £______.','25','The fee is twenty five pounds.'),
   ('mcq','How must the caller pay?','B','The receptionist requires payment by card.',['A. In cash','B. By card','C. By bank cheque']),
   ('text','Visitors should use the entrance on ______ Lane.','Garden','The side entrance is on Garden Lane.'),
   ('mcq','Which item is provided by the centre?','A','A projector is included, but the caller brings a laptop.',['A. A projector','B. A laptop','C. A camera']),
   ('text','The coordinator can show the room on ______.','Tuesday','She is available on Tuesday afternoon.')
  ]},
 {'id':'L2','title':'Museum visitor information','kind':'Everyday monologue','transcript':'''Welcome to the Harbour Museum. I will give you a short introduction before you explore. The ticket desk is on the ground floor, immediately behind the glass doors. Please keep your ticket, because staff may ask to see it in the exhibition rooms. Our newest gallery, called Water and Maps, is in the east wing. It follows the changing coastline over two hundred years and includes maps drawn by local sailors. The café is in the courtyard, not inside the gallery. It serves sandwiches until three, and the outdoor tables are sheltered from rain. Researchers who wish to use the archive must make an appointment for the research room. That room is not open for casual visits. At eleven fifteen each morning, a conservator gives a short demonstration of how paper maps are repaired. The demonstration is free, but places are limited to twenty visitors. Children under eight must remain with an adult in every gallery. Older children may join our activities independently if their family stays on the site. Audio guides are available at the desk. There is no rental charge, but we ask for a five pound refundable deposit. Please return the device before you leave. Today's family workshop is about drawing wetland birds. It begins after lunch and all materials are provided. The workshop room is next to the café. If you are leaving after four, use the north gate. The doors by the ticket desk are closed then so that staff can prepare for the next day. You may photograph most displays without a flash. The exception is the temporary exhibition, where photography is not allowed. Thank you, and enjoy your visit.''',
  'questions':[
   ('text','The ticket desk is on the ______ floor.','ground','It is on the ground floor.'),
   ('text','The new gallery is in the ______ wing.','east','Water and Maps is in the east wing.'),
   ('text','The café is in the ______.','courtyard','The café is in the courtyard.'),
   ('mcq','Who can enter the research room?','C','Archive researchers need an appointment.',['A. Any visitor with a ticket','B. Only children','C. Researchers with an appointment']),
   ('text','The map repair demonstration starts at ______.','11:15','The talk is at eleven fifteen.'),
   ('text','Children under ______ must stay with an adult.','8','Children under eight need an adult.'),
   ('text','The refundable audio-guide deposit is £______.','5','The deposit is five pounds.'),
   ('text','The family workshop involves drawing wetland ______.','birds','Visitors will draw wetland birds.'),
   ('text','After four o’clock, visitors should leave by the ______ gate.','north','The north gate is used after four.'),
   ('mcq','Where is photography prohibited?','B','Photography is prohibited in the temporary exhibition.',['A. In every gallery','B. In the temporary exhibition','C. In the courtyard'])
  ]},
 {'id':'L3','title':'Urban tree research plan','kind':'Academic discussion','transcript':'''Maya: We need to finalise our project on street trees before Friday. Leo: I thought we were studying air pollution. Maya: We changed the question after speaking to our tutor. We will test whether tree shade reduces pavement temperature in summer. Leo: That is easier to measure. How many streets are we using? Maya: Six streets, selected from three neighbourhoods. Two streets in each neighbourhood gives us some variety without making the project too large. Leo: And we need sensors. Maya: Two temperature sensors on each street: one in shade and one in full sun. We should put them at the same height above the pavement. Leo: When do we take readings? Maya: At noon and at four in the afternoon, on three clear days. The later reading may show whether the pavement keeps heat. Leo: Should we record humidity too? Maya: Yes. It might explain some variation, even though temperature is our main outcome. Leo: The tutor also warned us to consider pavement type. Dark asphalt and pale stone may heat differently. Maya: We will record pavement type and compare similar surfaces when possible. Leo: The pilot readings were strange yesterday. Maya: One sensor battery failed, so the data stopped halfway through. We have replaced it and will repeat the pilot tomorrow. Leo: Where do we store the results? Maya: In a shared spreadsheet, with a column for the date and exact location. Photos can go in a separate folder. Leo: The presentation is next week, but when is the written plan due? Maya: Friday at five. Leo: Our conclusion should mention that six streets are a small sample. Maya: Exactly. If the early findings look promising, we can recommend a larger sample for a later study. We must not claim that our results represent the whole city.''',
  'questions':[
   ('mcq','What is the main research question?','B','They study whether tree shade reduces pavement temperature.',['A. Whether trees reduce noise','B. Whether shade reduces pavement temperature','C. Whether trees increase traffic']),
   ('text','The students will study ______ streets.','6','They choose six streets.'),
   ('text','They will use ______ temperature sensors on each street.','2','There will be one shaded and one sunny sensor.'),
   ('text','Readings will be taken at noon and at ______.','4','Maya specifies four in the afternoon.'),
   ('text','They will also record ______ as an additional variable.','humidity','Maya says to record humidity.'),
   ('text','They need to control for the type of ______.','pavement','Pavement type may affect heating.'),
   ('mcq','Why were the pilot readings incomplete?','A','A sensor battery failed.',['A. A battery failed','B. It rained','C. A street was closed']),
   ('text','They will keep the results in a shared ______.','spreadsheet','Maya specifies a shared spreadsheet.'),
   ('text','The written plan is due on ______.','Friday','Maya says Friday at five.'),
   ('mcq','What do they suggest for a later study?','C','They recommend a larger sample.',['A. Fewer readings','B. No control variables','C. A larger sample'])
  ]},
 {'id':'L4','title':'Conserving historic textiles','kind':'Academic monologue','transcript':'''Today I will describe how a museum conserves an old textile. The example is a small woven cloth from a coastal village. Laboratory examination showed that its main fibre is flax. That identification matters because different fibres respond differently to water and handling. The blue colour came from a plant dye, while a darker area near the edge contained traces of iron. We do not yet know whether the iron was part of the original design or arrived later. The textile is fragile, so the first treatment is not washing. Instead, the conservator uses a soft brush to remove loose surface dust under magnification. A pH test checks whether the cloth has become unusually acidic. The test uses a tiny sample from an existing damaged edge. If the cloth needs support, a fine piece of silk can be placed behind it. The support is sewn with widely spaced stitches so that future conservators can remove it. Once treated, the textile is stored at around fifty percent relative humidity. Sudden changes in moisture can make fibres expand and contract. For display, the recommended light level is no more than fifty lux. Stronger light may fade the remaining colour, even when a visitor notices no immediate change. Insects are another risk. A newly acquired textile may be sealed and frozen before it joins the main collection, because freezing can kill many pests without applying chemicals directly to the cloth. Finally, every step is documented with photographs and written notes. The record includes what was tested, what materials were added and what was left untouched. The object is reviewed every year. Conservation is therefore not a single perfect repair. It is a series of limited decisions that preserve evidence while allowing later experts to reconsider earlier choices.''',
  'questions':[
   ('text','The textile’s main fibre is ______.','flax','Laboratory work identifies flax.'),
   ('text','Traces of ______ were found near the edge.','iron','The darker edge contains iron.'),
   ('mcq','What is used first to remove loose dust?','A','The conservator uses a soft brush.',['A. A soft brush','B. A washing machine','C. A chemical spray']),
   ('text','A ______ test checks whether the cloth is too acidic.','pH','The lecturer mentions a pH test.'),
   ('text','A fine piece of ______ may support the cloth.','silk','Silk can be placed behind it.'),
   ('text','Storage humidity is about ______ percent.','50','The target is fifty percent relative humidity.'),
   ('text','Display light should not exceed ______ lux.','50','The recommended maximum is fifty lux.'),
   ('mcq','Why might a newly acquired textile be frozen?','B','Freezing can kill many pests.',['A. To change its colour','B. To kill insects','C. To make it easier to fold']),
   ('text','Treatment is documented with written notes and ______.','photographs','The lecturer lists photographs and written notes.'),
   ('text','The object is reviewed every ______.','year','It is reviewed every year.')
  ]}
]
questions=[]
for i,section in enumerate(sections):
 for j,(kind,prompt,answer,explanation,*rest) in enumerate(section['questions'],start=1):
  questions.append({'number':i*10+j,'section':section['id'],'type':kind,'prompt':prompt,'answer':answer,'explanation':explanation,'options':rest[0] if rest else []})
 section.pop('questions')
 section['audio']='audio/'+section['id'].lower()+'.m4a'
assert len(questions)==40
obj={'id':'original-academic-listening-01','title':'原创 Academic Listening 模考 01','sourceType':'original_practice','notice':'原创缩时听力练习：4 个场景、40 题，音频由系统语音合成；并非 2026 年考场原题、真实录音或官方模考。','durationMinutes':30,'sections':sections,'questions':questions}
(APP/'data/listening-test.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
for section in sections:
 out=AUDIO/(section['id'].lower()+'.m4a')
 aiff=AUDIO/(section['id'].lower()+'.aiff')
 subprocess.run(['say','-v','Daniel','-r','165','-o',str(aiff),section['transcript']],check=True)
 subprocess.run(['afconvert','-f','m4af','-d','aac',str(aiff),str(out)],check=True)
 aiff.unlink()
 print(section['id'],out.stat().st_size,'bytes')
print('wrote',len(questions),'questions')
subprocess.run([sys.executable, str(APP/'scripts/build_sentence_audio.py')], check=True)
