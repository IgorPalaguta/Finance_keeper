from datetime import datetime

from flask import Flask, request, jsonify, render_template
import os 
import pg8000
import openai
from openai import OpenAI
import ssl

app = Flask(__name__)

# 🔒 Параметри підключення до Neon.tech
DB_CONFIG = {
    "user": "neondb_owner",
    "password": "npg_bHOf6c4hyoez",
    "host": "ep-dawn-cell-a2r98rv7-pooler.eu-central-1.aws.neon.tech",
    "database": "finance_bot",
    "ssl_context": ssl.create_default_context()
}


# 🔌 Функція підключення до бази PostgreSQL
def get_db_connection():
    conn = pg8000.connect(**DB_CONFIG)
    return conn

# 📌 Головна сторінка
@app.route('/')
def index():
    return render_template('index.html')

# 📌 Сторінка додавання категорії (отримує user_id)
@app.route('/add_category')
def add_category_page():
    user_id = request.args.get('user_id', '')
    return render_template('add_category.html', user_id=user_id)

@app.route('/add_spends')
def add_spends_page():
    return render_template('add_spends.html')

@app.route('/stats_check')
def stats_check_page():
    return render_template('stats_check.html')

@app.route('/add_budget')
def add_budget_page():
    return render_template('add_budget.html')

# 📥 Обробка POST-запиту на додавання категорії
@app.route('/add_category', methods=['POST'])
def add_category():
    import pg8000
    import ssl

    data = request.json
    user_id = data.get('user_id')
    category_name = data.get('category')

    if not user_id or not category_name:
        return jsonify({"message": "❌ Введіть user_id і назву категорії!"}), 400

    try:
        conn = pg8000.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM categories WHERE user_id = %s AND name = %s", (int(user_id), category_name))
        if cursor.fetchone():
            conn.close()
            return jsonify({"message": "⚠️ Категорія вже існує!"}), 400

        cursor.execute("INSERT INTO categories (user_id, name) VALUES (%s, %s)", (int(user_id), category_name))
        conn.commit()
        conn.close()

        return jsonify({"message": "✅ Категорія додана успішно!"})
    except Exception as e:
        print("Помилка підключення:", e)
        return jsonify({"message": "❌ Помилка сервера!"}), 500
@app.route('/get_categories')
def get_categories():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"categories": []}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories WHERE user_id = %s", (int(user_id),))
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({"categories": categories})
    except Exception as e:
        print("Помилка при отриманні категорій:", e)
        return jsonify({"categories": []}), 500


# 📥 Додавання витрат
@app.route('/add_expense', methods=['POST'])
def add_expense():
    data = request.json
    user_id = data.get('user_id')
    category = data.get('category')
    amount = data.get('amount')
    comment = data.get('comment', '')
    date = datetime.now().strftime('%Y-%m-%d')

    if not user_id or not category or not amount:
        return jsonify({"message": "❌ Усі поля обов’язкові!"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Додати витрату
        cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (%s, %s, %s, %s)",
            (int(user_id), float(amount), category, date)
        )

        # 2. Зменшити бюджет
        cursor.execute(
            "UPDATE budgets SET amount = amount - %s WHERE user_id = %s",
            (float(amount), int(user_id))
        )

        conn.commit()
        conn.close()
        return jsonify({"message": "✅ Витрату успішно додано та бюджет оновлено!"})

    except Exception as e:
        print("Помилка при додаванні витрати:", e)
        return jsonify({"message": "❌ Помилка сервера!"}), 500
        
@app.route("/get_expenses")
def get_expenses():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"expenses": []}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, amount FROM expenses
            WHERE user_id = %s ORDER BY date DESC LIMIT 10
        """, (int(user_id),))
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"expenses": [{"category": r[0], "amount": r[1]} for r in rows]})
    except Exception as e:
        print("❌ Помилка отримання витрат:", e)
        return jsonify({"expenses": []}), 500
        
@app.route("/set_budget", methods=["POST"])
def set_budget():
    data = request.json
    telegram_id = data.get("user_id")  # Це telegram_id користувача
    amount = data.get("amount")

    if not telegram_id or not amount:
        return jsonify({"message": "❌ Не передано user_id або суму"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Перевірка чи існує користувач з таким telegram_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (int(telegram_id),))
        result = cursor.fetchone()

        if result:
            user_id = result[0]
        else:
            # Якщо не існує — додаємо користувача
            cursor.execute("INSERT INTO users (telegram_id) VALUES (%s) RETURNING id", (int(telegram_id),))
            user_id = cursor.fetchone()[0]

        # 2. Вставка або оновлення бюджету
        cursor.execute("""
            INSERT INTO budgets (user_id, amount)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET amount = EXCLUDED.amount
        """, (user_id, float(amount)))

        conn.commit()
        conn.close()

        return jsonify({"message": "✅ Бюджет збережено"})
    except Exception as e:
        print("❌ Бюджет помилка:", e)
        return jsonify({"message": "❌ Серверна помилка"}), 500


@app.route("/get_budget")
def get_budget():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"budget": 0}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT amount FROM budgets WHERE user_id = %s", (int(user_id),))
        row = cursor.fetchone()
        conn.close()
        return jsonify({"budget": row[0] if row else 0})
    except Exception as e:
        print("❌ Бюджет отримання:", e)
        return jsonify({"budget": 0}), 500
        
@app.route('/get_expense_stats')
def get_expense_stats():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"expenses": []})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, category, amount FROM expenses
        WHERE user_id = %s
        ORDER BY date DESC
    """, (int(user_id),))
    rows = cursor.fetchall()
    conn.close()

    expenses = [{"date": r[0], "category": r[1], "amount": float(r[2])} for r in rows]
    return jsonify({"expenses": expenses})


@app.route('/ai_advice')
def ai_advice():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"advice": "❌ user_id не передано"})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = %s AND date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY category
            ORDER BY total DESC
        """, (int(user_id),))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return jsonify({"advice": "ℹ️ Немає витрат для аналізу."})

        expense_summary = "\n".join([f"{row[0]}: {row[1]} ₴" for row in rows])

        prompt = f"""
Проаналізуй витрати користувача за останній місяць і запропонуй 3 поради щодо покращення його фінансової поведінки. Ось дані:
{expense_summary}

Формат відповіді:
1. ...
2. ...
3. ...
        """

        client = OpenAI(
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )

        chat_completion = client.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )

        advice = chat_completion.choices[0].message.content
        return jsonify({"advice": advice})

    except Exception as e:
        print("❌ GPT Error:", e)
        return jsonify({"advice": "⚠️ Не вдалося отримати пораду."})


if __name__ == '__main__':
    app.run(debug=True)
