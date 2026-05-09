"""
load_sample_data.py - Management Command to Load Sample Data

Run this command once to populate the database with:
- 3 sample candidates (for testing login)
- 50 sample Python/general knowledge questions

Usage:
    python manage.py load_sample_data
"""

from django.core.management.base import BaseCommand
from exam.models import Candidate, Question


class Command(BaseCommand):
    help = 'Load sample candidates and questions into the database'

    def handle(self, *args, **kwargs):
        self.stdout.write("[i] Loading sample data...\n")

        # ── Create Sample Candidates ──────────────────────────────────
        # These candidates can log in using name + mobile + registration_id
        candidates_data = [
            {'name': 'Rahul',  'mobile': '9876543210', 'registration_id': 'TH-2024-001'},
            {'name': 'Priya',   'mobile': '8765432109', 'registration_id': 'TH-2024-002'},
            {'name': 'Arjun Reddy',   'mobile': '7654321098', 'registration_id': 'TH-2024-003'},
            {'name': 'Sneha',   'mobile': '9988776655', 'registration_id': 'TH-2024-004'},
            {'name': 'Vikram',  'mobile': '9123456789', 'registration_id': 'TH-2024-005'},
            {'name': 'Abhi',  'mobile': '9999999999', 'registration_id': 'ABC123'},
        ]

        for c in candidates_data:
            candidate, created = Candidate.objects.get_or_create(
                registration_id=c['registration_id'],
                defaults={'name': c['name'], 'mobile': c['mobile']}
            )
            if created:
                self.stdout.write(f"  [OK] Candidate created: {c['name']} | ID: {c['registration_id']}")
            else:
                self.stdout.write(f"  [!] Candidate already exists: {c['name']}")

        # ── Create Sample Questions ───────────────────────────────────
        # 50 Python / Programming / General questions
        questions_data = [
            # Python Basics
            {
                'question_text': 'What is the output of: print(type([]))?',
                'option_a': "<class 'dict'>",
                'option_b': "<class 'list'>",
                'option_c': "<class 'tuple'>",
                'option_d': "<class 'set'>",
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which keyword is used to define a function in Python?',
                'option_a': 'func',
                'option_b': 'define',
                'option_c': 'def',
                'option_d': 'function',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What does OOP stand for?',
                'option_a': 'Object Oriented Python',
                'option_b': 'Object Oriented Programming',
                'option_c': 'Open Oriented Programming',
                'option_d': 'Object Ordered Programming',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which of the following is immutable in Python?',
                'option_a': 'List',
                'option_b': 'Dictionary',
                'option_c': 'Set',
                'option_d': 'Tuple',
                'correct_answer': 'D',
            },
            {
                'question_text': 'What is the correct syntax to create a class in Python?',
                'option_a': 'class MyClass():',
                'option_b': 'create MyClass():',
                'option_c': 'define MyClass():',
                'option_d': 'object MyClass():',
                'correct_answer': 'A',
            },
            {
                'question_text': 'Which method is used to add an item to a list in Python?',
                'option_a': 'add()',
                'option_b': 'push()',
                'option_c': 'append()',
                'option_d': 'insert_last()',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What is the output of: print(2 ** 3)?',
                'option_a': '6',
                'option_b': '8',
                'option_c': '9',
                'option_d': '5',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which of the following is used to handle exceptions in Python?',
                'option_a': 'try-catch',
                'option_b': 'try-except',
                'option_c': 'error-handle',
                'option_d': 'catch-finally',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What does len() function return?',
                'option_a': 'Length of a string only',
                'option_b': 'Number of elements in any iterable',
                'option_c': 'Last index of a list',
                'option_d': 'Memory size of object',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which symbol is used for single-line comments in Python?',
                'option_a': '//',
                'option_b': '--',
                'option_c': '#',
                'option_d': '/* */',
                'correct_answer': 'C',
            },
            # Django / Web
            {
                'question_text': 'What is Django?',
                'option_a': 'A JavaScript framework',
                'option_b': 'A Python web framework',
                'option_c': 'A database management system',
                'option_d': 'A CSS framework',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What does MVC stand for in web development?',
                'option_a': 'Model View Controller',
                'option_b': 'Module View Class',
                'option_c': 'Model Variable Content',
                'option_d': 'Method View Constructor',
                'correct_answer': 'A',
            },
            {
                'question_text': 'Which database does Django use by default?',
                'option_a': 'MySQL',
                'option_b': 'PostgreSQL',
                'option_c': 'SQLite',
                'option_d': 'MongoDB',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What command creates a new Django project?',
                'option_a': 'django new project',
                'option_b': 'django-admin startproject',
                'option_c': 'python start project',
                'option_d': 'manage.py createproject',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What is the purpose of migrations in Django?',
                'option_a': 'To deploy the project',
                'option_b': 'To synchronize database schema with models',
                'option_c': 'To transfer data between databases',
                'option_d': 'To start the development server',
                'correct_answer': 'B',
            },
            # Data Structures
            {
                'question_text': 'What is a stack?',
                'option_a': 'A data structure that follows FIFO',
                'option_b': 'A data structure that follows LIFO',
                'option_c': 'A sorted list',
                'option_d': 'A binary tree',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What is the time complexity of binary search?',
                'option_a': 'O(n)',
                'option_b': 'O(n²)',
                'option_c': 'O(log n)',
                'option_d': 'O(1)',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What is a dictionary in Python?',
                'option_a': 'An ordered list',
                'option_b': 'A collection of key-value pairs',
                'option_c': 'An unordered set',
                'option_d': 'A stack-based structure',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which sorting algorithm has the best average case time complexity?',
                'option_a': 'Bubble Sort',
                'option_b': 'Insertion Sort',
                'option_c': 'Quick Sort',
                'option_d': 'Selection Sort',
                'correct_answer': 'C',
            },
            {
                'question_text': 'In Python, which data structure uses curly braces {} and stores unique values?',
                'option_a': 'List',
                'option_b': 'Tuple',
                'option_c': 'Dictionary',
                'option_d': 'Set',
                'correct_answer': 'D',
            },
            # General CS
            {
                'question_text': 'What does CPU stand for?',
                'option_a': 'Central Process Unit',
                'option_b': 'Central Processing Unit',
                'option_c': 'Computer Processing Unit',
                'option_d': 'Core Processing Unit',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What is an API?',
                'option_a': 'Advanced Programming Interface',
                'option_b': 'Application Protocol Interface',
                'option_c': 'Application Programming Interface',
                'option_d': 'Automated Programming Interface',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What does HTTP stand for?',
                'option_a': 'Hyper Text Transfer Protocol',
                'option_b': 'Hyper Text Transmission Protocol',
                'option_c': 'High Transfer Text Protocol',
                'option_d': 'Hyper Text Transit Protocol',
                'correct_answer': 'A',
            },
            {
                'question_text': 'Which of the following is NOT a programming language?',
                'option_a': 'Python',
                'option_b': 'Java',
                'option_c': 'HTML',
                'option_d': 'C++',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What is the full form of SQL?',
                'option_a': 'Standard Query Language',
                'option_b': 'Structured Query Language',
                'option_c': 'Simple Query Language',
                'option_d': 'Sequential Query Language',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What is recursion in programming?',
                'option_a': 'A loop that runs infinitely',
                'option_b': 'A function that calls itself',
                'option_c': 'A function that calls another function',
                'option_d': 'A method to sort arrays',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which of the following is an object-oriented programming language?',
                'option_a': 'C',
                'option_b': 'Assembly',
                'option_c': 'Python',
                'option_d': 'FORTRAN',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What does RAM stand for?',
                'option_a': 'Random Access Memory',
                'option_b': 'Read Access Memory',
                'option_c': 'Random Available Memory',
                'option_d': 'Rapid Access Memory',
                'correct_answer': 'A',
            },
            {
                'question_text': 'What is a boolean data type?',
                'option_a': 'A data type that stores numbers',
                'option_b': 'A data type that stores True or False',
                'option_c': 'A data type that stores text',
                'option_d': 'A data type that stores lists',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What is the purpose of a primary key in a database?',
                'option_a': 'To encrypt data',
                'option_b': 'To uniquely identify each record in a table',
                'option_c': 'To link two tables',
                'option_d': 'To sort data automatically',
                'correct_answer': 'B',
            },
            # More Python
            {
                'question_text': 'What is the output of: print("Hello"[1])?',
                'option_a': 'H',
                'option_b': 'e',
                'option_c': 'l',
                'option_d': 'He',
                'correct_answer': 'B',
            },
            {
                'question_text': 'How do you convert a string "123" to an integer in Python?',
                'option_a': 'str("123")',
                'option_b': 'float("123")',
                'option_c': 'int("123")',
                'option_d': 'num("123")',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What is a lambda function in Python?',
                'option_a': 'A named function',
                'option_b': 'An anonymous one-line function',
                'option_c': 'A class method',
                'option_d': 'A built-in function',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which Python module is used for working with dates and times?',
                'option_a': 'time_module',
                'option_b': 'datetime',
                'option_c': 'calendar',
                'option_d': 'clock',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What is pip in Python?',
                'option_a': 'A Python testing tool',
                'option_b': 'Python Integrated Package',
                'option_c': 'Python package installer',
                'option_d': 'Python IDE Plugin',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What is __init__ in Python?',
                'option_a': 'A module file',
                'option_b': 'A constructor method of a class',
                'option_c': 'A global variable',
                'option_d': 'An import statement',
                'correct_answer': 'B',
            },
            {
                'question_text': 'How do you open a file in Python for reading?',
                'option_a': 'open("file.txt", "w")',
                'option_b': 'open("file.txt", "r")',
                'option_c': 'read("file.txt")',
                'option_d': 'load("file.txt")',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What does the "self" keyword represent in Python class methods?',
                'option_a': 'The parent class',
                'option_b': 'The current instance of the class',
                'option_c': 'The class itself',
                'option_d': 'A global variable',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which of the following is used to inherit from a parent class in Python?',
                'option_a': 'class Child extends Parent:',
                'option_b': 'class Child(Parent):',
                'option_c': 'class Child inherits Parent:',
                'option_d': 'class Child -> Parent:',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What is polymorphism?',
                'option_a': 'Using multiple databases',
                'option_b': 'Ability to take many forms — one interface, multiple implementations',
                'option_c': 'Hiding data from the user',
                'option_d': 'Writing multiple functions with same logic',
                'correct_answer': 'B',
            },
            # Networking / Web
            {
                'question_text': 'What is the default port for HTTPS?',
                'option_a': '80',
                'option_b': '8080',
                'option_c': '443',
                'option_d': '3000',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What does JSON stand for?',
                'option_a': 'JavaScript Object Notation',
                'option_b': 'Java Simple Object Network',
                'option_c': 'JavaScript Online Notation',
                'option_d': 'Java Script Object Naming',
                'correct_answer': 'A',
            },
            {
                'question_text': 'Which HTTP method is used to retrieve data from a server?',
                'option_a': 'POST',
                'option_b': 'PUT',
                'option_c': 'DELETE',
                'option_d': 'GET',
                'correct_answer': 'D',
            },
            {
                'question_text': 'What is a REST API?',
                'option_a': 'An API that only works with Python',
                'option_b': 'A stateless API architecture using HTTP methods',
                'option_c': 'An API for databases only',
                'option_d': 'An API for mobile apps',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which CSS framework is known for its responsive grid system?',
                'option_a': 'Tailwind',
                'option_b': 'Foundation',
                'option_c': 'Bootstrap',
                'option_d': 'Bulma',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What is Git used for?',
                'option_a': 'Web development',
                'option_b': 'Version control and source code management',
                'option_c': 'Database management',
                'option_d': 'Containerization',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What is encapsulation in OOP?',
                'option_a': 'Inheriting properties from parent class',
                'option_b': 'Writing multiple functions',
                'option_c': 'Binding data and methods together and restricting access',
                'option_d': 'Creating multiple objects',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What is the purpose of the "pass" statement in Python?',
                'option_a': 'To exit a loop',
                'option_b': 'To skip an iteration',
                'option_c': 'To do nothing — acts as a placeholder',
                'option_d': 'To pass a variable',
                'correct_answer': 'C',
            },
            {
                'question_text': 'What is a virtual environment in Python?',
                'option_a': 'A simulated OS',
                'option_b': 'An isolated Python environment with its own packages',
                'option_c': 'A Docker container',
                'option_d': 'A Python GUI tool',
                'correct_answer': 'B',
            },
            {
                'question_text': 'Which of the following is used to read environment variables in Python?',
                'option_a': 'sys.env',
                'option_b': 'os.environ',
                'option_c': 'env.get()',
                'option_d': 'config.read()',
                'correct_answer': 'B',
            },
            {
                'question_text': 'What does the "zip()" function do in Python?',
                'option_a': 'Compresses files',
                'option_b': 'Combines multiple iterables element-wise into tuples',
                'option_c': 'Sorts two lists together',
                'option_d': 'Merges two dictionaries',
                'correct_answer': 'B',
            },
        ]

        created_count = 0
        for q in questions_data:
            question, created = Question.objects.get_or_create(
                question_text=q['question_text'],
                defaults={
                    'option_a'      : q['option_a'],
                    'option_b'      : q['option_b'],
                    'option_c'      : q['option_c'],
                    'option_d'      : q['option_d'],
                    'correct_answer': q['correct_answer'],
                }
            )
            if created:
                created_count += 1

        self.stdout.write(f"\n  [OK] {created_count} questions added to database.")
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write("\n[OK] Sample data loaded successfully!\n")
        self.stdout.write("\n[i] TEST CANDIDATE CREDENTIALS:")
        self.stdout.write("-" * 40)
        for c in candidates_data:
            self.stdout.write(f"  Name: {c['name']}")
            self.stdout.write(f"  Mobile: {c['mobile']}")
            self.stdout.write(f"  Reg ID: {c['registration_id']}")
            self.stdout.write("-" * 40)
        self.stdout.write("\n[i] You can now run the server and login!\n")
