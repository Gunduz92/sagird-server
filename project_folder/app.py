from flask import Flask, render_template, request, jsonify
import sys
import io
import openai
import os

openai.api_key = os.getenv("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")

def get_chatgpt_hint(code_text, error_text):
    prompt = f"""Mənə aşağıdakı Python kodunun səhvini başa sal və düzgün yazmaq üçün ipucu ver.
Kod:
{code_text}

Səhv mesajı:
{error_text}

Yalnız qısa və sadə ipucu ver: məsələn, hansı operator səhvdir, input formatı düzgün deyil və s.
"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )
    return response['choices'][0]['message']['content'].strip()





app = Flask(__name__)

# Tapşırıqları description.txt faylından oxuyuruq
def load_tasks():
    with open('tasks/task1/description.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    sections = content.split('#TASK')
    tasks = []
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
            'tests': tests
        })
    return tasks

@app.route('/')
def index():
    tasks = load_tasks()
    return render_template('index.html', tasks=tasks)

@app.route('/check', methods=['POST'])
def check_code():
    data = request.get_json()
    user_code = data['code']
    task_id = int(data['task_id'])

    tasks = load_tasks()
    task = tasks[task_id]

    results = []

    for test in task['tests']:
        input_data = test['input']
        expected_output = test['output']

        inputs = input_data.strip().split('\n')

        try:
            old_stdout = sys.stdout
            sys.stdout = mystdout = io.StringIO()

            def fake_input():
                return inputs.pop(0)

            exec_globals = {'input': fake_input}
            exec(user_code, exec_globals)

            sys.stdout.seek(0)
            user_output = mystdout.getvalue().strip()

            if user_output == expected_output:
                results.append(True)
            else:
                results.append(False)

        except Exception as e:
            results.append(False)

        finally:
            sys.stdout = old_stdout

    return jsonify(results=results)

if __name__ == '__main__':
    app.run(debug=True)
