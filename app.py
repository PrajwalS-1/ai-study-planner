from flask import Flask, render_template, request, send_file
import random

# ML IMPORTS
from sklearn.neighbors import KNeighborsRegressor
import numpy as np

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# ================= ML MODEL =================
def train_knn():
    # Features: [difficulty, number of topics]
    X = np.array([
        [1, 2],   # Easy
        [2, 3],   # Medium
        [3, 4],   # Hard
        [1, 1],
        [2, 2],
        [3, 5]
    ])

    # Target: study time
    y = np.array([1, 2, 3, 1, 2, 4])

    model = KNeighborsRegressor(n_neighbors=2)
    model.fit(X, y)
    return model

knn_model = train_knn()


# Predict time using ML
def predict_time(diff, num_topics):
    if diff == "Easy":
        d = 1
    elif diff == "Medium":
        d = 2
    else:
        d = 3

    prediction = knn_model.predict([[d, num_topics]])
    return round(float(prediction[0]), 1)


# ================= AI LOGIC =================
def generate_plan(subjects, topics, difficulties, total_days, hours):
    plan = []

    structured = []
    for sub, tpcs, diff in zip(subjects, topics, difficulties):
        topic_list = [t.strip() for t in tpcs.split(',')]
        structured.append({
            "subject": sub,
            "topics": topic_list,
            "difficulty": diff
        })

    # Priority: Hard → Medium → Easy
    priority = {"Hard": 3, "Medium": 2, "Easy": 1}
    structured.sort(key=lambda x: priority[x["difficulty"]], reverse=True)

    # Track last used topic index for variation
    topic_index = {item["subject"]: 0 for item in structured}

    for d in range(total_days):
        day_plan = []

        for item in structured:
            sub = item["subject"]
            diff = item["difficulty"]
            topics_list = item["topics"]

            # 🔄 Rotate topics (ensures different each day)
            idx = (topic_index[sub] + d) % len(topics_list)
            topic = topics_list[idx]

            # 🔁 Spaced repetition (only for hard)
            if diff == "Hard" and d % 2 == 1:
                topic = topic + " (Revision)"

            # 🤖 ML prediction
            time = predict_time(diff, len(topics_list))

            # ⚡ Smart break
            if time >= 2:
                topic_display = f"{sub} - {topic} (+10 min break)"
            else:
                topic_display = f"{sub} - {topic}"

            day_plan.append((topic_display, time))

        plan.append(day_plan)

    # 🔥 FINAL RANDOMNESS → makes regenerate work
    for day in plan:
        random.shuffle(day)

    return plan

# ================= PDF =================
def create_pdf(plan):
    file_path = "study_plan.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []

    # Title
    content.append(Paragraph("AI STUDY PLANNER REPORT", styles['Title']))
    content.append(Paragraph("Generated using ML (KNN Model)", styles['Normal']))

    for i, day in enumerate(plan):
        content.append(Paragraph(f"<br/>Day {i+1}", styles['Heading2']))

        for t in day:
            content.append(Paragraph(f"{t[0]} - {t[1]} hrs", styles['Normal']))

    doc.build(content)
    return file_path


# ================= ROUTES =================
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/planner', methods=['GET', 'POST'])
def planner():
    if request.method == 'POST':
        subjects = request.form.getlist('subjects')
        topics = request.form.getlist('topics')
        difficulties = request.form.getlist('difficulty')
        hours = int(request.form['hours'])

        duration = int(request.form['duration'])
        dtype = request.form['duration_type']

        if dtype == 'Weeks':
            total_days = duration * 7
        elif dtype == 'Months':
            total_days = duration * 30
        else:
            total_days = duration

        plan = generate_plan(subjects, topics, difficulties, total_days, hours)

        return render_template('result.html',
                               plan=plan,
                               subjects=subjects,
                               topics=topics,
                               difficulties=difficulties,
                               duration=duration,
                               dtype=dtype,
                               hours=hours)

    return render_template('planner.html')


@app.route('/regenerate', methods=['POST'])
def regenerate():
    subjects = request.form.getlist('subjects')
    topics = request.form.getlist('topics')
    difficulties = request.form.getlist('difficulty')
    hours = int(request.form['hours'])

    duration = int(request.form['duration'])
    dtype = request.form['duration_type']

    if dtype == 'Weeks':
        total_days = duration * 7
    elif dtype == 'Months':
        total_days = duration * 30
    else:
        total_days = duration

    plan = generate_plan(subjects, topics, difficulties, total_days, hours)

    return render_template('result.html',
                           plan=plan,
                           subjects=subjects,
                           topics=topics,
                           difficulties=difficulties,
                           duration=duration,
                           dtype=dtype,
                           hours=hours)


@app.route('/download', methods=['POST'])
def download():
    plan = eval(request.form['plan'])
    file_path = create_pdf(plan)
    return send_file(file_path, as_attachment=True)


# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)