import json
import re
from flask import Flask, request, jsonify
import os
from groq import Groq
from dotenv import load_dotenv
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)

load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_json_from_response(text):
    """Extract JSON from text that might contain markdown or other text."""
    # Look for JSON between curly braces
    json_pattern = r'\{.*\}'
    match = re.search(json_pattern, text, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    # If that fails, try to find JSON between triple backticks
    code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    
    for block in code_blocks:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue
    
    return None

def generate_questions_and_answers(text):
    prompt = f"""
    You are an AI academic assistant. Based on the given text, generate the following:
    
    1. 10 multiple-choice questions (MCQs) with 4 answer choices each, and mark the correct answer.
    2. 5 subjective questions with answers.
    
    Your response MUST be valid JSON in the following format with no additional text:
    {{
    "questions": [
        {{
            "id": 1,
            "type": "mcq",
            "text": "Your question here?",
            "options": [
                {{"id": "a", "text": "Option A"}},
                {{"id": "b", "text": "Option B"}},
                {{"id": "c", "text": "Option C"}},
                {{"id": "d", "text": "Option D"}}
            ],
            "correctAnswer": "b"
        }},
        {{
            "id": 11,
            "type": "subjective",
            "text": "Your question here?",
            "expectedKeywords": ["keyword1", "keyword2", "keyword3"]
        }}
        ]
    }}
    
    Text:
    {text}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are a helpful study assistant. Return only valid JSON with no additional text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}  # Request JSON format if supported by the model
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try parsing JSON directly
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON
            extracted_json = extract_json_from_response(content)
            if extracted_json:
                return extracted_json
            
            # If extraction fails, return a structured error
            return {
                "error": "Invalid JSON from model",
                "raw_response": content[:1000]  # Limit the raw response size
            }
    
    except Exception as e:
        return {"error": str(e)}

@app.route('/generate_questions', methods=['POST'])
def generate_questions():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400
    
    text = data.get("text", "")
    
    if not text.strip():
        return jsonify({"error": "No text provided."}), 400
    
    result = generate_questions_and_answers(text)
    
    if "error" in result:
        return jsonify(result), 500
    
    return jsonify({
        "status": "success",
        "data": result
    }), 200

# Add health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)