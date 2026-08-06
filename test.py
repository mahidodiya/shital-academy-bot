from logics.course_detector import detect_course

tests = [
    # ---------- General ----------
    "I want to join a course",
    "Suggest me a course",
    "Which course is best?",
    "I want computer training",

    # ---------- Python ----------
    "I want to learn python",
    "Do you teach Python?",
    "Python programming course",
    "Pyhton classes",
    "Learn coding using python",

    # ---------- Excel ----------
    "Advanced Excel",
    "MS Excel classes",
    "Excel course",
    "Advnced excel",

    # ---------- Web Development ----------
    "Website development course",
    "PHP classes",
    "JavaScript course",
    "Backend development",
    "Frontend development",
    "Full stack course",

    # ---------- Web Designing ----------
    "HTML CSS course",
    "Learn web designing",
    "Website design course",

    # ---------- Data Analytics ----------
    "Power BI course",
    "SQL classes",
    "Python for Data Analysis",
    "Business Analytics",
    "Data Analyst course",

    # ---------- Office Executive ----------
    "Office assistant course",
    "Computer operator training",
    "Back office course",

    # ---------- Tally ----------
    "Tally Prime",
    "Tally classes",

    # ---------- CCC ----------
    "CCC",
    "Advanced CCC",
    "Computer basics",

    # ---------- English ----------
    "Spoken English",
    "Speak English fluently",
    "Foundation English",
    "Basic English",
    "Rapido English",
    "Rapid English",

    # ---------- IELTS ----------
    "IELTS coaching",
    "Study abroad",
    "IELTS preparation",

    # ---------- Negative ----------
    "Java programming",
    "Photoshop course",
    "Graphic design",
    "Mobile repairing",
    "Civil engineering",
    "AutoCAD",
    "Digital marketing",
]

for query in tests:
    course, score = detect_course(query)
    print(f"{query:<40} -> {course} ({score:.2f})")