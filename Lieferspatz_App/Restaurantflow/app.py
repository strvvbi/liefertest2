import sqlite3
import random
from flask import Flask, session, render_template, request, g, redirect, url_for
from datetime import datetime, time

app = Flask(__name__)
app.secret_key = "123456"
app.config['SESSION_TYPE'] = 'filesystem'

#connecting the sqlite3 database to the application
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('lieferspatz2.db')
    return db
                              

#terminating our database connection once we're done using it
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

        
#filtering the restaurants for zipCode and openingTimes 
def restaurant_list():
    user_zip_code = session["user"][4]
    current_time = datetime.now().time()

    cursor = get_db().cursor()
    cursor.execute("select id, name, details, deliveryRadius, openingTime, closingTime from restaurants")
    session["all_data"] = cursor.fetchall()

    session["filtered_restaurants"] = []

    for restaurant in session["all_data"]: 
        delivery_radius_zip_codes = list(map(int, restaurant[3].split(', ')))
        opening_time_str = restaurant[4]
        closing_time_str = restaurant[5]
        opening_time = datetime.strptime(opening_time_str, "%H:%M").time()
        closing_time = datetime.strptime(closing_time_str, "%H:%M").time()
        if int(user_zip_code) in delivery_radius_zip_codes and opening_time <= current_time <= closing_time:
            session["filtered_restaurants"].append((restaurant[0], restaurant[1], restaurant[2]))
    return session["filtered_restaurants"]

def get_menu_items_grouped(restaurant_id):
    cursor = get_db().cursor()
    cursor.execute("select * from menu_items where restaurant_id=? and status is null order by category, id", (restaurant_id,))
    session["menu_items"] = cursor.fetchall()

    items_vorspeise = [item for item in session["menu_items"] if item[5] == 'Vorspeise']
    items_hauptspeise = [item for item in session["menu_items"] if item[5] == 'Hauptspeise']
    items_nachspeise = [item for item in session["menu_items"] if item[5] == 'Nachspeise']
    items_getraenke = [item for item in session["menu_items"] if item[5] == 'Getränk']
    return items_vorspeise, items_hauptspeise, items_nachspeise, items_getraenke 

def get_restaurant_name(restaurant_id):
    cursor = get_db().cursor()
    cursor.execute("select name from restaurants where id=?", (restaurant_id,))
    restaurant = cursor.fetchone()
    session["restaurant_name"] = restaurant[0]
    return session["restaurant_name"] if restaurant else None 

def get_restaurant_id(restaurant_id):
    cursor = get_db().cursor()
    cursor.execute("select id from restaurants where id=?", (restaurant_id,))
    restaurant = cursor.fetchone()
    session["restaurant_id"] = restaurant[0]
    return session["restaurant_id"] if restaurant else None 

def add_to_orders(item_id, quantity):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("insert into orders_test (item_id, quantity) values (?,?)", (item_id, quantity))
    db.commit

def calculate_total_price(items):
    total_price = sum(item['price'] * item['quantity'] for item in items)
    return total_price

@app.route("/start")
def index(): 
	return render_template("homepage.html")

@app.route("/homepage", methods=['GET', 'POST'])
def home():
	if request.method == 'POST':
		if request.form.get('registerClientBtn') == "Als Kunde registrieren":
			return redirect(url_for("create_client_account"))
		elif request.form.get('loginClientBtn') == "Als Kunde anmelden":
			return redirect(url_for("login_client"))
		elif request.form.get('registerRestaurantBtn') == "Als Restaurant registrieren":
			return redirect(url_for("create_restaurant_account"))
		elif request.form.get('loginRestaurantBtn') == "Als Restaurant anmelden":
			return redirect(url_for("login_restaurant"))
	else: 
		return redirect(url_for("home"))
		

@app.route("/registerClient", methods=["POST", "GET"])
def create_client_account():
	if request.method == "POST":
		connection = sqlite3.connect('lieferspatz2.db')
		cursor = connection.cursor()

		cursor.execute("create table if not exists client_accounts (id integer primary key autoincrement, forname text, lastname text, address text, zipCode text, username text, password text)")
		first_name = request.form['firstName']
		last_name = request.form['lastName']
		address = request.form['address']
		zip_Code = request.form['zipCode']
		username = request.form['username']
		password = request.form['password']

		cursor.execute("insert into client_accounts (forname, lastname, address, zipCode, username, password) values (?,?,?,?,?,?)", (first_name, last_name, address, zip_Code, username, password))

		connection.commit()
		connection.close()

		return redirect(url_for("login_client"))
	else:
		return render_template("registerClient.html")
	
@app.route("/loginClient", methods=["POST", "GET"])
def login_client():
	if request.method == "POST":
		session.permanent = True
		connection = sqlite3.connect('lieferspatz2.db')
		cursor = connection.cursor()

		username = request.form['username']
		password = request.form['password']

		cursor.execute("select * from client_accounts where username == ? and password == ?", (username,  password))
		result = cursor.fetchone()
		connection.commit()
		connection.close()

		if result:
			session["user"] = result
			return redirect(url_for("login_confirmation"))
		else:
			return redirect(url_for("login_confirmation_false"))	
		
	else:
		return render_template("loginClient.html")	


@app.route("/registerRestaurant", methods=["POST", "GET"])
def create_restaurant_account():
	if request.method == 'POST':
		connection = sqlite3.connect('lieferspatz2.db')
		cursor = connection.cursor()

		cursor.execute("create table if not exists restaurants (id integer primary key autoincrement, name text, address text, zipCode text, details text, deliveryRadius text, openingTime text, closingTime text, userName text, password text)")
		restaurant_name = request.form['restaurantName']
		address = request.form['address']
		zip_Code = request.form['zipCode']
		deliveryRadius = request.form['servedArea']
		openingTime = request.form['openFrom']
		closingTime = request.form['openUntil']  
		details = request.form['description']
		username = request.form['username']
		password = request.form['password']

		cursor.execute("insert into restaurants (name, address, zipCode, details, deliveryRadius, openingTime, closingTime, userName, password) values (?,?,?,?,?,?,?,?,?)", (restaurant_name, address, zip_Code, details, deliveryRadius, openingTime, closingTime, username, password))

		connection.commit()
		connection.close()

		return redirect(url_for("login_restaurant"))
	else:
		return render_template("registerRestaurant.html")

@app.route("/loginRestaurant", methods=["POST", "GET"])
def login_restaurant():
	if request.method == 'POST':
		session.permanent = True
		connection = sqlite3.connect('lieferspatz2.db')
		cursor = connection.cursor()

		username = request.form['username']
		password = request.form['password']

		cursor.execute("select * from restaurants where userName == ? and password == ?", (username, password))
		result = cursor.fetchone() 
		connection.commit()
		connection.close()

		if result:
			session["restaurantuser"] = result
			return redirect(url_for("login_confirmation_restaurant"))  #Link zur Login Confirmation
		else:
			return redirect(url_for("login_confirmation_false_restaurant"))
	else:
		return render_template("loginRestaurant.html")

@app.route("/loginconfirmation")
def login_confirmation():
      return render_template("loginconfirmation.html", login_success=True)

@app.route("/loginconfirmationfalse")
def login_confirmation_false():
      return render_template("loginconfirmation.html", login_success=False)

def number_of_new_orders():
    restaurant_id = session["restaurantuser"][0]
    status = "in Bearbeitung"
    db = get_db()
    cursor = db.cursor()
    cursor.execute("select * from orders where restaurant_id=? and status=?", (restaurant_id, status))
    result = cursor.fetchall()
    number = len(result)
    db.commit()
    db.close()
    return number    

@app.route("/loginconfirmationrestaurant")
def login_confirmation_restaurant():
    number = number_of_new_orders()

    if number > 0:
        return render_template("loginconfirmationrestaurant.html", login_success=True, new_orders=True, number=number)
    else:
        return render_template("loginconfirmationrestaurant.html", login_success=True, new_orders=False)


@app.route("/loginconfirmationfalserestaurant")
def login_confirmation_false_restaurant():
      return render_template("loginconfirmationrestaurant.html", login_success=False)

@app.route("/restaurants")
def restaurants():
    session["filtered_restaurants"] = restaurant_list()
    return render_template("restaurants.html", restaurant_data = session["filtered_restaurants"])

@app.route("/menu/<int:restaurant_id>", methods=['GET', 'POST'])
def menu(restaurant_id):
    items_vorspeise, items_hauptspeise, items_nachspeise, items_getraenke = get_menu_items_grouped(restaurant_id)
    session["restaurant_name"] = get_restaurant_name(restaurant_id)
    session["restaurant_id"] = get_restaurant_id(restaurant_id)

    categories = []
    if items_vorspeise:
        categories.append(('Vorspeise', items_vorspeise))
    if items_hauptspeise:
        categories.append(('Hauptspeise', items_hauptspeise))
    if items_nachspeise:
        categories.append(('Nachspeise', items_nachspeise))
    if items_getraenke:
        categories.append(('Getränke', items_getraenke))

    if request.method == 'POST':
        for category, items in categories:
            for item in items:
                quantity_key = 'quantity' + str(item[0])
                quantity = int(request.form.get(quantity_key, 0))
                if quantity > 0:
                    add_to_orders(item[0], quantity)

    return render_template(
        "menu.html",
        categories=categories, 
        restaurant_name=session["restaurant_name"], 
        restaurant_id=restaurant_id,
        get_menu_items_grouped=get_menu_items_grouped)
    

@app.route("/add_to_cart", methods=['POST'])
def add_to_cart():
    if request.method == 'POST':
        session ["restaurant_id"] = request.form.get('restaurant_id')
        restaurant_id = session["restaurant_id"]
        menu_items = get_menu_items_grouped(restaurant_id)
        client_id = session["user"][0]                            #client id aus der Session einsetzen!!!

        selected_items = []

        for category_items in menu_items:
            for item in category_items:
                item_id = request.form.get('item_id{}'.format(item[0]))
                quantity_key = 'quantity{}'.format(item[0])
                quantity = int(request.form.get(quantity_key, 0))  

                if quantity > 0:
                    selected_items.append({
                        'item_id': item_id,
                        'quantity': quantity, 
                        'name': item[2],
                        'price': item[3]
                    }) 
        
        total_price = calculate_total_price(selected_items)
        session['selected_items'] = selected_items
        session['total_price'] = total_price

        return redirect('/cart')

@app.route("/cart")
def cart():
    selected_items = session.get('selected_items', [])
    total_price = session.get('total_price', 0)
    return render_template("cart.html", selected_items=selected_items, restaurant_name = session["restaurant_name"], total_price=total_price)

@app.route("/update_cart", methods=['POST'])
def update_cart():
    if request.method == 'POST':
        action = request.form.get('action')
        item_id = request.form.get('item_id')
        selected_items = session.get('selected_items', [])

        for item in selected_items:
            if item['item_id'] == item_id:
                if action == 'increase':
                    item['quantity'] += 1
                elif action == 'decrease':
                    if item['quantity'] > 1:
                        item['quantity'] -= 1
                    else: 
                        selected_items.remove(item)
                elif action == 'remove':
                    selected_items.remove(item)

        total_price = calculate_total_price(selected_items)   
        session['selected_items'] = selected_items             
        session['total_price'] = total_price

        return redirect('/cart')
    
@app.route("/submit_order", methods=['POST'])
def submit_order():
    if request.method == 'POST':
        client_id = session["user"][0]                #session variable eingeben
        restaurant_id = session ["restaurant_id"]

        current_datetime = datetime.now()
        order_date_str = current_datetime.strftime("%d.%m.%Y")
        order_time_str = current_datetime.strftime("%H:%M")
        status = "in Bearbeitung"

        order_comment = request.form.get('order_comment', '')

        cursor = get_db().cursor()
        cursor.execute("insert into orders (client_id, restaurant_id, orderDate, orderTime, status, comment) values (?, ?, ?, ?, ?, ?)", (client_id, restaurant_id, order_date_str, order_time_str, status, order_comment))
        order_id = cursor.lastrowid

        selected_items = session.get('selected_items', [])

        for item in selected_items:
            item_id = item['item_id']
            quantity = item['quantity']

            cursor.execute("insert into order_content (order_id, item_id, quantity) values (?, ?, ?)", (order_id, item_id, quantity))
        
        
        get_db().commit()
        cursor.close()

        session.pop('selected_items', None)
        session.pop('total_price', None)

        return render_template("confirmation.html")

@app.route("/clientorderoverview")
def client_order_overview():
    if request.method == 'POST' and request.form.get('logoutBtn') == 'Logout':
          session.pop('user', None)
          return redirect(url_for('index'))
    
    client_id = session["user"][0]                   #client id aus der session schreiben!

    cursor = get_db().cursor()
    cursor.execute(""" select orders.id, restaurants.name, orders.orderDate, orders.orderTime, orders.status
                   from orders
                   join restaurants on orders.restaurant_id = restaurants.id
                   where orders.client_id = ?
                   order by 
                        case
                            when orders.status = 'in Bearbeitung' then 1
                            when orders.status = 'in Zubereitung' then 2
                            else 3
                        end,
                        orders.orderDate DESC, orders.orderTime DESC""", (client_id,))
    order_data = cursor.fetchall()
    cursor.close()

    return render_template("clientorderoverview.html", order_data = order_data)

@app.route("/restaurantorderoverview")
def restaurant_order_overview():
    if request.method == 'POST' and request.form.get('logoutBtn') == 'Logout':
          session.pop('user', None)
          return redirect(url_for('index'))
    
    client_id = session["restaurantuser"][0]                   #restaurant id aus der session schreiben!

    cursor = get_db().cursor()
    cursor.execute(""" select orders.id, orders.client_id, orders.orderDate, orders.orderTime, orders.status
                   from orders
                   join restaurants on orders.restaurant_id = restaurants.id
                   where orders.restaurant_id = ?
                   order by 
                        case
                            when orders.status = 'in Bearbeitung' then 1
                            when orders.status = 'in Zubereitung' then 2
                            else 3
                        end,
                        orders.orderDate DESC, orders.orderTime DESC""", (client_id,))
    order_data = cursor.fetchall()
    cursor.close()

    return render_template("restaurantorderoverview.html", order_data = order_data)


@app.route("/restaurantMenu", methods=['GET', 'POST'])
def restaurant_menu():
    restaurant_id = session["restaurantuser"][0] 
    items_vorspeise, items_hauptspeise, items_nachspeise, items_getraenke = get_menu_items_grouped(restaurant_id)
    session["restaurant_name"] = get_restaurant_name(restaurant_id)
    session["restaurant_id"] = get_restaurant_id(restaurant_id)

    categories = []
    if items_vorspeise:
        categories.append(('Vorspeise', items_vorspeise))
    if items_hauptspeise:
        categories.append(('Hauptspeise', items_hauptspeise))
    if items_nachspeise:
        categories.append(('Nachspeise', items_nachspeise))
    if items_getraenke:
        categories.append(('Getränke', items_getraenke))
                
    return render_template(
        "restaurantMenu.html",
        categories=categories, 
        restaurant_name=session["restaurant_name"], 
        restaurant_id=restaurant_id,
        get_menu_items_grouped=get_menu_items_grouped)

@app.route("/addToMenu", methods=['POST','GET'])
def add_to_menu():   
    if request.method == 'POST':
        restaurant_id = session["restaurantuser"][0]
        restaurant_name=session["restaurant_name"]

        db = get_db()
        cursor = db.cursor()

        item_name = request.form['itemName']
        price = request.form['price']
        description = request.form['description']
        category = request.form['category']
        cursor.execute("insert into menu_items (restaurant_id, name, price, description, category) values (?,?,?,?,?)", (restaurant_id, item_name, price, description, category))

        db.commit()
        db.close()

        return redirect(url_for('restaurant_menu'))
    else:
         return render_template(
            "addToMenu.html",
            restaurant_name=session["restaurant_name"])


@app.route("/update_menu", methods=['POST'])
def update_menu():
    if request.method == 'POST':
        action = request.form.get('action')
        item_id = request.form.get('item_id')
        session["item_id"] = item_id

        if action == 'change':
            return redirect(url_for('change_item'))
        elif action == 'remove':
            remove_from_menu(item_id)

    return redirect(url_for('restaurant_menu'))
    
@app.route("/remove_from_menu", methods=['GET', 'POST'])
def remove_from_menu(item_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("update menu_items set status = 'deleted' where id=?", (item_id,))

    db.commit()
    db.close()    
      
    return redirect(url_for('restaurant_menu'))

def get_item(item_id):
    cursor = get_db().cursor()
    cursor.execute("select * from menu_items where id=?", (item_id,))
    item = cursor.fetchone()
    session["item"] = item
    return session["item"] if item else None 

@app.route("/changeItem", methods=['GET', 'POST'])
def change_item():
    restaurant_id = session["restaurantuser"][0]
    restaurant_name=session["restaurant_name"]
    item_id = session["item_id"]
    item = get_item(item_id)
    
    if request.method == 'POST':

        db = get_db()
        cursor = db.cursor()

        cursor.execute("update menu_items set status = 'changed' where id=?", (item_id,))

        item_name = request.form['itemName']
        price = request.form['price']
        description = request.form['description']
        category = request.form['category']
        cursor.execute("insert into menu_items (restaurant_id, name, price, description, category) values (?,?,?,?,?)", (restaurant_id, item_name, price, description, category))

        db.commit()
        db.close() 

        return redirect(url_for('restaurant_menu'))
    else:
         return render_template(
            "changeItem.html",
            restaurant_name=session["restaurant_name"],
            item=item)
    
#Anzeige der Bestelldetails
@app.route("/order_details/<int:order_id>")
def order_details_route(order_id):
    cursor = get_db().cursor()
    cursor.execute("""
    SELECT menu_items.name, menu_items.price, menu_items.description, menu_items.category,
           order_content.quantity, orders.orderDate, orders.orderTime, orders.status, orders.comment, orders.id
    FROM orders
    JOIN order_content ON orders.id = order_content.order_id
    JOIN menu_items ON order_content.item_id = menu_items.id
    WHERE orders.id = ?""", (order_id,))
    order_details = cursor.fetchall()
    cursor.close()

    return render_template("order_details.html", details= order_details)

from flask import request


#Status der Bestellung ändern 
@app.route("/statusupdate", methods=["POST"])
def handle_status_update():
    action = request.form.get("action")
    order_id = request.form.get("order_id")
    print(f"Received POST request with action: {action}, order_id: {order_id}")

    if action == "Annehmen":
        accept_order(order_id)
    elif action == "Ablehnen":
        reject_order(order_id)
    elif action == "Versandt":
        finish_order(order_id)

    return render_template("statusupdate.html")

# Status auf in Zubereitung setzen
def accept_order(order_id):
        connection = sqlite3.connect('lieferspatz2.db')
        cursor = connection.cursor()
        print(order_id)
        cursor.execute("UPDATE orders SET status = 'in Zubereitung' WHERE id = ?", (order_id,))
        connection.commit()
        connection.close()

#Status auf storniert setzen
def reject_order(order_id):
        connection = sqlite3.connect('lieferspatz2.db')
        cursor = connection.cursor()
        cursor.execute("UPDATE orders SET status = 'Storniert' WHERE id = ?", (order_id,))
        connection.commit()
        connection.close()

#Status auf Abgeschlossen setzen
def finish_order(order_id):
        connection = sqlite3.connect('lieferspatz2.db')
        cursor = connection.cursor()
        cursor.execute("UPDATE orders SET status = 'Abgeschlossen' WHERE id = ?", (order_id,))
        connection.commit()
        connection.close()

if __name__ == '__main__':
	app.run(debug=True)

