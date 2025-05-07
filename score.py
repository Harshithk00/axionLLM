# import json
# import os
# from groq import Groq
# from flask import Flask, request, jsonify
# from dotenv import load_dotenv

# load_dotenv()
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# app = Flask(__name__)

# def evaluate_with_ai(questions: list, user_answers: dict):
#     prompt = f"""
# You are an AI evaluator. You are given a list of questions (both MCQ and Subjective), each with correct answers or expected keywords. You are also given a student's answers. Evaluate the student's performance.

# Instructions:
# - For each MCQ: compare user's answer with the correct one. Award 1 point if correct, 0 if wrong.
# - For each Subjective: compare user's answer with expected keywords. Score between 0 and 1. If the score is < 0.69, consider the question a weak topic.
# - Return total score, max score, percentage, list of weak topics, and list of wrong MCQ answers.

# Respond only in this JSON format:
# {{
#   "score": float,
#   "maxScore": int,
#   "percentage": float,
#   "weakTopics": [
#     {{
#       "question": string,
#       "whatiswrong": [string]
#     }}
#   ],
#   "wrongMcqAnswers": [
#     {{
#       "question": string,
#       "yourAnswer": string,
#       "correctAnswer": string
#     }}
#   ]
# }}

# Questions:
# {json.dumps(questions)}

# User Answers:
# {json.dumps(user_answers)}
# """

#     response = client.chat.completions.create(
#         model="llama3-8b-8192",
#         messages=[
#             {"role": "system", "content": "You are a strict but fair evaluator. Respond only in JSON."},
#             {"role": "user", "content": prompt}
#         ]
#     )

#     result = response.choices[0].message.content.strip()

#     try:
#         return json.loads(result)
#     except json.JSONDecodeError:
#         print("Error parsing AI response:", result)
#         return {}




# @app.route('/evaluate', methods=['POST'])
# def evaluate():
#     data = request.get_json()
#     questions = data.get('questions', [])
#     user_answers = data.get('userAnswers', {})

#     if not questions or not user_answers:
#         return jsonify({"error": "Invalid input"}), 400

#     evaluation_result = evaluate_with_ai(questions, user_answers)

#     if not evaluation_result:
#         return jsonify({"error": "Failed to evaluate"}), 500

#     return jsonify(evaluation_result)


# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5002, debug=True)


import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Try to use Groq if API key is available, otherwise prepare for a fallback
try:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    AI_SERVICE = "groq"
except (ImportError, TypeError):
    AI_SERVICE = "fallback"
    print("Warning: Groq API key not found or module not installed. Using fallback evaluation.")

def fallback_evaluate(questions, user_answers):
    """Fallback evaluation if AI service is not available"""
    calculatedScore = 0
    weakTopics = []
    wrongMcqAnswers = []
    
    for q in questions:
        if q["type"] == "mcq":
            user_answer = user_answers.get(str(q["id"]))
            if user_answer == q["correctAnswer"]:
                calculatedScore += 1
            else:
                weakTopics.append({
                    "question": q["text"],
                    "whatiswrong": ["Incorrect answer selection"]
                })
                wrongMcqAnswers.append({
                    "question": q["text"],
                    "yourAnswer": user_answer if user_answer else "No answer",
                    "correctAnswer": q["correctAnswer"]
                })
        elif q["type"] == "subjective":
            answer = user_answers.get(str(q["id"]), "")
            keywords_found = 0
            missing_keywords = []
            
            for keyword in q.get("expectedKeywords", []):
                if keyword.lower() in answer.lower():
                    keywords_found += 1
                else:
                    missing_keywords.append(keyword)
            
            percentage_found = keywords_found / len(q.get("expectedKeywords", [])) if q.get("expectedKeywords") else 0
            
            if percentage_found >= 0.7:
                calculatedScore += 1
            else:
                weakTopics.append({
                    "question": q["text"],
                    "whatiswrong": [f"Missing key concepts: {', '.join(missing_keywords)}"]
                })
    
    total_questions = len(questions)
    percentage = (calculatedScore / total_questions) * 100 if total_questions > 0 else 0
    
    return {
        "score": calculatedScore,
        "maxScore": total_questions,
        "percentage": percentage,
        "weakTopics": weakTopics,
        "wrongMcqAnswers": wrongMcqAnswers
    }

def evaluate_with_ai(questions, user_answers):
    """Evaluate using Groq LLM API"""
    prompt = f"""
You are an AI evaluator. You are given a list of questions (both MCQ and Subjective), each with correct answers or expected keywords. You are also given a student's answers. Evaluate the student's performance.

Instructions:
- For each MCQ: compare user's answer with the correct one. Award 1 point if correct, 0 if wrong.
- For each Subjective: compare user's answer with expected keywords. Score between 0 and 1. If the score is < 0.69, consider the question a weak topic.
- Return total score, max score, percentage, list of weak topics, and list of wrong MCQ answers.

Respond only in this JSON format:
{{
  "score": float,
  "maxScore": int,
  "percentage": float,
  "weakTopics": [
    {{
      "question": string,
      "whatiswrong": [string]
    }}
  ],
  "wrongMcqAnswers": [
    {{
      "question": string,
      "yourAnswer": string,
      "correctAnswer": string
    }}
  ]
}}

Questions:
{json.dumps(questions)}

User Answers:
{json.dumps(user_answers)}
"""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are a strict but fair evaluator. Respond only in JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content.strip()

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            print("Error parsing AI response:", result)
            return fallback_evaluate(questions, user_answers)
    except Exception as e:
        print(f"Error with AI service: {e}")
        return fallback_evaluate(questions, user_answers)

@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.get_json()
    questions = data.get('questions', [])
    user_answers = data.get('answers', {})  # Changed from userAnswers to answers to match frontend

    if not questions or not user_answers:
        return jsonify({"error": "Invalid input"}), 400

    # Use AI evaluation if available, otherwise use fallback
    if AI_SERVICE == "groq":
        evaluation_result = evaluate_with_ai(questions, user_answers)
    else:
        evaluation_result = fallback_evaluate(questions, user_answers)

    return jsonify(evaluation_result)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "service": AI_SERVICE})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)