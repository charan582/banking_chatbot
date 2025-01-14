from nltk.corpus import stopwords
import nltk
from nltk.stem import WordNetLemmatizer
import smtplib
import numpy as np
import joblib
import map
import pandas as pd
import mysql.connector
from state import shared_state
from sklearn.feature_extraction.text import TfidfVectorizer
import re
import random
import string
import otp


class IntentRecognizer:
    def __init__(self):
        self.intents = {
            "greet": ["hello", "hi", "hey"],
            "goodbye": ["bye", "goodbye", "see you"],
            "authenticate": ["login", "authenticate", "sign in"],
            "balance_inquiry": ["balance", "check balance"],
            "transfer": ["transfer", "send money"],
            "log_out":["logout","sign out"],
            "transaction":["transaction","history","transaction history"],
            "loan_status":['loan sanction','loan status','sanctioned', 'loan'],
            "status":['account status','active','locked','working','status'],
            "bank_add":["bank address",'nearest bank','atm','nearest','address'],
            'info':['account info','information','account information','account details','details of account']
        }
        
    def recognize_intent(self, user_input):
        # for intent, keywords in self.intents.items():
        #     if any(keyword in user_input.lower() for keyword in keywords):
        #         return intent
        # else:
        #     return self.predict_intent(user_input.lower())
        return self.predict_intent(user_input.lower())
    
    # log_reg_model = joblib.load('chatbot_intent_classifier.pkl')
    # label_encoder = joblib.load('label_encoder.pkl')

    # nlp = spacy.load("en_core_web_md")

    # def get_spacy_embeddings(self,texts):
    #     return np.array([self.nlp(text).vector for text in texts])


    def predict_intent(self,user_input):
        # user_embedding = self.get_spacy_embeddings([user_input])
        svm_model = joblib.load('models/svm_model_final.joblib')
        vectorizer = joblib.load('models/vectorizer_final.joblib')
        X_train_tfidf = vectorizer.transform([user_input])
        predicted_label = svm_model.predict(X_train_tfidf)
        predicted_prob = svm_model.predict_proba(X_train_tfidf)
        intent_score = predicted_prob[0][predicted_label[0]]
        print(predicted_label,intent_score)
        # predicted_intent = self.label_encoder.inverse_transform(predicted_label)

        return map.intent_map[predicted_label[0]] if intent_score >0.4 else 'unknown'

# ir = IntentRecognizer()
# print(ir.predict_intent('Hello'))


class Chatbot:
    def __init__(self):
        self.intent_recognizer = IntentRecognizer()
        self.account_number = None
        self.password = None
        self.topup_state = None
        self.acc_number = None
        self.amount = None
        self.pin = None
        self.otp_storage = {}

    def extract_entities(self, user_input):
        date_pattern = r'\b(\d{1,2}-\d{1,2}-\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b'
        date_match = re.search(date_pattern, user_input)

        count_pattern = r'\b(previous|last|recent)\s(\d+)\stransactions\b'
        count_match = re.search(count_pattern, user_input, re.IGNORECASE)

        transaction_date = None
        if date_match:
            transaction_date = date_match.group(0)

        transaction_count = None
        if count_match:
           transaction_count = int(count_match.group(2))
           print(transaction_count)

        return transaction_date, transaction_count
    
    def extract_transfer_details(self, user_input):
        # Pattern to match amount in formats like "500", "500.50", "Rs 500", etc.
        amount_pattern = r'\b(Rs\.?\s?|₹)?(\d+(\.\d{1,2})?)\b'
        amount_match = re.search(amount_pattern, user_input, re.IGNORECASE)

        # Pattern to match account number (assuming 8 to 16 digit account numbers)
        acc_number_pattern = r'\b\d{8,16}\b'
        acc_number_match = re.search(acc_number_pattern, user_input)

        # Extract amount
        amount = None
        if amount_match:
            amount = float(amount_match.group(2))  # Extract numeric value

        # Extract account number
        acc_number = None
        if acc_number_match:
            acc_number = acc_number_match.group(0)

        return amount, acc_number
    
    def calculate_emi(self, principal, annual_rate, tenure_years):
        monthly_rate = annual_rate / 12 / 100
        months = tenure_years * 12
        emi = (principal * monthly_rate * (1 + monthly_rate)*months) / ((1 + monthly_rate)*months - 1)
        return round(emi, 2)

    def handle_input(self, user_input):
        intent = self.intent_recognizer.recognize_intent(user_input) if not user_input.isdigit() else None
        self.account_number = shared_state.account_number
        print(intent)
        
        if shared_state.state == "start" and intent == "authenticate":
            shared_state.state = "awaiting_account_number"
            return "Please enter your Account Number."
        
        elif shared_state.state == "awaiting_account_number":
            shared_state.account_number = user_input
            shared_state.state = "awaiting_password"
            return "Please enter your password."
        
        elif shared_state.state == "awaiting_password":
            self.password = user_input
            authenticated = self.authenticate_user(self.account_number, self.password)
            if authenticated:
                shared_state.state = "authenticated"
                return "Authentication successful! How can I assist you today?"
            else:
                shared_state.state = "start"
                return "Authentication failed. Please try again."
            
        elif shared_state.state == "authenticated" and intent == "authenticate":
            return "You are already logged in. How can I assist you today?"
        
        elif intent == "greet":
            return "Hello! How can I help you with your banking needs today?"
        
        elif intent == "goodbye":
            return "Goodbye! Have a great day."
        
        elif intent == "top_up_limits":
            self.topup_state="awaiting_account_type"
            return "Enter your account type."
        
        elif self.topup_state == "awaiting_account_type" and user_input=='savings account':
            self.topup_state = None
            return "The daily top-up limit is 50,000 rupees."
        
        elif self.topup_state == "awaiting_account_type" and user_input=='business account':
            self.topup_state = None
            return "The daily top-up limit is unlimited."
        
        elif intent == "balance_inquiry":
            if shared_state.state == "authenticated":
                result = self.fetch_data(self.account_number,"select balance from users where account_number = %s")
                return f"Your bank balance is Rs. {result[0][0]}" if result != -1 else "The server is currently down."
            else:
                return "Please log in to check your balance."
                    
        elif user_input == 'logout' or (shared_state.state == "authenticated" and intent == "log_out"):
            shared_state.state = "start"
            return "You are succesfully Logged out"
        
        elif shared_state.state == "authenticated" and intent == "transaction":
            self.transaction_date, self.transaction_count = self.extract_entities(user_input)
            if "transactions of" in user_input or re.search(r'\b(\d{1,2}-\d{1,2}-\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b', user_input):
                result = self.fetch_datat(self.account_number, self.transaction_date)
                output = f"Transaction Id    Date    Recipient    Type    Amount\n"
                for i in range(len(result)):
                    output += f"{result[i][2]}    {result[i][4]}    {result[i][1]}      {result[i][5]}    {result[i][3]}\n"
                return output
            elif "previous" in user_input or "last" in user_input:
                result = self.fetch_datat(self.account_number, None, self.transaction_count)
                output = f'''Transaction_Id    Date    Recipient    Type    Amount\n'''
                for i in range(len(result)):
                    output += f"\n{result[i][2]}    {result[i][4]}    {result[i][1]}      {result[i][5]}    {result[i][3]}\n"
                return output
            else:
                result = self.fetch_datat(self.account_number)
                print(result)
                return f'''Transaction Id    Date    Recipient    Type    Amount
{result[0][2]}    {result[0][4]}    {result[0][1]}      {result[0][5]}    {result[0][3]}''' if result != -1 else "The server is currently down."

        elif shared_state.state == "authenticated" and intent == "status":
            result = self.fetch_data(self.account_number,"select account_status from users where account_number = %s")
            return f"Your bank account is {result[0][0]}" if result != -1 else "The server is currently down."

        elif shared_state.state == "authenticated" and intent == "loan_status":
            result = self.fetch_data(self.account_number,"select loan_status from loans where account_number = %s")
            return f"Your loan status is {result[0][0]}" if result != -1 else "The server is currently down."
        
        elif shared_state.state == "authenticated" and intent == "loan_amt":
            result = self.fetch_data(self.account_number,"select * from loans where account_number = %s")
            result.append(self.calculate_emi(result[0][-3],result[0][-1],result[0][-2]))
            print(result)
            return f"Your Outstanding amount is Rs.{result[0][3]} and the EMI is Rs.{result[1]}" if result != -1 else "The server is currently down."
        
        elif shared_state.state == "authenticated" and intent == "loan_doc":
            return f"The required documents are \n AADHAR CARD\nPAN CARD\nINCOME PROOF(Salary Slips)\nPASSPORT SIZED PHOTOGRAPHS" 
        
        elif shared_state.state == "authenticated" and intent == "bank_add":
            result = self.fetch_data(self.account_number,"select bank_add from users where account_number = %s")
            return f"Your bank address is {result[0][0]}" if result != -1 else "The server is currently down."
        
        elif shared_state.state == "authenticated" and intent == "info":
            result = self.fetch_data(self.account_number,"select fullname,email,account_number,account_status,balance,bank_add from users where account_number = %s")
            print(result)
            return f'''Name          : {result[0][0]}
Email         : {result[0][1]}
Account Number: {result[0][2]}            
Account Status: {result[0][3]}
Balance       : Rs.{result[0][4]}
Bank Address  : {result[0][5]}
''' if result != -1 else "The server is currently down."
        
        elif shared_state.state == "authenticated" and intent == "transfer":
            self.state = None
            self.amount, self.acc_number = self.extract_transfer_details(user_input)
            if not self.acc_number:
                shared_state.state = "awaiting_recipient_acc_num"
                return "Enter the recipient account number"
            elif not self.amount:
                shared_state.state = "awaiting_amount"
                return "Enter the amount in numbers"
            shared_state.state = "awaiting_pin"
            return "Enter the card pin"
        
        elif shared_state.state == "awaiting_recipient_acc_num":
            self.acc_number = user_input
            shared_state.state = "awaiting_amount"
            return "Enter the amount in number"
        
        elif shared_state.state == "awaiting_amount":
            if re.search(r'\b(Rs\.?\s?|₹)?(\d+(\.\d{1,2})?)\b', user_input, re.IGNORECASE):
                self.amount = user_input
                shared_state.state = "awaiting_pin"
                return "Enter the card pin"
            return "Enter the amount in number format"

        elif shared_state.state == "awaiting_pin":
            self.pin = user_input
            shared_state.state = "awaiting_otp"
            return otp.send_otp(shared_state.account_number)

        elif shared_state.state == "awaiting_otp":
            check,message = otp.verify_otp(shared_state.account_number, int(user_input))
            if check:
                shared_state.state = "authenticated"
                return self.transfer_money(shared_state.account_number, self.acc_number, self.amount, self.pin)
            return message

        elif intent in map.intent_responses:
            return map.intent_responses[intent]

        elif intent != 'unknown' and intent not in map.intent_responses:
            return "You are not authenticated. Please authenticate."

        else:
            return "I'm sorry, I didn't understand that. Could you please rephrase?"

    def authenticate_user(self, account_number, password):
        try:
            mydb = mysql.connector.connect(host = 'localhost', user = 'root', database = 'bankserver')
        except:
            return False
        else:
            mycursor = mydb.cursor()
            mycursor.execute("select password from users where account_number = %s", (account_number,))
            result = mycursor.fetchall()
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
            if result:
                return password == result[0][0]
            return False
        
    def fetch_datat(self, account_number, transaction_date=None, transaction_count=None, query="SELECT * FROM transactions WHERE account_number = %s AND trans_status = %s "):
        try:
            mydb = mysql.connector.connect(host='localhost', user='root', database='bankserver')
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return -1
        else:
            try:
                mycursor = mydb.cursor()

                if transaction_date:
                    query += " AND trans_date = %s"
                    mycursor.execute(query, (account_number, 'Successful', transaction_date))
                elif transaction_count:
                    query += " ORDER BY trans_date DESC LIMIT %s"
                    mycursor.execute(query, (account_number, 'Successful', transaction_count))
                else:
                    mycursor.execute(query, (account_number, 'Successful',))

                result = mycursor.fetchall()
                return result

            except mysql.connector.Error as err:
                print(f"Query Execution Error: {err}")
                return -1

            finally:
                if mydb.is_connected():
                    mycursor.close()
                    mydb.close()

    def fetch_data(self, account_number, query):
        try:
            mydb = mysql.connector.connect(host = 'localhost', user = 'root', database = 'bankserver')
        except:
            return -1
        else:
            mycursor = mydb.cursor()
            mycursor.execute(query,(account_number,))

            result = mycursor.fetchall()
            if mydb.is_connected():
                mycursor.close()
                mydb.close()
            return result
        
    def transfer_money(self, account_s, account_r, amount, pin):
        try:
            mydb = mysql.connector.connect(host='localhost', user='root', database='bankserver')
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return -1
        else:
            try:
                mycursor = mydb.cursor()

                mycursor.execute("SELECT pin, card_status FROM cards WHERE account_number = %s", (account_s,))
                db_pin = mycursor.fetchone()

                if db_pin[0] != int(pin):
                    return "The entered pin is incorrect. Please enter the correct pin."

                mycursor.execute("SELECT balance FROM users WHERE account_number = %s", (account_s,))
                sender_balance = mycursor.fetchone()

                if sender_balance is None:
                    return "Sender account does not exist."

                sender_balance = sender_balance[0]

                mycursor.execute("SELECT account_status FROM users WHERE account_number = %s", (account_r,))
                recipient_status = mycursor.fetchone()

                if recipient_status is None:
                    return "Recipient account does not exist."

                recipient_status = recipient_status[0]

                if sender_balance < int(amount) or recipient_status != 'active' or db_pin[1] != 'Active':
                    mycursor.execute("INSERT INTO transactions (account_number, from_to, trans_id, trans_amt, trans_date, trans_type, trans_status) "
            "VALUES (%s, %s, %s, %s, NOW(), 'debit', 'Failed')",
            (account_s, account_r, self.generate_transaction_id(), amount))
                    mydb.commit()
                    return "Insufficient funds to complete the transfer." if sender_balance < int(amount) else "Transaction Failed. Try again Later.\nThe recipient account is inactive."

                # Deduct amount from sender and update the balance
                mycursor.execute("UPDATE users SET balance = balance - %s WHERE account_number = %s", (amount, account_s))

                # Add amount to recipient and update the balance
                mycursor.execute("UPDATE users SET balance = balance + %s WHERE account_number = %s", (amount, account_r))

                trans_id = self.generate_transaction_id()

                mycursor.execute("INSERT INTO transactions (account_number, from_to, trans_id, trans_amt, trans_date, trans_type, trans_status) "
            "VALUES (%s, %s, %s, %s, NOW(), 'debit', 'Successful')",
            (account_s, account_r, trans_id, amount))
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login("1da21cs040.cs@drait.edu.in", "lkgyxthfjgbjboya")
                    message = f"Subject: Amount debited\n\nAn amount of Rs. {amount} has been debited fromn your account.\nThe transaction ID id {trans_id}."
                    server.sendmail("1da21cs040.cs@drait.edu.in", 'charandatta582@gmail.com', message)
                    server.quit()
                new_id = self.generate_transaction_id()
                mycursor.execute("INSERT INTO transactions (account_number, from_to, trans_id, trans_amt, trans_date, trans_type, trans_status) "
            "VALUES (%s, %s, %s, %s, NOW(), 'credit', 'Successful')",
            (account_r, account_s, new_id, amount))
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login("1da21cs040.cs@drait.edu.in", "lkgyxthfjgbjboya")
                    message = f"Subject: Amount credited\n\nAn amount of Rs. {amount} has been credited fromn your account.\nThe transaction ID id {new_id}."
                    server.sendmail("1da21cs040.cs@drait.edu.in", 'bharathbk5401@gmail.com', message)
                    server.quit()
                mydb.commit()

                mycursor.execute("select balance from users where account_number = %s",(account_s,))
                bal= mycursor.fetchone()
                
                return f"Transaction Successful\nAn amount of Rs. {amount} has been debited.\nThe transaction id is {trans_id}.\nYour current balance is Rs. {bal[0]}"

            except mysql.connector.Error as err:
                print(f"Query Execution Error: {err}")
                return -1

            finally:
                if mydb.is_connected():
                    mycursor.close()
                    mydb.close()

    def generate_transaction_id(self, length=10):
        # Generate a random alphanumeric string of the specified length
        characters = string.ascii_letters + string.digits
        transaction_id = ''.join(random.choices(characters, k=length))
        return transaction_id


cb = Chatbot()
print(cb.handle_input('Check balance'))

