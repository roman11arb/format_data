# 1. Make the script so it can take data as a prop
# 2. Make a function that verifys the existance of folders with that data
# 3. Run the script from a .bat file
# 4. The function shall return true or false
# 5. Check file mny, mtdvolfeed, pos, st4

import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

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
    # mtd = mtd.rename(columns={"COMMISSION": "COMMISSION_FEE"})
    # currency_cols = [col for col in mtd.columns if col.endswith("_C")]

    account_number = mtd["ACCT"].astype(str).str.zfill(5)
    mtd_m = mtd[mtd["WDATID"] == "M"].copy()

    # --- Base aggregation (PL_TOTAL, OPT_PREMIUM) ---
    mtd_m.insert(0, "Class_ID", "ARB" + account_number + "_" + mtd["CURRENCY"])
    result = mtd_m.groupby("Class_ID").agg({"PL_TOTAL": "sum", "OPT_PREMIUM": "sum"})

    # --- Dynamically find all *_C columns and their matching *_FEE columns ---
    fee_cols = [col for col in mtd.columns if col.endswith("_C")]

    def fee_calculation(currency_col, mtd_m):
        # Derive the fee column name by replacing _C suffix with _FEE
        fee_col = currency_col[:-2]
        print(currency_col)

        # Here i take out all the probability that an empty value may go past
        temp_df = mtd_m.copy()
        temp_df[currency_col] = temp_df[currency_col].str.replace(" ", "")
        temp_df = temp_df.loc[~(temp_df[currency_col].isna())]
        temp_df = temp_df.loc[~(temp_df[currency_col] == "")]
        temp_df = temp_df.loc[~(temp_df[fee_col] == 0)]

        temp_df["Class_ID"] = (
            "ARB"
            + temp_df["ACCT"].astype(str).str.zfill(5)
            + "_"
            + temp_df[currency_col]
        )

        aggregated = temp_df.groupby("Class_ID", as_index=False).agg({fee_col: "sum"})
        print(aggregated)
        return aggregated

    # If we meet an col that has empty values just go past
    for currency_col in fee_cols:
        aggregated = fee_calculation(currency_col, mtd_m)

        if aggregated.empty:
            continue

        result = result.merge(aggregated, on="Class_ID", how="outer")
    result = result.fillna(0)
    result["Total_Fees"] = 0
    fee_col_list = []
    for columns in result.columns:
        if columns in ["PL_TOTAL", "OPT_PREMIUM", "Class_ID", "Total_Fees"]:
            continue

        fee_col_list.append(columns)
        result["Total_Fees"] = result["Total_Fees"] + result[columns]

    print(fee_col_list)

    # # --- Handle COMMISSION separately (keeping your original logic) ---
    # commission_df = mtd_m.copy()
    # commission_df["Class_ID"] = "ARB" + account_number + "_" + mtd_m["COMMISSION_C"]

    # result = result.groupby("Class_ID").sum()
    result.to_csv("mtd-result.csv")
    return result


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
