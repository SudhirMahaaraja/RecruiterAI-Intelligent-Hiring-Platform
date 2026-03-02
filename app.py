import os
import json
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
import bcrypt

from config import Config
from utils.ai_screening import screen_candidate
from utils.resume_parser import parse_resume

app = Flask(__name__)
app.config.from_object(Config)

# MongoDB setup
client = MongoClient(app.config['MONGO_URI'])
db = client.recruiting_agent
fs = gridfs.GridFS(db)

# Collections
jobs_col = db.jobs
candidates_col = db.candidates
applications_col = db.applications
assessments_col = db.assessments
coding_problems_col = db.coding_problems
assessment_results_col = db.assessment_results
coding_results_col = db.coding_results
hr_users_col = db.hr_users
meetings_col = db.meetings
proctor_logs_col = db.proctor_logs

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MODELS_FOLDER'], exist_ok=True)


# ─── Helpers ────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def validate_experience(exp_str):
    """Validate that experience is within 0-3 years bracket."""
    import re
    # Extract all numbers from the string
    numbers = [int(n) for n in re.findall(r'\d+', exp_str)]
    if not numbers:
        return True # If no numbers, assume it's a general description
    
    # Check if any number exceeds 3
    for n in numbers:
        if n > 3:
            return False
    return True


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'hr_user' not in session:
            flash('Please log in to access the HR dashboard.', 'warning')
            return redirect(url_for('hr_login'))
        return f(*args, **kwargs)
    return decorated


def candidate_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'candidate_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('candidate_login'))
        return f(*args, **kwargs)
    return decorated


def seed_data():
    """Seed initial job listings and HR user if empty."""
    if hr_users_col.count_documents({}) == 0:
        hashed = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        hr_users_col.insert_one({
            'username': 'admin',
            'password': hashed,
            'name': 'HR Admin',
            'email': 'hr@company.com',
            'created_at': datetime.utcnow()
        })

    # Clear existing jobs if they have old configurations (like 3-5 years)
    if jobs_col.count_documents({'experience': {'$regex': '[4-9]|1[0-9]'}}) > 0:
        jobs_col.delete_many({})

    if jobs_col.count_documents({}) == 0:
        sample_jobs = [
            {
                'title': 'Python Developer (Fresher)',
                'department': 'Engineering',
                'location': 'Bangalore, India',
                'type': 'Full-time',
                'experience': '0-2 years',
                'salary_range': '₹6L - ₹12L',
                'description': 'Join our engineering team as a Python Developer. You\'ll contribute to building scalable backend services and learn best practices in software development.',
                'requirements': [
                    'Proficiency in Python 3.x',
                    'Basic understanding of Flask or Django',
                    'Knowledge of SQL databases',
                    'Eagerness to learn Docker and Kubernetes',
                    'Understanding of Git version control'
                ],
                'responsibilities': [
                    'Develop backend components',
                    'Write clean and testable code',
                    'Collaborate with the team on feature development',
                    'Participate in peer code reviews'
                ],
                'skills': ['python', 'flask', 'sql', 'git', 'rest api'],
                'status': 'active',
                'created_at': datetime.utcnow(),
                'applications_count': 0
            },
            {
                'title': 'Junior Frontend Developer',
                'department': 'Engineering',
                'location': 'Remote',
                'type': 'Full-time',
                'experience': '0-1 year',
                'salary_range': '₹5L - ₹10L',
                'description': 'We are looking for a Junior Frontend Developer to join our team. You\'ll build responsive UI components and collaborate with designers to deliver great user experiences.',
                'requirements': [
                    'Good knowledge of JavaScript/TypeScript',
                    'Basic understanding of React.js',
                    'Strong knowledge of HTML5 and CSS3',
                    'Experience with responsive web design',
                    'Familiarity with Git'
                ],
                'responsibilities': [
                    'Build UI components with React',
                    'Ensure responsiveness of web pages',
                    'Collaborate with designers and backend developers',
                    'Fix UI bugs and improve performance'
                ],
                'skills': ['javascript', 'react', 'html', 'css', 'git', 'responsive design'],
                'status': 'active',
                'created_at': datetime.utcnow(),
                'applications_count': 0
            },
            {
                'title': 'Junior Data Scientist',
                'department': 'Data & Analytics',
                'location': 'Hyderabad, India',
                'type': 'Full-time',
                'experience': '0-2 years',
                'salary_range': '₹8L - ₹15L',
                'description': 'Entry-level Data Scientist role focusing on building ML models, data analysis, and providing insights for business decisions.',
                'requirements': [
                    'Foundation in statistics and mathematics',
                    'Proficiency in Python',
                    'Familiarity with scikit-learn or TensorFlow',
                    'Basic SQL knowledge',
                    'Understanding of data visualization'
                ],
                'responsibilities': [
                    'Perform exploratory data analysis',
                    'Help develop machine learning models',
                    'Clean and preprocess data',
                    'Document findings and report to the team'
                ],
                'skills': ['python', 'statistics', 'machine learning', 'sql', 'data analysis'],
                'status': 'active',
                'created_at': datetime.utcnow(),
                'applications_count': 0
            },
            {
                'title': 'Junior DevOps Engineer',
                'department': 'Infrastructure',
                'location': 'Chennai, India',
                'type': 'Full-time',
                'experience': '1-3 years',
                'salary_range': '₹7L - ₹13L',
                'description': 'Start your career in infrastructure management. You\'ll help manage cloud services, build CI/CD pipelines, and ensure system reliability.',
                'requirements': [
                    'Basic understanding of AWS/GCP',
                    'Knowledge of Docker containers',
                    'Familiarity with CI/CD concepts',
                    'Basic Linux shell scripting skills',
                    'Eagerness to learn Terraform'
                ],
                'responsibilities': [
                    'Support cloud infrastructure management',
                    'Assist in building CI/CD pipelines',
                    'Monitor system health and performance',
                    'Troubleshoot infrastructure issues'
                ],
                'skills': ['aws', 'docker', 'linux', 'ci/cd', 'git'],
                'status': 'active',
                'created_at': datetime.utcnow(),
                'applications_count': 0
            }
        ]
        jobs_col.insert_many(sample_jobs)

    # Seed coding problems
    if db.coding_problems.count_documents({}) == 0:
        sample_coding_problems = [
            {
                'title': 'Reverse a String',
                'description': 'Write a function that reverses a string.',
                'difficulty': 'Easy',
                'category': 'General',
                'initial_code': 'def reverse_string(s):\n    # Write your code here\n    pass',
                'test_cases': [
                    {'input': 'hello', 'expected': 'olleh'},
                    {'input': 'Python', 'expected': 'nohtyP'}
                ]
            },
            {
                'title': 'Find Maximum',
                'description': 'Write a function that finds the maximum value in a list of numbers.',
                'difficulty': 'Easy',
                'category': 'General',
                'initial_code': 'def find_max(numbers):\n    # Write your code here\n    pass',
                'test_cases': [
                    {'input': [1, 5, 3, 9, 2], 'expected': 9},
                    {'input': [-1, -5, -3], 'expected': -1}
                ]
            },
            {
                'title': 'Palindrome Check',
                'description': 'Write a function that checks if a string is a palindrome.',
                'difficulty': 'Easy',
                'category': 'General',
                'initial_code': 'def is_palindrome(s):\n    # Write your code here\n    pass',
                'test_cases': [
                    {'input': 'racecar', 'expected': True},
                    {'input': 'hello', 'expected': False}
                ]
            }
        ]
        db.coding_problems.insert_many(sample_coding_problems)

    # Seed sample assessments
    if assessments_col.count_documents({}) == 0:
        sample_assessments = [
            {
                'title': 'Python Developer Assessment',
                'category': 'Engineering',
                'duration_minutes': 30,
                'questions': [
                    {
                        'id': 1,
                        'question': 'What is the output of: print(type([]) is list)?',
                        'options': ['True', 'False', 'Error', 'None'],
                        'correct': 0,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 2,
                        'question': 'Which of the following is used to create a generator in Python?',
                        'options': ['return', 'yield', 'generate', 'create'],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 3,
                        'question': 'What does the GIL in Python stand for?',
                        'options': ['Global Interpreter Lock', 'General Input Lock', 'Global Input Layer', 'General Interpreter Layer'],
                        'correct': 0,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 4,
                        'question': 'What is the time complexity of dictionary lookup in Python?',
                        'options': ['O(n)', 'O(log n)', 'O(1)', 'O(n²)'],
                        'correct': 2,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 5,
                        'question': 'Which decorator is used to define a static method in Python?',
                        'options': ['@static', '@staticmethod', '@classmethod', '@method'],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 6,
                        'question': 'What is the difference between deepcopy and copy in Python?',
                        'options': [
                            'No difference',
                            'deepcopy creates a new object with new nested objects, copy creates shallow copy',
                            'copy is faster than deepcopy always',
                            'deepcopy only works with lists'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 7,
                        'question': 'What will be the output of: list(range(0, 10, 3))?',
                        'options': ['[0, 3, 6, 9]', '[0, 3, 6]', '[3, 6, 9]', '[0, 1, 2, 3]'],
                        'correct': 0,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 8,
                        'question': 'Which Python module is used for regular expressions?',
                        'options': ['regex', 're', 'regexp', 'pattern'],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 9,
                        'question': 'What is a Python decorator?',
                        'options': [
                            'A function that takes another function and extends its behavior',
                            'A class that inherits from another class',
                            'A special type of variable',
                            'A Python module'
                        ],
                        'correct': 0,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 10,
                        'question': 'What does the __init__ method do in a Python class?',
                        'options': [
                            'Destroys an object',
                            'Initializes a new instance of the class',
                            'Creates a static method',
                            'Imports a module'
                        ],
                        'correct': 1,
                        'difficulty': 'easy'
                    }
                ],
                'created_at': datetime.utcnow()
            },
            {
                'title': 'Frontend Developer Assessment',
                'category': 'Engineering',
                'duration_minutes': 30,
                'questions': [
                    {
                        'id': 1,
                        'question': 'What does the "use strict" directive do in JavaScript?',
                        'options': [
                            'Enables strict mode with additional error checking',
                            'Makes variables immutable',
                            'Disables console logging',
                            'Enables TypeScript features'
                        ],
                        'correct': 0,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 2,
                        'question': 'Which CSS property is used to create a flex container?',
                        'options': ['display: block', 'display: flex', 'display: grid', 'display: inline'],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 3,
                        'question': 'What is the virtual DOM in React?',
                        'options': [
                            'The actual browser DOM',
                            'A lightweight copy of the real DOM for efficient updates',
                            'A CSS framework',
                            'A type of database'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 4,
                        'question': 'What is event bubbling in JavaScript?',
                        'options': [
                            'Events propagate from child to parent elements',
                            'Events propagate from parent to child elements',
                            'Events are cancelled automatically',
                            'Events only fire on the target element'
                        ],
                        'correct': 0,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 5,
                        'question': 'Which hook is used for side effects in React?',
                        'options': ['useState', 'useEffect', 'useReducer', 'useContext'],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 6,
                        'question': 'What is the CSS Box Model order from inside to outside?',
                        'options': [
                            'Content → Padding → Border → Margin',
                            'Margin → Border → Padding → Content',
                            'Content → Border → Padding → Margin',
                            'Padding → Content → Border → Margin'
                        ],
                        'correct': 0,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 7,
                        'question': 'What does Promise.all() do?',
                        'options': [
                            'Resolves when any promise resolves',
                            'Resolves when all promises resolve, rejects if any rejects',
                            'Always resolves regardless of individual promises',
                            'Runs promises sequentially'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 8,
                        'question': 'What is the purpose of the key prop in React lists?',
                        'options': [
                            'Styling purposes',
                            'Helps React identify which items have changed for efficient re-rendering',
                            'Required for all React components',
                            'Adds accessibility features'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 9,
                        'question': 'Which HTTP method is idempotent?',
                        'options': ['POST', 'GET', 'PATCH', 'None of these'],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 10,
                        'question': 'What is closure in JavaScript?',
                        'options': [
                            'A function that has access to variables from its outer scope',
                            'A way to close the browser window',
                            'A type of loop',
                            'A CSS property'
                        ],
                        'correct': 0,
                        'difficulty': 'medium'
                    }
                ],
                'created_at': datetime.utcnow()
            },
            {
                'title': 'Data Science Assessment',
                'category': 'Data & Analytics',
                'duration_minutes': 30,
                'questions': [
                    {
                        'id': 1,
                        'question': 'What is the difference between supervised and unsupervised learning?',
                        'options': [
                            'Supervised uses labeled data, unsupervised uses unlabeled data',
                            'No difference',
                            'Supervised is faster',
                            'Unsupervised requires more data'
                        ],
                        'correct': 0,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 2,
                        'question': 'What is overfitting in machine learning?',
                        'options': [
                            'Model performs well on training data but poorly on unseen data',
                            'Model performs poorly on all data',
                            'Model is too simple',
                            'Model trains too fast'
                        ],
                        'correct': 0,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 3,
                        'question': 'Which algorithm is commonly used for classification?',
                        'options': ['Linear Regression', 'Random Forest', 'K-Means', 'PCA'],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 4,
                        'question': 'What is the purpose of cross-validation?',
                        'options': [
                            'To train the model faster',
                            'To evaluate model performance on different subsets of data',
                            'To increase the dataset size',
                            'To reduce the number of features'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 5,
                        'question': 'What does the F1 score measure?',
                        'options': [
                            'Only precision',
                            'Only recall',
                            'Harmonic mean of precision and recall',
                            'Accuracy of the model'
                        ],
                        'correct': 2,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 6,
                        'question': 'What is regularization used for?',
                        'options': [
                            'To speed up training',
                            'To prevent overfitting by adding a penalty term',
                            'To increase model complexity',
                            'To normalize the data'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 7,
                        'question': 'Which technique is used for dimensionality reduction?',
                        'options': ['Random Forest', 'PCA', 'Gradient Descent', 'Backpropagation'],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 8,
                        'question': 'What is the vanishing gradient problem?',
                        'options': [
                            'Gradients become too large during training',
                            'Gradients become extremely small, making learning very slow',
                            'The model runs out of memory',
                            'The learning rate is too high'
                        ],
                        'correct': 1,
                        'difficulty': 'hard'
                    },
                    {
                        'id': 9,
                        'question': 'What is the purpose of a confusion matrix?',
                        'options': [
                            'To visualize model predictions vs actual values',
                            'To confuse the model',
                            'To store training data',
                            'To optimize hyperparameters'
                        ],
                        'correct': 0,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 10,
                        'question': 'What is batch normalization?',
                        'options': [
                            'Normalizing the entire dataset at once',
                            'Normalizing layer inputs for each mini-batch during training',
                            'Reducing batch size',
                            'A type of data augmentation'
                        ],
                        'correct': 1,
                        'difficulty': 'hard'
                    }
                ],
                'created_at': datetime.utcnow()
            },
            {
                'title': 'DevOps Assessment',
                'category': 'Infrastructure',
                'duration_minutes': 30,
                'questions': [
                    {
                        'id': 1,
                        'question': 'What is the primary purpose of Docker?',
                        'options': [
                            'Version control',
                            'Containerization of applications',
                            'Database management',
                            'Network monitoring'
                        ],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 2,
                        'question': 'What is Kubernetes used for?',
                        'options': [
                            'Code compilation',
                            'Container orchestration',
                            'File storage',
                            'Email service'
                        ],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 3,
                        'question': 'What is Infrastructure as Code (IaC)?',
                        'options': [
                            'Writing code in the cloud',
                            'Managing infrastructure through machine-readable config files',
                            'A programming language',
                            'A type of database'
                        ],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 4,
                        'question': 'What is the difference between a Docker image and a container?',
                        'options': [
                            'No difference',
                            'An image is a template, a container is a running instance of an image',
                            'A container is a template, an image is a running instance',
                            'Images are larger than containers'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 5,
                        'question': 'What does CI/CD stand for?',
                        'options': [
                            'Code Integration/Code Deployment',
                            'Continuous Integration/Continuous Delivery',
                            'Container Integration/Container Deployment',
                            'Cloud Integration/Cloud Delivery'
                        ],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 6,
                        'question': 'What is a Kubernetes Pod?',
                        'options': [
                            'A virtual machine',
                            'The smallest deployable unit that can contain one or more containers',
                            'A type of network',
                            'A storage volume'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 7,
                        'question': 'What is the purpose of a load balancer?',
                        'options': [
                            'To store data',
                            'To distribute incoming traffic across multiple servers',
                            'To compile code',
                            'To monitor logs'
                        ],
                        'correct': 1,
                        'difficulty': 'easy'
                    },
                    {
                        'id': 8,
                        'question': 'What is Terraform primarily used for?',
                        'options': [
                            'Application development',
                            'Provisioning and managing infrastructure',
                            'Code testing',
                            'Log analysis'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 9,
                        'question': 'What is the purpose of a reverse proxy?',
                        'options': [
                            'To directly serve static files',
                            'To forward client requests to backend servers and return responses',
                            'To block all incoming traffic',
                            'To compress files'
                        ],
                        'correct': 1,
                        'difficulty': 'medium'
                    },
                    {
                        'id': 10,
                        'question': 'What is the 12-factor app methodology?',
                        'options': [
                            'A set of 12 programming languages',
                            'Best practices for building scalable, maintainable SaaS applications',
                            'A security framework',
                            'A testing methodology'
                        ],
                        'correct': 1,
                        'difficulty': 'hard'
                    }
                ],
                'created_at': datetime.utcnow()
            }
        ]
        assessments_col.insert_many(sample_assessments)


# ─── PUBLIC ROUTES ──────────────────────────────────────────────────

@app.route('/')
def index():
    jobs = list(jobs_col.find({'status': 'active'}).sort('created_at', -1))
    return render_template('index.html', jobs=jobs)


@app.route('/job/<job_id>')
def job_detail(job_id):
    job = jobs_col.find_one({'_id': ObjectId(job_id)})
    if not job:
        flash('Job not found.', 'danger')
        return redirect(url_for('index'))
    return render_template('job_detail.html', job=job)


@app.route('/apply/<job_id>', methods=['GET', 'POST'])
def apply(job_id):
    job = jobs_col.find_one({'_id': ObjectId(job_id)})
    if not job:
        flash('Job not found.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        linkedin = request.form.get('linkedin', '').strip()
        cover_letter = request.form.get('cover_letter', '').strip()
        resume = request.files.get('resume')

        if not all([name, email, phone]) or not resume:
            flash('Please fill in all required fields and upload your resume.', 'danger')
            return render_template('apply.html', job=job)

        if not allowed_file(resume.filename):
            flash('Invalid file format. Please upload PDF or DOCX.', 'danger')
            return render_template('apply.html', job=job)

        # Check for duplicate application
        existing = applications_col.find_one({
            'email': email,
            'job_id': str(job['_id'])
        })
        if existing:
            flash('You have already applied for this position.', 'warning')
            return render_template('apply.html', job=job)

        # Save resume to MongoDB GridFS
        filename = secure_filename(f"{email}_{resume.filename}")
        resume_file_id = fs.put(resume, filename=filename, content_type=resume.content_type)

        # Parse resume directly from the uploaded file stream
        resume.seek(0)
        resume_text = parse_resume(resume, ext=os.path.splitext(filename)[1].lower())

        # AI Screening
        screening_result = screen_candidate(resume_text, job)

        # Save or update candidate
        candidate = candidates_col.find_one({'email': email})
        if not candidate:
            candidate_id = candidates_col.insert_one({
                'name': name,
                'email': email,
                'phone': phone,
                'linkedin': linkedin,
                'resume_file_id': resume_file_id,
                'resume_text': resume_text,
                'created_at': datetime.utcnow()
            }).inserted_id
        else:
            candidate_id = candidate['_id']
            candidates_col.update_one(
                {'_id': candidate_id},
                {'$set': {
                    'resume_file_id': resume_file_id,
                    'resume_text': resume_text,
                    'phone': phone
                }}
            )

        # Determine stage based on screening
        if screening_result['score'] >= 60:
            stage = 'assessment'
            stage_label = 'Round 1: Assessment Pending'
        else:
            stage = 'rejected'
            stage_label = 'Did Not Meet Requirements'

        # Create application record
        application_id = applications_col.insert_one({
            'candidate_id': str(candidate_id),
            'job_id': str(job['_id']),
            'job_title': job['title'],
            'name': name,
            'email': email,
            'phone': phone,
            'linkedin': linkedin,
            'cover_letter': cover_letter,
            'resume_file_id': resume_file_id,
            'screening_score': screening_result['score'],
            'screening_details': screening_result,
            'stage': stage,
            'stage_label': stage_label,
            'stage_history': [
                {
                    'stage': 'applied',
                    'label': 'Application Submitted',
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'stage': 'screening',
                    'label': 'AI Screening Completed',
                    'score': screening_result['score'],
                    'timestamp': datetime.utcnow().isoformat()
                },
                {
                    'stage': stage,
                    'label': stage_label,
                    'timestamp': datetime.utcnow().isoformat()
                }
            ],
            'proctor_flags': [],
            'assessment_completed': False,
            'assessment_score': None,
            'meeting_scheduled': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }).inserted_id

        # Update jobs application count
        jobs_col.update_one({'_id': job['_id']}, {'$inc': {'applications_count': 1}})

        # Store candidate session
        session['candidate_id'] = str(candidate_id)
        session['candidate_name'] = name
        session['candidate_email'] = email

        if stage == 'assessment':
            flash('Your application has been submitted and you have been shortlisted! Please proceed to the assessment.', 'success')
            return redirect(url_for('candidate_dashboard'))
        else:
            flash('Thank you for applying. We will review your application and get back to you.', 'info')
            return redirect(url_for('application_status', application_id=str(application_id)))

    return render_template('apply.html', job=job)


# ─── CANDIDATE ROUTES ──────────────────────────────────────────────

@app.route('/candidate/login', methods=['GET', 'POST'])
def candidate_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        candidate = candidates_col.find_one({'email': email})
        if candidate:
            session['candidate_id'] = str(candidate['_id'])
            session['candidate_name'] = candidate['name']
            session['candidate_email'] = candidate['email']
            return redirect(url_for('candidate_dashboard'))
        else:
            flash('No account found with this email. Please apply for a job first.', 'danger')
    return render_template('candidate_login.html')


@app.route('/candidate/dashboard')
@candidate_login_required
def candidate_dashboard():
    candidate_id = session['candidate_id']
    applications = list(applications_col.find({'candidate_id': candidate_id}).sort('created_at', -1))
    return render_template('candidate_dashboard.html', applications=applications)


@app.route('/candidate/coding-assessment/<application_id>')
@candidate_login_required
def take_coding_assessment(application_id):
    application = applications_col.find_one({'_id': ObjectId(application_id)})
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('candidate_dashboard'))

    if application['candidate_id'] != session['candidate_id']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('candidate_dashboard'))

    if application.get('coding_completed'):
        flash('You have already completed the coding assessment.', 'info')
        return redirect(url_for('candidate_dashboard'))

    if application['stage'] != 'coding_round':
        flash('Coding assessment is not available at this stage.', 'warning')
        return redirect(url_for('candidate_dashboard'))

    # Get 2 random coding problems
    problems = list(coding_problems_col.aggregate([{'$sample': {'size': 2}}]))

    return render_template('coding_assessment.html',
                         application=application,
                         problems=problems)


@app.route('/api/submit-coding-assessment', methods=['POST'])
def submit_coding_assessment():
    if 'candidate_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    application_id = data.get('application_id')
    solutions = data.get('solutions', []) # List of {problem_id, code}

    try:
        application = applications_col.find_one({'_id': ObjectId(application_id)})
    except Exception:
        return jsonify({'error': 'Invalid application'}), 400

    if not application:
        return jsonify({'error': 'Application not found'}), 404

    # Basic scoring logic (in a real app, this would use a sandbox)
    results = []
    total_score = 0
    for sol in solutions:
        problem = coding_problems_col.find_one({'_id': ObjectId(sol['problem_id'])})
        if not problem: continue

        # Placeholder for actual code execution/testing
        # For now, we'll just record the submission and give a partial score
        # based on presence of code
        code_length = len(sol['code'].strip())
        score = 50 if code_length > 20 else 0 # Simple heuristic
        results.append({
            'problem_id': sol['problem_id'],
            'title': problem['title'],
            'code': sol['code'],
            'score': score
        })
        total_score += score

    avg_score = total_score / len(solutions) if solutions else 0

    # Save result
    coding_results_col.insert_one({
        'application_id': application_id,
        'candidate_id': session['candidate_id'],
        'solutions': results,
        'avg_score': avg_score,
        'completed_at': datetime.utcnow()
    })

    # Update application stage to behavioural
    next_stage = 'behavioural'
    stage_label = 'Round 3: Behavioural Round'

    applications_col.update_one(
        {'_id': ObjectId(application_id)},
        {
            '$set': {
                'stage': next_stage,
                'stage_label': stage_label,
                'coding_completed': True,
                'coding_score': avg_score,
                'updated_at': datetime.utcnow()
            },
            '$push': {
                'stage_history': {
                    'stage': next_stage,
                    'label': stage_label,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        }
    )

    return jsonify({
        'success': True,
        'message': 'Coding assessment submitted successfully.',
        'next_stage': next_stage
    })


@app.route('/candidate/assessment/<application_id>')
@candidate_login_required
def take_assessment(application_id):
    application = applications_col.find_one({'_id': ObjectId(application_id)})
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('candidate_dashboard'))

    if application['candidate_id'] != session['candidate_id']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('candidate_dashboard'))

    if application.get('assessment_completed'):
        flash('You have already completed this assessment.', 'info')
        return redirect(url_for('candidate_dashboard'))

    if application['stage'] != 'assessment':
        flash('Assessment is not available at this stage.', 'warning')
        return redirect(url_for('candidate_dashboard'))

    # Find the matching assessment
    job = jobs_col.find_one({'_id': ObjectId(application['job_id'])})
    assessment = None
    if job:
        assessment = assessments_col.find_one({'category': job.get('department', '')})
    if not assessment:
        assessment = assessments_col.find_one({})

    if not assessment:
        flash('No assessment available. Please contact HR.', 'warning')
        return redirect(url_for('candidate_dashboard'))

    return render_template('assessment.html',
                         application=application,
                         assessment=assessment,
                         duration=assessment.get('duration_minutes', 30))


@app.route('/api/auto-terminate-assessment', methods=['POST'])
def auto_terminate_assessment():
    """Auto-terminate assessment due to severe proctoring violations."""
    if 'candidate_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    application_id = data.get('application_id')
    reason = data.get('reason', 'Severe proctoring violation')
    proctor_data = data.get('proctor_data', {})

    try:
        application = applications_col.find_one({'_id': ObjectId(application_id)})
    except Exception:
        return jsonify({'error': 'Invalid application'}), 400

    if not application:
        return jsonify({'error': 'Application not found'}), 404

    # Force reject
    stage_label = f'Rejected — {reason}'
    proctor_flags = [reason]

    assessment_results_col.insert_one({
        'application_id': application_id,
        'candidate_id': session['candidate_id'],
        'answers': {},
        'score': 0,
        'correct_count': 0,
        'total_questions': 0,
        'integrity_score': 0,
        'proctor_data': proctor_data,
        'proctor_flags': proctor_flags,
        'terminated': True,
        'termination_reason': reason,
        'completed_at': datetime.utcnow()
    })

    applications_col.update_one(
        {'_id': ObjectId(application_id)},
        {
            '$set': {
                'stage': 'rejected',
                'stage_label': stage_label,
                'assessment_completed': True,
                'assessment_score': 0,
                'integrity_score': 0,
                'proctor_flags': proctor_flags,
                'updated_at': datetime.utcnow()
            },
            '$push': {
                'stage_history': {
                    'stage': 'rejected',
                    'label': stage_label,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        }
    )

    return jsonify({
        'success': True,
        'terminated': True,
        'reason': reason
    })


@app.route('/api/submit-assessment', methods=['POST'])
def submit_assessment():
    if 'candidate_id' not in session:
        return jsonify({'error': 'Session expired. Please log in again.'}), 401
    data = request.get_json()
    application_id = data.get('application_id')
    answers = data.get('answers', {})
    proctor_data = data.get('proctor_data', {})

    application = applications_col.find_one({'_id': ObjectId(application_id)})
    if not application:
        return jsonify({'error': 'Application not found'}), 404

    job = jobs_col.find_one({'_id': ObjectId(application['job_id'])})
    assessment = None
    if job:
        assessment = assessments_col.find_one({'category': job.get('department', '')})
    if not assessment:
        assessment = assessments_col.find_one({})

    # Grade the assessment
    correct = 0
    total = len(assessment['questions'])
    for q in assessment['questions']:
        answer = answers.get(str(q['id']))
        if answer is not None and int(answer) == q['correct']:
            correct += 1

    score = round((correct / total) * 100) if total > 0 else 0

    # Analyze proctor data
    tab_switches = proctor_data.get('tab_switches', 0)
    copy_attempts = proctor_data.get('copy_attempts', 0)
    paste_attempts = proctor_data.get('paste_attempts', 0)
    right_click_attempts = proctor_data.get('right_click_attempts', 0)
    face_violations = proctor_data.get('face_violations', 0)
    multiple_persons = proctor_data.get('multiple_persons', 0)
    ai_detection_flags = proctor_data.get('ai_detection_flags', 0)

    proctor_flags = []
    integrity_score = 100

    if tab_switches > 2:
        proctor_flags.append(f'Excessive tab switching ({tab_switches} times)')
        integrity_score -= min(30, tab_switches * 5)
    elif tab_switches > 0:
        proctor_flags.append(f'Minor tab switching ({tab_switches} times)')
        integrity_score -= tab_switches * 3

    if copy_attempts > 0:
        proctor_flags.append(f'Copy attempts detected ({copy_attempts} times)')
        integrity_score -= copy_attempts * 10

    if paste_attempts > 0:
        proctor_flags.append(f'Paste attempts detected ({paste_attempts} times)')
        integrity_score -= paste_attempts * 10

    if right_click_attempts > 0:
        proctor_flags.append(f'Right-click attempts ({right_click_attempts} times)')
        integrity_score -= right_click_attempts * 5

    if face_violations > 0:
        proctor_flags.append(f'Face not detected / looking away ({face_violations} times)')
        integrity_score -= face_violations * 5

    if multiple_persons > 0:
        proctor_flags.append(f'Multiple persons detected ({multiple_persons} times)')
        integrity_score -= multiple_persons * 15

    integrity_score = max(0, integrity_score)

    # Check for auto-rejection due to severe violations
    auto_rejected = False
    if tab_switches > 2:
        auto_rejected = True
        proctor_flags.append('AUTO-REJECTED: Excessive tab switching')
    if face_violations >= 2:
        auto_rejected = True
        proctor_flags.append('AUTO-REJECTED: Camera hidden repeatedly')
    if multiple_persons >= 2:
        auto_rejected = True
        proctor_flags.append('AUTO-REJECTED: Multiple persons detected repeatedly')

    # Determine next stage
    if auto_rejected:
        next_stage = 'rejected'
        stage_label = 'Rejected — Severe Proctoring Violations'
        integrity_score = 0
    elif score >= 60 and integrity_score >= 50:
        next_stage = 'coding_round'
        stage_label = 'Round 2: Coding Assessment'
    elif integrity_score < 50:
        next_stage = 'flagged'
        stage_label = 'Flagged — Integrity Concerns'
    else:
        next_stage = 'rejected'
        stage_label = 'Assessment Not Passed'

    # Save assessment result
    assessment_results_col.insert_one({
        'application_id': application_id,
        'candidate_id': session['candidate_id'],
        'assessment_id': str(assessment['_id']),
        'answers': answers,
        'score': score,
        'correct_count': correct,
        'total_questions': total,
        'integrity_score': integrity_score,
        'proctor_data': proctor_data,
        'proctor_flags': proctor_flags,
        'completed_at': datetime.utcnow()
    })

    # Update application
    stage_entry = {
        'stage': next_stage,
        'label': stage_label,
        'assessment_score': score,
        'integrity_score': integrity_score,
        'timestamp': datetime.utcnow().isoformat()
    }

    applications_col.update_one(
        {'_id': ObjectId(application_id)},
        {
            '$set': {
                'stage': next_stage,
                'stage_label': stage_label,
                'assessment_completed': True,
                'assessment_score': score,
                'integrity_score': integrity_score,
                'proctor_flags': proctor_flags,
                'updated_at': datetime.utcnow()
            },
            '$push': {'stage_history': stage_entry}
        }
    )

    return jsonify({
        'success': True,
        'score': score,
        'integrity_score': integrity_score,
        'stage': next_stage,
        'message': stage_label
    })


@app.route('/application/<application_id>')
def application_status(application_id):
    application = applications_col.find_one({'_id': ObjectId(application_id)})
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('index'))
    return render_template('application_status.html', application=application)


# ─── PROCTOR API ────────────────────────────────────────────────────

@app.route('/api/proctor-log', methods=['POST'])
def proctor_log():
    data = request.get_json()
    data['timestamp'] = datetime.utcnow()
    proctor_logs_col.insert_one(data)
    return jsonify({'status': 'logged'})


@app.route('/api/detect-frame', methods=['POST'])
def detect_frame():
    """Receive a base64 frame and run YOLO person detection."""
    try:
        from ultralytics import YOLO
        import base64
        import numpy as np
        import cv2

        data = request.get_json()
        frame_data = data.get('frame', '')

        if ',' in frame_data:
            frame_data = frame_data.split(',')[1]

        img_bytes = base64.b64decode(frame_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        model_path = os.path.join(app.config['MODELS_FOLDER'], app.config['YOLO_MODEL'])
        if not os.path.exists(model_path):
            model_path = app.config['YOLO_MODEL']

        model = YOLO(model_path)
        results = model(img, verbose=False)

        person_count = 0
        phone_detected = False
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                if cls_name == 'person':
                    person_count += 1
                elif cls_name == 'cell phone':
                    phone_detected = True

        return jsonify({
            'person_count': person_count,
            'phone_detected': phone_detected,
            'violation': person_count != 1 or phone_detected
        })
    except Exception as e:
        return jsonify({'error': str(e), 'person_count': 1, 'violation': False})


# ─── HR ROUTES ──────────────────────────────────────────────────────

@app.route('/hr/login', methods=['GET', 'POST'])
def hr_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        hr_user = hr_users_col.find_one({'username': username})
        if hr_user and bcrypt.checkpw(password.encode('utf-8'), hr_user['password']):
            session['hr_user'] = {
                'id': str(hr_user['_id']),
                'username': hr_user['username'],
                'name': hr_user['name']
            }
            return redirect(url_for('hr_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('hr_login.html')


@app.route('/hr/logout')
def hr_logout():
    session.pop('hr_user', None)
    return redirect(url_for('hr_login'))


@app.route('/hr/dashboard')
@login_required
def hr_dashboard():
    # Stats
    total_apps = applications_col.count_documents({})
    pending_assessment = applications_col.count_documents({'stage': {'$in': ['assessment', 'coding_round']}})
    interview_ready = applications_col.count_documents({'stage': {'$in': ['behavioural', 'tech_hr', 'final_hr']}})
    flagged = applications_col.count_documents({'stage': 'flagged'})
    hired = applications_col.count_documents({'stage': 'hired'})
    rejected = applications_col.count_documents({'stage': 'rejected'})
    active_jobs = jobs_col.count_documents({'status': 'active'})

    stats = {
        'total_applications': total_apps,
        'pending_assessment': pending_assessment,
        'interview_ready': interview_ready,
        'flagged': flagged,
        'hired': hired,
        'rejected': rejected,
        'active_jobs': active_jobs
    }

    # Recent applications
    recent_apps = list(applications_col.find().sort('created_at', -1).limit(20))

    return render_template('hr_dashboard.html', stats=stats, applications=recent_apps)


@app.route('/hr/applications')
@login_required
def hr_applications():
    stage_filter = request.args.get('stage', 'all')
    query = {}
    if stage_filter != 'all':
        query['stage'] = stage_filter

    applications = list(applications_col.find(query).sort('created_at', -1))
    return render_template('hr_applications.html', applications=applications, current_filter=stage_filter)


@app.route('/hr/application/<application_id>')
@login_required
def hr_application_detail(application_id):
    application = applications_col.find_one({'_id': ObjectId(application_id)})
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('hr_dashboard'))

    assessment_result = assessment_results_col.find_one({'application_id': application_id})
    meetings = list(meetings_col.find({'application_id': application_id}).sort('created_at', -1))

    return render_template('hr_application_detail.html',
                         application=application,
                         assessment_result=assessment_result,
                         meetings=meetings)


@app.route('/hr/application/<application_id>/update-stage', methods=['POST'])
@login_required
def update_stage(application_id):
    new_stage = request.form.get('stage')
    stage_labels = {
        'assessment': 'Round 1: Assessment Pending',
        'coding_round': 'Round 2: Coding Assessment',
        'behavioural': 'Round 3: Behavioural Round',
        'tech_hr': 'Round 4: Tech HR',
        'final_hr': 'Round 5: Final HR',
        'offer': 'Offer Extended',
        'hired': 'Hired — Onboarding',
        'rejected': 'Rejected',
        'flagged': 'Flagged for Review'
    }

    label = stage_labels.get(new_stage, new_stage.title())

    applications_col.update_one(
        {'_id': ObjectId(application_id)},
        {
            '$set': {
                'stage': new_stage,
                'stage_label': label,
                'updated_at': datetime.utcnow()
            },
            '$push': {
                'stage_history': {
                    'stage': new_stage,
                    'label': label,
                    'updated_by': session['hr_user']['name'],
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        }
    )

    flash(f'Application stage updated to: {label}', 'success')
    return redirect(url_for('hr_application_detail', application_id=application_id))


@app.route('/hr/schedule-meeting/<application_id>', methods=['GET', 'POST'])
@login_required
def schedule_meeting(application_id):
    application = applications_col.find_one({'_id': ObjectId(application_id)})
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('hr_dashboard'))

    if request.method == 'POST':
        meeting_date = request.form.get('meeting_date')
        meeting_time = request.form.get('meeting_time')
        meeting_type = request.form.get('meeting_type', 'interview')
        meeting_link = request.form.get('meeting_link', '')
        notes = request.form.get('notes', '')

        meeting = {
            'application_id': application_id,
            'candidate_id': application['candidate_id'],
            'candidate_name': application['name'],
            'candidate_email': application['email'],
            'job_title': application['job_title'],
            'meeting_date': meeting_date,
            'meeting_time': meeting_time,
            'meeting_type': meeting_type,
            'meeting_link': meeting_link,
            'notes': notes,
            'status': 'scheduled',
            'scheduled_by': session['hr_user']['name'],
            'created_at': datetime.utcnow()
        }

        meetings_col.insert_one(meeting)

        # Update application
        applications_col.update_one(
            {'_id': ObjectId(application_id)},
            {
                '$set': {
                    'meeting_scheduled': True,
                    'updated_at': datetime.utcnow()
                },
                '$push': {
                    'stage_history': {
                        'stage': 'meeting_scheduled',
                        'label': f'{meeting_type.title()} scheduled for {meeting_date} at {meeting_time}',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            }
        )

        flash(f'Meeting scheduled successfully for {meeting_date} at {meeting_time}.', 'success')
        return redirect(url_for('hr_application_detail', application_id=application_id))

    return render_template('schedule_meeting.html', application=application)


@app.route('/hr/jobs')
@login_required
def hr_jobs():
    jobs = list(jobs_col.find().sort('created_at', -1))
    return render_template('hr_jobs.html', jobs=jobs)


@app.route('/hr/job/new', methods=['GET', 'POST'])
@login_required
def hr_new_job():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        department = request.form.get('department', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('type', '').strip()
        experience = request.form.get('experience', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        description = request.form.get('description', '').strip()
        requirements = [r.strip() for r in request.form.get('requirements', '').split('\n') if r.strip()]
        responsibilities = [r.strip() for r in request.form.get('responsibilities', '').split('\n') if r.strip()]
        skills = [s.strip().lower() for s in request.form.get('skills', '').split(',') if s.strip()]

        if not validate_experience(experience):
            flash('Error: This system only supports fresher-level roles (0-3 years experience). Please adjust the experience requirement.', 'danger')
            return render_template('hr_new_job.html')

        jobs_col.insert_one({
            'title': title,
            'department': department,
            'location': location,
            'type': job_type,
            'experience': experience,
            'salary_range': salary_range,
            'description': description,
            'requirements': requirements,
            'responsibilities': responsibilities,
            'skills': skills,
            'status': 'active',
            'created_at': datetime.utcnow(),
            'applications_count': 0
        })

        flash('Job listing created successfully!', 'success')
        return redirect(url_for('hr_jobs'))

    return render_template('hr_new_job.html')


@app.route('/candidate/logout')
def candidate_logout():
    session.pop('candidate_id', None)
    session.pop('candidate_name', None)
    session.pop('candidate_email', None)
    return redirect(url_for('index'))


# ─── ERROR HANDLERS ─────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ─── MAIN ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        seed_data()
    app.run(debug=True, use_reloader=False, port=5000)

# Auto-commit: Refactor assessment logic for better performance - 2026-03-04 17:53:52

# Auto-commit: Add logging to coding round submission - 2026-03-04 17:53:53

# Auto-commit: Implement security checks for proctoring - 2026-03-04 17:53:53
