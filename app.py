from flask import Flask, request, jsonify, render_template
import pg8000
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


if __name__ == '__main__':
    app.run(debug=True)
