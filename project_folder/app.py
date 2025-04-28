import os
from flask import Flask, render_template, request, jsonify
import sys
import io
import openai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

def load_tasks():
    base_dir = 'tasks'
    tasks = []
    categories = []

    for category_folder in os.listdir(base_dir):
        category_path = os.path.join(base_dir, category_folder)
        description_file = os.path.join(category_path, 'description.txt')

        if os.path.isdir(category_path) and os.path.exists(description_file):
            categories.append(category_folder)
            with open(description_file, 'r', encoding='utf-8') as f:
                content = f.read()

            sections = content.split('#TASK')
            for section in sections:
                if section.strip() == "":
                    continue
                parts = section.strip().split('#TESTS')
                description = parts[0].strip()
                tests_raw = parts[1].strip().split('#NEWTEST')

                tests = []
                for test in tests_raw:
                    if test.strip():
                        test_parts = test.strip().split('#OUTPUT')
                        input_data = test_parts[0].strip()
                        output_data = test_parts[1].strip()
                        tests.append({'input': input_data, 'output': output_data})

                tasks.append({
                    'description': description,
                    'category': category_folder,
                    'tests': tests
                })

    return tasks, categories

def get_chatgpt_hint(code_text, error_text):
    prompt = f"""Python kodu səhv verir. Xətanın səbəbini aydın və qısa izah et və şagirdə ipucu ver:
Kod:
{code_text}

Səhv:
{error_text}

Yalnız qısa və sadə ipucu ver."""
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )
    return response['choices'][0]['message']['content'].strip()

@app.route('/')
def index():
    tasks, categories = load_tasks()
    return render_template('index.html', tasks=tasks, categories=categories)

@app.route('/check', methods=['POST'])
def check_code():
    data = request.get_json()
    user_code = data['code']
    task_id = int(data['task_id'])

    tasks, categories = load_tasks()
    task = tasks[task_id]

    test_results = []

    for idx, test in enumerate(task['tests']):
        input_data = test['input']
        expected_output = test['output']

        inputs = input_data.strip().split('\n')

        try:
            def fake_input():
                return inputs.pop(0)

            old_stdout = sys.stdout
            sys.stdout = mystdout = io.StringIO()

            exec_globals = {'input': fake_input}
            exec(user_code, exec_globals)

            sys.stdout.seek(0)
            user_output = mystdout.getvalue().strip()

            is_correct = user_output == expected_output

            test_results.append({
                'correct': is_correct,
                'user_output': user_output,
                'expected_output': expected_output,
                'test_index': idx,
                'code': user_code
            })

        except Exception as e:
            test_results.append({
                'correct': False,
                'user_output': "Xəta baş verdi.",
                'expected_output': expected_output,
                'test_index': idx,
                'error_message': str(e),
                'code': user_code
            })

        finally:
            sys.stdout = old_stdout

    return jsonify(results=test_results)

@app.route('/hint', methods=['POST'])
def hint():
    data = request.get_json()
    expected_output = data['expected_output']
    user_output = data['user_output']
    error_message = data.get('error_message', '')
    user_code = data['code']

    if error_message:
        hint_text = get_chatgpt_hint(user_code, error_message)
    else:
        hint_text = get_chatgpt_hint(user_code, f"Çıxış fərqlidir. Gözlənilən: {expected_output}, Verilən: {user_output}")

    return jsonify(hint=hint_text)

if __name__ == '__main__':
    app.run(debug=True)
