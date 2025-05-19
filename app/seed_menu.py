from app import app, db, MenuItem

with app.app_context():
    sample_items = [
        MenuItem(name="Margherita Pizza", price=9.99, description="Classic cheese pizza with basil."),
        MenuItem(name="BBQ Burger", price=11.49, description="Beef burger with BBQ sauce and onion rings."),
        MenuItem(name="Caesar Salad", price=7.99, description="Romaine lettuce with creamy Caesar dressing."),
        MenuItem(name="Sushi Platter", price=14.99, description="Assorted sushi rolls with soy sauce."),
        MenuItem(name="Pasta Carbonara", price=12.49, description="Creamy pasta with bacon and parmesan."),
    ]
    db.session.bulk_save_objects(sample_items)
    db.session.commit()
    print("✔ Sample menu items added.")
