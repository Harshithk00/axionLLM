import json
import os
from groq import Groq
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = Flask(__name__)

def evaluate_with_ai(questions: list, user_answers: dict):
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
        return {}




@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.get_json()
    questions = data.get('questions', [])
    user_answers = data.get('userAnswers', {})

    if not questions or not user_answers:
        return jsonify({"error": "Invalid input"}), 400

    evaluation_result = evaluate_with_ai(questions, user_answers)

    if not evaluation_result:
        return jsonify({"error": "Failed to evaluate"}), 500

    return jsonify(evaluation_result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)