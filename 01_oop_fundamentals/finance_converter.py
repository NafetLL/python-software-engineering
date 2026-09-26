class Finance:

    def __init__(self):
        self.products = []

    def ingress(self, **register):
        self.products.append(register)

    def convert_to_soles(self):
        for product in self.products:
            # Loop for convert and update the value
            for name, price_usd in list(product.items()):
                price_pen = round(price_usd * 3.75, 2)
                # Saving the soles version in the dictionary
                product[f"{name}_soles"] = price_pen

    def display(self):
        print("\n FINANCE REGISTER + CONVERSION:")
        print("-" * 45)
        for i, product in enumerate(self.products, 1):
            for key, value in product.items():
                if "_soles" in key:
                    original_name = key.replace("_soles", "")
                    usd_val = product[original_name]
                    print(
                    f"{i}. {original_name:<12} | USD ${usd_val:<6} -> S/. {value}"
                    )
        print("-" * 45)
        print (self.products)


if __name__ == "__main__":
    initiation = Finance()
    initiation.ingress(HpLaptop=555, WirelessMouse=25.5)
    initiation.convert_to_soles()
    initiation.display()