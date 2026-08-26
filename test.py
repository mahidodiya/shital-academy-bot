from chatbot import process_message

CASES = [
       "hi python course duration and fees details please",
"excel course starting date and branch address",
"ielts offline?",
"confused between rapido and spoken english",
"do u provide certifcate after python?",
"timing?",

"im weak in english foundation vs rapido which one?" ,
"can senior citizen join ccc class?" ,
"office executive course has tally and excel both?",
"ccc or office executive for back office job?",

"data analytics course me placement guaranteed hai?"  ,
"python certificate standard hai ki govt recognized?" ,
"tally + excel sath me kare toh discount milega?",

"python me django and flask sikhoge?" ,
"data analytics course includes power bi or sql?"  ,
"tally me payroll and export sales hai?" ,
"advanced ccc covers ai tools and shortcuts?",

"online class available or only offline in bhavnagar?",
"ielts mock test weekly hota hai?" ,
"gujarati typing practice ccc me milegi?" ,

]

for q in CASES:
    r = process_message(q)
    print(f"\nYOU: {q}\nBOT: {r['response']}\nINTENT: {r.get('intent')} | COURSE: {r.get('course')} | FAQ: {r.get('course_faq') or r.get('academy_faq')}")
