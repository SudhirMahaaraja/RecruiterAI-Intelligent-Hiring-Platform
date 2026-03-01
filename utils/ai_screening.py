"""
AI-powered candidate screening using TF-IDF similarity matching.
Compares candidate resume text against job description and requirements.
"""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def screen_candidate(resume_text, job):
    """
    Screen a candidate's resume against a job description.
    Returns a dict with score (0-100) and details.
    """
    if not resume_text or not resume_text.strip():
        return {
            'score': 0,
            'skill_match': 0,
            'experience_match': 0,
            'description_match': 0,
            'matched_skills': [],
            'missing_skills': job.get('skills', []),
            'summary': 'Could not parse resume content.'
        }

    resume_lower = resume_text.lower()

    # 1. Skill matching (40% weight)
    job_skills = [s.lower().strip() for s in job.get('skills', [])]
    matched_skills = []
    missing_skills = []

    for skill in job_skills:
        # Handle multi-word skills and variations
        skill_variants = [skill, skill.replace(' ', ''), skill.replace('-', ' ')]
        found = False
        for variant in skill_variants:
            if variant in resume_lower:
                matched_skills.append(skill)
                found = True
                break
        if not found:
            missing_skills.append(skill)

    skill_score = (len(matched_skills) / len(job_skills) * 100) if job_skills else 50

    # 2. Job description similarity (30% weight)
    job_text = f"{job.get('description', '')} {' '.join(job.get('requirements', []))} {' '.join(job.get('responsibilities', []))}"

    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        tfidf_matrix = vectorizer.fit_transform([resume_lower, job_text.lower()])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        description_score = similarity * 100
    except Exception:
        description_score = 30  # Default if TF-IDF fails

    # 3. Experience matching (30% weight)
    experience_score = 50  # Default
    exp_range = job.get('experience', '')
    exp_numbers = re.findall(r'\d+', exp_range)

    # Look for years of experience in resume
    resume_years = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)', resume_lower)
    if resume_years and exp_numbers:
        max_resume_years = max(int(y) for y in resume_years)
        min_required = int(exp_numbers[0]) if exp_numbers else 0
        if max_resume_years >= min_required:
            experience_score = 90
        elif max_resume_years >= min_required - 1:
            experience_score = 70
        else:
            experience_score = 40
    elif resume_years:
        experience_score = 60

    # Weighted final score
    final_score = round(
        skill_score * 0.40 +
        description_score * 0.30 +
        experience_score * 0.30
    )

    # Generate summary
    if final_score >= 80:
        summary = 'Excellent match! The candidate demonstrates strong alignment with the job requirements.'
    elif final_score >= 60:
        summary = 'Good match. The candidate meets most of the key requirements for this role.'
    elif final_score >= 40:
        summary = 'Partial match. The candidate has some relevant skills but may lack key requirements.'
    else:
        summary = 'Low match. The candidate does not meet the primary requirements for this role.'

    return {
        'score': min(100, max(0, final_score)),
        'skill_match': round(skill_score),
        'experience_match': round(experience_score),
        'description_match': round(description_score),
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'summary': summary
    }
