import json

class TechStoreInventory:

    def __init__(self, store):
        self.store = store
        self.inventory = []
        self.total = 0

    def add_product(self, name, stock, unitprice):
        product = {"name": name, "stock": stock, "unitprice": unitprice}
        self.inventory.append(product)
        # Sort by stock in descending order
        self.inventory.sort(key=lambda x: x["stock"], reverse=True)

    def inventory_total_value(self):
        # Calculate total value cleanly
        self.total = sum(
            data["stock"] * data["unitprice"] for data in self.inventory
        )

        print("\n" + "=" * 55)
        print(f" STORE: '{self.store}' | TOTAL INVENTORY VALUE: ${self.total:,.2f}")
        print("=" * 55)
        print(" INDEXED PRODUCTS (Sorted by Stock):")
        for i, display in enumerate(self.inventory, 1):
            subtotal = display["stock"] * display["unitprice"]
            print(
                f"  {i}. {display['name']:<12} | Stock: {display['stock']:<5} | Unit: ${display['unitprice']:<5} | Subtotal: ${subtotal}"
            )
        print("=" * 55)

    def save(self, file_name):
        if not file_name.endswith(".json"):
            file_name += ".json"

        # Structured dictionary report for JSON
        report_data = {
            "store": self.store,
            "total_inventory_value": self.total,
            "inventory": self.inventory,
        }

        with open(file_name, "w", encoding="utf-8") as archivo:
            json.dump(report_data, archivo, indent=4, ensure_ascii=False)
        print(f"File saved correctly as '{file_name}'")


# --- TEST ---
program = TechStoreInventory("2049 Store")
program.add_product("CPU", 1100, 15)
program.add_product("Laptop", 900, 55)
program.add_product("Monitor ", 250, 300)

program.inventory_total_value()
program.save("inventory_report")