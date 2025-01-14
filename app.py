from flask import Flask, request, jsonify,render_template, current_app as app
from chat import Chatbot
import mysql.connector
from state import shared_state

app = Flask(__name__)
chatbot = Chatbot()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    response = chatbot.handle_input(user_input)
    return jsonify({"response": response})

@app.route('/login.html', methods=["GET"])
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def loginn():
    data = request.json
    account_number = data.get('account_number')
    password = data.get('password')
    
    if not account_number or not password:
        return jsonify({'message': 'Account Number and password are required'}), 400
    
    # Connect to database
    connection = mysql.connector.connect(host = 'localhost', user = 'root', database = 'bankserver')
    cursor = connection.cursor()
    cursor.execute("select password from users where account_number = %s", (account_number,))
    result = cursor.fetchall()
    connection.close()
    
    if result is None:
        return jsonify({'message': 'User not found'}), 404
    
    
    # Verify the password
    if result[0][0]==password:
        shared_state.state='authenticated'
        shared_state.account_number = account_number
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/sign-up.html', methods=["GET"])
def signup():
    return render_template('sign-up.html')

@app.route('/sign-up', methods=['POST'])
def signupp():
    data = request.json
    fullname = data.get('fullname')
    email = data.get('email')
    account_number = data.get('account_number')
    password = data.get('password')
    confirm_password = data.get('confirmpassword')
    print(password,confirm_password)

    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    try:
        conn = mysql.connector.connect(host = 'localhost', user = 'root', database = 'bankserver')
        cursor = conn.cursor()
        cursor.execute('''insert into users (fullname, email, account_number, password) values (%s,%s,%s,%s)''',(fullname,email,account_number,password))
        conn.commit()
        conn.close()
        return jsonify({"message": "User registered successfully"}), 200
    except Exception:
        print(Exception)
        return jsonify({"message": "Username or email already exists"}), 400

if __name__ == "__main__":
    app.run(debug=True)
