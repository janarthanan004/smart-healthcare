from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session
import joblib
from database import get_connection

def generate_description(disease):
    return f"{disease} is a medical condition that may require proper diagnosis and treatment. Please consult a healthcare professional for detailed evaluation and management."


app = Flask(__name__)
app.secret_key = "secret"

model = joblib.load('model.pkl')

@app.route('/appointment')
def appointment():
    if 'user_id' not in session:
        return redirect('/login')

    patient_id = session['user_id']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.name, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_id DESC
        LIMIT 1
    """, (patient_id,))

    appointment = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("appointment.html", appointment=appointment)



# Home
@app.route('/')
def index():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO patients (name,email,password) VALUES (%s,%s,%s)",
            (name,email,password)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/login')

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM patients WHERE email=%s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            return redirect('/dashboard')

    return render_template('login.html')

@app.route('/history')
def history():
    patient_id = session['user_id']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.name, d.specialization, a.appointment_date
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.patient_id = %s
    """, (patient_id,))

    history = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('history.html', history=history)

@app.route('/admin', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM admin WHERE username=%s", (username,))
        admin = cursor.fetchone()

        if admin and check_password_hash(admin[2], password):
            session['admin'] = True
            return redirect('/admin_dashboard')

    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM patients")
    total_patients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template('admin_dashboard.html',
                           total_patients=total_patients,
                           total_appointments=total_appointments)

@app.route('/add_doctor', methods=['GET','POST'])
def add_doctor():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        experience = request.form['experience']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO doctors (name,specialization,experience) VALUES (%s,%s,%s)",
            (name,specialization,experience)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/admin_dashboard')

    return render_template('add_doctor.html')


# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    symptoms = joblib.load("symptom_list.pkl")
    return render_template("dashboard.html",
                           symptoms=symptoms)


# prediction
@app.route('/predict', methods=['POST'])
def predict():

    if 'user_id' not in session:
        return redirect('/login')

    symptom_list = joblib.load("symptom_list.pkl")

    input_vector = [0] * len(symptom_list)
    selected_symptoms = request.form.getlist('symptoms')

    # Minimum symptom validation
    if len(selected_symptoms) < 2:
        return render_template("dashboard.html",
                               symptoms=symptom_list,
                               error="Please select at least 2 symptoms")

    # Encode symptoms
    for symptom in selected_symptoms:
        if symptom in symptom_list:
            index = symptom_list.index(symptom)
            input_vector[index] = 1

    # Prediction
    prediction = model.predict([input_vector])[0]
    probabilities = model.predict_proba([input_vector])[0]

    confidence = round(max(probabilities) * 100, 2)
    max_prob = confidence

    # Store disease in session (IMPORTANT for doctors page)
    session['disease'] = prediction

    # If confidence too low
    if max_prob < 30:
        return render_template("prediction.html",
                               disease="Prediction Uncertain",
                               description="The selected symptoms are insufficient to generate a reliable diagnosis.",
                               risk="Low Confidence - Please consult a doctor",
                               top3=[],
                               confidence=confidence)

    # Risk classification
    if max_prob > 70:
        risk = "High Risk"
    elif max_prob > 40:
        risk = "Moderate Risk"
    else:
        risk = "Low Risk"

    # Top 3 diseases
    top3_indices = probabilities.argsort()[-3:][::-1]
    top3 = [(model.classes_[i], round(probabilities[i] * 100, 2))
            for i in top3_indices]

    description = generate_description(prediction)

    return render_template("prediction.html",
                           disease=prediction,
                           description=description,
                           risk=risk,
                           top3=top3,
                           confidence=confidence)

# Show Doctors
@app.route('/doctors')
def doctors():
    disease = session.get('disease')

    if disease == "Heart Disease":
        specialization = "Cardiologist"
    elif disease in ["Flu","Cold"]:
        specialization = "General Physician"
    else:
        specialization = "Dermatologist"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM doctors WHERE specialization=%s",
        (specialization,)
    )

    doctors = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('doctors.html', doctors=doctors)

@app.route('/book/<int:doctor_id>')
def book(doctor_id):
    if 'user_id' not in session:
        return redirect('/login')

    patient_id = session['user_id']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO appointments (patient_id, doctor_id) VALUES (%s,%s)",
        (patient_id, doctor_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/appointment')

@app.route('/confirm_appointment', methods=['POST'])
def confirm_appointment():
    if 'user_id' not in session:
        return redirect('/login')

    doctor_id = request.form['doctor_id']
    patient_id = session['user_id']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO appointments (patient_id, doctor_id) VALUES (%s,%s)",
        (patient_id, doctor_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return render_template("appointment.html", success=True)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
