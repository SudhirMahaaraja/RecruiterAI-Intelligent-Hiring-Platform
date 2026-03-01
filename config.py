import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'rec-agent-secret-key-2026')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/recruiting_agent')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MODELS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
    
    # Assessment settings
    ASSESSMENT_DURATION_MINUTES = 30
    MAX_TAB_SWITCHES = 3
    
    # YOLO model
    YOLO_MODEL = 'yolov8n.pt'
