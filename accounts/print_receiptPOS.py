import sys
import json
import win32print
import requests
from datetime import datetime


def get_philippines_time(fallback_time=None, timeout=1.5):
    try:
        response = requests.get(
            "http://worldtimeapi.org/api/timezone/Asia/Manila", timeout=timeout
        )
        if response.status_code == 200:
            return response.json()["datetime"]
    except requests.exceptions.Timeout:
        print("Request timed out. Using fallback time.")
    except Exception as e:
        print(f"An error occurred: {e}. Using fallback time.")

    return fallback_time if fallback_time else "Could not get time"


# Ensure print_data is passed as an argument
if len(sys.argv) < 2:
    print(
        "Error: No print data provided. Please pass JSON data as a command-line argument."
    )
    sys.exit(1)

# Get the print data from the command-line argument
print_data = json.loads(sys.argv[1])

# Extract fallback_time from print_data
fallback_time = print_data.get("fallback_time")
current_time = get_philippines_time(fallback_time)

# Proceed with the rest of the printing logic using current_time
datetime_obj = datetime.strptime(current_time[:19], "%Y-%m-%dT%H:%M:%S")
formatted_date = datetime_obj.strftime("%a, %b %d, %Y")
formatted_time = datetime_obj.strftime("%I:%M %p")

printer_name = "POS58 v9"
hprinter = win32print.OpenPrinter(printer_name)
job = win32print.StartDocPrinter(hprinter, 1, ("Receipt", None, "RAW"))
win32print.StartPagePrinter(hprinter)

# Command to open the cash drawer
cash_drawer_command = b"\x1B\x70\x00\x19\xFA"  # ESC p 0 25 250
win32print.WritePrinter(hprinter, cash_drawer_command)

max_width = 32  # Adjusted width for a 58mm thermal printer
header1 = " Universal Auto Supply and Bolt".center(max_width)
header2 = "Center".center(max_width)
header3 = "Cagayan de Oro, Philippines".center(max_width)

win32print.WritePrinter(hprinter, f"{header1}\n".encode("utf-8"))
win32print.WritePrinter(hprinter, f"{header2}\n".encode("utf-8"))
win32print.WritePrinter(hprinter, f"{header3}\n".encode("utf-8"))

for _ in range(2):
    win32print.WritePrinter(hprinter, b"\n")

# Print cashier name
cashier = print_data.get("cashier", "Unknown Cashier")
win32print.WritePrinter(hprinter, f"Cashier: {cashier}\n".encode("utf-8"))

# Add the POS system information
pos_system = "POS: KiosCorp POS"
win32print.WritePrinter(hprinter, f"{pos_system}\n".encode("utf-8"))

for _ in range(1):
    win32print.WritePrinter(hprinter, b"\n")

# Continue with the order details
order_id = print_data.get("order_id", "Unknown Order ID")
order_status = print_data.get("order_status", "Unknown Status")
paid_amount = print_data.get("paid_amount", 0.0)
change = print_data.get("change", 0.0)

win32print.WritePrinter(hprinter, f"Order ID: {order_id}\n".encode("utf-8"))
win32print.WritePrinter(hprinter, f"Status: {order_status}\n".encode("utf-8"))
win32print.WritePrinter(hprinter, f"Date: {formatted_date}\n".encode("utf-8"))
win32print.WritePrinter(hprinter, f"Time: {formatted_time}\n".encode("utf-8"))
win32print.WritePrinter(hprinter, b"\n")
win32print.WritePrinter(hprinter, "Item Name          Qty    Price\n".encode("utf-8"))
win32print.WritePrinter(hprinter, "--------------------------------\n".encode("utf-8"))

# Print the items
items = print_data.get("items", [])
num_items = len(items)

for index, item in enumerate(items):
    name = item["product"]["product_name"].ljust(19)[:19]
    quantity = str(item["quantity"]).rjust(1)
    price = item["product"]["product_price"]  # This should now be a float
    color = item["color"]  # Adjust width as needed
    size = item["size"]  # Adjust width as needed

    # Print the item details
    win32print.WritePrinter(
        hprinter, f"{name} {quantity}  {price:7.2f}\n".encode("utf-8")
    )
    win32print.WritePrinter(hprinter, f"({color},{size})\n".encode("utf-8"))

    # Add a blank line *after* the item, except for the last item
    if index < num_items - 1:  # Only if it's not the last item
        win32print.WritePrinter(hprinter, b"\n")

# After printing all items, add a separator line
win32print.WritePrinter(hprinter, "--------------------------------\n".encode("utf-8"))

# Extract total from print_data
total = float(print_data.get("total", 0.0))  # Default to 0.0 if not found
subtotal = float(print_data.get("subtotal", 0.0))  # Get subtotal from print_data
vat_percentage = float(print_data.get("vat_percentage", 0))  # Get VAT percentage
vat_amount = subtotal * (vat_percentage / 100)  # Calculate VAT amount

# Print the subtotal, VAT, and total
win32print.WritePrinter(
    hprinter, f"Subtotal:          {subtotal:11.2f}\n".encode("utf-8")
)
win32print.WritePrinter(
    hprinter, f"VAT {vat_percentage}%:         {vat_amount:11.2f}\n".encode("utf-8")
)
win32print.WritePrinter(hprinter, f"Total:             {total:11.2f}\n".encode("utf-8"))

# Add a few new lines for spacing
for _ in range(2):
    win32print.WritePrinter(hprinter, b"\n")

# Print paid amount and change below the total
win32print.WritePrinter(hprinter, f"Cash: {paid_amount:.2f}\n".encode("utf-8"))
win32print.WritePrinter(hprinter, f"Change: {change:.2f}\n".encode("utf-8"))

# Add a few new lines for spacing
for _ in range(2):
    win32print.WritePrinter(hprinter, b"\n")

# Print the thank you message
thank_you = "Thank you for your purchase!".center(max_width)
win32print.WritePrinter(hprinter, f"{thank_you}\n".encode("utf-8"))

for _ in range(1):
    win32print.WritePrinter(hprinter, b"\n")

# Add the disclaimer about the receipt
win32print.WritePrinter(hprinter, "<------------------------------>\n".encode("utf-8"))
disclaimer1 = "Please note that this is not an".center(max_width)
win32print.WritePrinter(hprinter, f"{disclaimer1}\n".encode("utf-8"))
disclaimer2 = "official receipt".center(max_width)
win32print.WritePrinter(hprinter, f"{disclaimer2}\n".encode("utf-8"))
win32print.WritePrinter(hprinter, "<------------------------------>\n".encode("utf-8"))

for _ in range(1):
    win32print.WritePrinter(hprinter, b"\n")

powered_by = "Powered by KiosCorp".center(max_width)
win32print.WritePrinter(hprinter, f"{powered_by}\n".encode("utf-8"))

# Add a few new lines for spacing
for _ in range(4):
    win32print.WritePrinter(hprinter, b"\n")

# End the printing process
win32print.EndPagePrinter(hprinter)
win32print.EndDocPrinter(hprinter)
win32print.ClosePrinter(hprinter)

print("Receipt printed successfully and cash drawer opened.")
