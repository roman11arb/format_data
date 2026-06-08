# 1. Make the script so it can take data as a prop
# 2. Make a function that verifys the existance of folders with that data
# 3. Run the script from a .bat file
# 4. The function shall return true or false
# 5. Check file mny, mtdvolfeed, pos, st4

import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

path_origin = os.getenv("Reporting-Data")
files_to_check = ["mny", "mtdvolfeed", "pos", "st4"]
file_path = "Data_Temporary/Wedbush/FTP"


def validate_date():
    while True:
        date = input("Enter the date (YYYYMMDD): ")

        try:
            datetime.strptime(date, "%Y%m%d")
            break
        except ValueError:
            print("Invalid date, please try again or press Ctrl + C to exit.")

    print(f"Valid date has been entered: {type(date)}")
    # The type returned for date is str
    return date


def working_day(date):
    raw_date = datetime.strptime(date, "%Y%m%d")
    # Format data to be without time zone
    formatted_date = datetime.date(raw_date)
    first_of_month = formatted_date.replace(day=1)
    date_to_check = first_of_month - timedelta(days=1)
    # Use .weekday directly on the date that i need
    while date_to_check.weekday() >= 5:
        print(date_to_check, date_to_check.weekday())
        date_to_check = date_to_check - timedelta(days=1)

    return date_to_check.strftime("%Y%m%d")


def check_files(valid_date):
    for file in files_to_check:

        final_file = Path(path_origin) / file_path / f"{file}{valid_date}.csv"

        if final_file.exists():
            # print(f"File exists: {file}{valid_date}.csv")
            return True
        else:
            print(f"File does not exist for the current date: {file}{valid_date}")
            return False


def format_file_mtd(date):
    full_path = path_origin + file_path + f"/mtdvolfeed{date}.csv"
    mtd = pd.read_csv(full_path)
    mtd_commission = pd.read_csv(full_path)

    account_number = mtd["ACCT"].astype(str).str.zfill(5)
    account = mtd_commission["ACCT"].astype(str).str.zfill(5)
    mtd = mtd[mtd["WDATID"] == "M"]
    mtd.insert(0, "Class_ID", "ARB" + account_number + "_" + mtd["CURRENCY"])
    grouped_mtd = mtd.groupby("Class_ID").agg({"PL_TOTAL": "sum", "OPT_PREMIUM": "sum"})

    grouped_mtd.to_csv(f"mtd{date}_formatted.csv")

    # Commisons
    mtd_commission.insert(
        0, "Class_ID", "ARB" + account + "_" + mtd_commission["COMMISSION_C"]
    )

    mtd_commission = mtd_commission.groupby("Class_ID").agg({"COMMISSION": "sum"})

    mtd_commission.to_csv(f"commison{date}.csv")

    print(date)
    # return mtd


def format_file_mny(current_date, previous_date):
    current_file = pd.read_csv(path_origin + file_path + f"/mny{current_date}.csv")
    prev_file = pd.read_csv(path_origin + file_path + f"/mny{previous_date}.csv")

    current_account_number = current_file["MACCT"].astype(str).str.zfill(5)
    prev_account_number = prev_file["MACCT"].astype(str).str.zfill(5)

    current_file.insert(
        0, "Class_ID", "ARB" + current_account_number + "_" + current_file["MCURAT"]
    )
    prev_file.insert(
        0, "Class_ID", "ARB" + prev_account_number + "_" + prev_file["MCURAT"]
    )

    current_file = current_file[current_file["MRECID"] == "M"]
    prev_file = prev_file[prev_file["MRECID"] == "M"]

    current_file.to_csv(f"formated_test{current_date}.csv")
    prev_file.to_csv(f"formated_test{previous_date}.csv")


def main():
    # Validate date, if user did input a valid date format
    current_date = validate_date()
    previous_date = working_day(current_date)

    # Check for files if they exist for the date user specified
    files_exist = check_files(current_date)

    if files_exist:
        working_day(current_date)
        format_file_mtd(current_date)
        # format_file_mny(current_date, previous_date)
    else:
        print("Files do not exist, or some error has occured")


if __name__ == "__main__":
    main()
