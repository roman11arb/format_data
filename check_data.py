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

# date = "20260525"


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


def format_date(date):
    date_value = pd.to_datetime(date)
    return f"{date_value.month}/{date_value.day}/{date_value.year}"


def working_day(date: str, frequency: str = "monthly") -> str:
    """
    Find the last working day based on frequency.

    Args:
        date: Date string in format YYYYMMDD
        frequency: Either 'monthly' (last working day of previous month)
                   or 'daily' (last working day before the given date)

    Returns:
        Date string in format YYYYMMDD
    """
    if frequency not in ("monthly", "daily"):
        raise ValueError(
            f"Invalid frequency '{frequency}'. Must be 'monthly' or 'daily'."
        )

    raw_date = datetime.strptime(date, "%Y%m%d")
    formatted_date = raw_date.date()

    if frequency == "monthly":
        # Go to the last day of the previous month
        first_of_month = formatted_date.replace(day=1)
        date_to_check = first_of_month - timedelta(days=1)
    elif frequency == "daily":
        # Start from the day before the given date
        date_to_check = formatted_date - timedelta(days=1)

    # Walk backwards until we land on a weekday (Mon=0 ... Fri=4)
    while date_to_check.weekday() >= 5:
        date_to_check -= timedelta(days=1)

    return date_to_check.strftime("%Y%m%d")


def is_previous_day_working(date: str) -> bool:
    """
    Check if the day immediately before the given date was a working day (Mon–Fri).

    Args:
        date: Date string in format YYYYMMDD

    Returns:
        True if the previous calendar day was a working day, False otherwise
    """
    raw_date = datetime.strptime(date, "%Y%m%d")
    previous_day = raw_date.date() - timedelta(days=1)

    return previous_day.weekday() < 5


def next_working_day(date: str) -> str:
    """
    Find the next working day after the given date.

    Args:
        date: Date string in format YYYYMMDD

    Returns:
        Date string in format YYYYMMDD of the next working day
    """
    raw_date = datetime.strptime(date, "%Y%m%d")
    date_to_check = raw_date.date() + timedelta(days=1)

    while date_to_check.weekday() >= 5:
        date_to_check += timedelta(days=1)

    return date_to_check.strftime("%d/%m/%Y")


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
        # print(currency_col)

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
        # print(aggregated)
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

    # print(fee_col_list)

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
    accounts = pd.read_csv(
        "C:/Users/Roman Lupan/ARB Sustained Holdings/Arb-Shares - Corporate/Accounting-Finance/Reporting Data/Sage/TA_Classes/Accounts.csv"
    )

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

    current_file = current_file[
        ~current_file["Class_ID"].isin(accounts["Title"].tolist())
    ]

    current_file = current_file.groupby("Class_ID", as_index=False).sum(
        numeric_only=True
    )
    prev_file = prev_file.groupby("Class_ID", as_index=False).sum(numeric_only=True)

    prev_file = prev_file[~prev_file["Class_ID"].isin(accounts["Title"].tolist())]

    # Take the cols that i need from the prev_file and put them in a list
    # Make a loop that for each col in that list I shall add to it's name _PREV
    # Append these cols to the mtd_result file from previous function
    # On the each step write a print statement to be easier to debug

    # After that do the same thing but for the current file and don't add the _PREV at the end

    mtd_final = format_file_mtd(current_date)

    prev_metrics = prev_file[["MOTE", "MSOV", "MLOV", "MLQVAL", "Class_ID"]]
    current_metrics = current_file[["MOTE", "MSOV", "MLOV", "MLQVAL", "Class_ID"]]
    prev_metrics = prev_metrics.rename(
        columns={
            "MOTE": "MOTE_PREV",
            "MLOV": "MLOV_PREV",
            "MSOV": "MSOV_PREV",
            "MLQVAL": "MLQVAL_PREV",
        }
    )

    final_result = pd.merge(mtd_final, prev_metrics, on="Class_ID", how="inner")
    final_result = pd.merge(final_result, current_metrics, on="Class_ID", how="inner")

    final_result["UNREALISED"] = (
        final_result["MOTE"]
        + final_result["MSOV"]
        + final_result["MLOV"]
        - final_result["MOTE_PREV"]
        - final_result["MSOV_PREV"]
        - final_result["MLOV_PREV"]
    )

    final_result["TRD_RESULT_CALCULATION"] = (
        final_result["PL_TOTAL"]
        + final_result["OPT_PREMIUM"]
        + final_result["UNREALISED"]
    )

    final_result["Prev_Bal"] = final_result["MLQVAL_PREV"]
    final_result["Bal"] = final_result["MLQVAL"]

    final_result["TRD_RESULT"] = final_result["Bal"] - final_result["Prev_Bal"]

    final_result["Final"] = (
        final_result["TRD_RESULT_CALCULATION"] - final_result["TRD_RESULT"]
    )

    final_result["Final"] = final_result["Final"].round(2)

    print(prev_metrics.head())
    print(final_result.head())

    final_result.to_csv(f"final_result{current_date}.csv")
    return final_result

    # current_file.to_csv(f"formated_test{current_date}.csv")
    # prev_file.to_csv(f"formated_test{previous_date}.csv")


def prepare_for_sage(current_date, previous_date):
    ta_classes = pd.read_csv(f"{path_origin}Sage/TA_Classes/TA_Classes.csv")
    formatted_mny = format_file_mny(current_date, previous_date)

    # formatted_mny = pd.read_csv("final_result20260525.csv")
    formatted_mny.index = formatted_mny["Class_ID"].tolist()

    # print(formatted_mny[formatted_mny.index.duplicated(keep="first")])

    # Calculate TRD gain and loss = Unrealized _ PL_TOTAL + OPT_PREMIUM
    # Get commsissons
    # Calculate clearing + exchange_efe
    # other fees = rest of the fees sum()

    # metrics = ["gain/loss", "commissions", "exch-fee"]

    sage_template = pd.read_csv("C:/Users/Roman Lupan/Documents/GL-JE_template.csv")
    sage_cols = sage_template.columns.tolist()

    sage_file = pd.DataFrame(columns=sage_cols)

    formatted_mny["Temporary_Total"] = (
        formatted_mny["CLEARING_FEE"] + formatted_mny["EXCHANG_EFE"]
    )
    gl_list_to_post = []
    cols_to_copy = ["Customer ID", "Location ID", "Department ID"]

    def gl_dt_ct(sage_template, df, description, dt_ct_col, acct, date, value_col):
        df_gl = pd.DataFrame(columns=sage_template.columns)
        df_gl["GLENTRY_CLASSID"] = df["Class_ID"]
        # sage_template.index = sage_template["GLENTRY_CLASSID"].tolist()
        df_gl["DESCRIPTION"] = f"{description}_{date}"
        # sage_template[dt_ct_col] = df[value_col]
        df_gl[dt_ct_col] = df_gl["GLENTRY_CLASSID"].map(
            df.set_index("Class_ID")[value_col]
        )

        df_gl["ACCT_NO"] = acct
        if dt_ct_col == "DEBIT":
            ct_col = "CREDIT"
        else:
            ct_col = "DEBIT"

        negmask = df_gl[dt_ct_col] <= 0
        df_gl.loc[negmask, ct_col] = df_gl.loc[negmask, dt_ct_col].abs()

        df_gl.loc[negmask, dt_ct_col] = pd.NA

        return df_gl

    trd_gain_dt = gl_dt_ct(
        sage_file,
        formatted_mny,
        "Wedbush_Trading gain (loss), net",
        "DEBIT",
        "12100",
        current_date,
        "TRD_RESULT_CALCULATION",
    )

    trd_gain_ct = gl_dt_ct(
        sage_file,
        formatted_mny,
        "Wedbush_Trading gain (loss), net",
        "CREDIT",
        "40050",
        current_date,
        "TRD_RESULT_CALCULATION",
    )

    trd_gain = pd.concat([trd_gain_dt, trd_gain_ct])

    commissions_dt = gl_dt_ct(
        sage_file,
        formatted_mny,
        "Wedbush_Brokerage Commissions",
        "DEBIT",
        "12100",
        current_date,
        "COMMISSION",
    )

    commissions_ct = gl_dt_ct(
        sage_file,
        formatted_mny,
        "Wedbush_Brokerage Commissions",
        "CREDIT",
        "50110",
        current_date,
        "COMMISSION",
    )

    commissions = pd.concat([commissions_dt, commissions_ct])

    clearing_exchange_dt = gl_dt_ct(
        sage_file,
        formatted_mny,
        "Wedbush_Clearing and Exchange Fees",
        "DEBIT",
        "12100",
        current_date,
        "Temporary_Total",
    )

    clearing_exchange_ct = gl_dt_ct(
        sage_file,
        formatted_mny,
        "Wedbush_Clearing and Exchange Fees",
        "CREDIT",
        "50120",
        current_date,
        "Temporary_Total",
    )

    clearing_exchange = pd.concat([clearing_exchange_dt, clearing_exchange_ct])

    gl_list_to_post.append(trd_gain)
    gl_list_to_post.append(commissions)
    gl_list_to_post.append(clearing_exchange)

    combined_df = pd.concat(gl_list_to_post, ignore_index=True)

    department_id_map = ta_classes.set_index("Class ID")["Department ID"]
    location_id_map = ta_classes.set_index("Class ID")["Location ID"]
    customer_id_map = ta_classes.set_index("Class ID")["Customer ID"]

    combined_df["DEPT_ID"] = combined_df["GLENTRY_CLASSID"].map(department_id_map)
    combined_df["LOCATION_ID"] = combined_df["GLENTRY_CLASSID"].map(location_id_map)
    combined_df["GLENTRY_CUSTOMERID"] = combined_df["GLENTRY_CLASSID"].map(
        customer_id_map
    )

    formatted_date = format_date(current_date)

    combined_df["DATE"] = formatted_date

    last_working_day = working_day(current_date, "daily")

    if is_previous_day_working(current_date):
        combined_df["JOURNAL"] = "GJ"
    else:
        last_day = next_working_day(current_date)
        right_type = format_date(last_day)
        combined_df["JOURNAL"] = "DTA"
        combined_df["REVERSEDATE"] = right_type

    print(f"This is the working day: {last_working_day}")

    trd_gain.to_csv("trd_gain.csv")
    commissions.to_csv("commissions_dt.csv")
    clearing_exchange.to_csv("clearing_exchange.csv")
    combined_df.to_csv("combined_data.csv")

    # mapping = {
    #     "gain/loss": [
    #         {
    #             "DESCRIPTION": f"Wedbush_Trading gain (loss), net_{current_date}",
    #             "ACCT_NO": 12100,
    #             "DEBIT": formatted_mny["UNREALISED"]
    #             + formatted_mny["PL_TOTAL"]
    #             + formatted_mny["OPT_PREMIUM"],
    #         },
    #         {
    #             "DESCRIPTION": f"Wedbush_Trading gain (loss), net_{current_date}",
    #             "ACCT_NO": 40050,
    #             "CREDIT": formatted_mny["UNREALISED"]
    #             + formatted_mny["PL_TOTAL"]
    #             + formatted_mny["OPT_PREMIUM"],
    #         },
    #     ],
    #     "commissions": [
    #         {
    #             "DESCRIPTION": f"Wedbush_Brokerage Commissions_{current_date}",
    #             "ACCT_NO": 12100,
    #         },
    #         {
    #             "DESCRIPTION": f"Wedbush_Brokerage Commissions_{current_date}",
    #             "ACCT_NO": 50110,
    #         },
    #     ],
    #     "exch-fee": [
    #         {
    #             "DESCRIPTION": f"Wedbush_Clearing and Exchange Fees_{current_date}",
    #             "ACCT_NO": 12100,
    #         },
    #         {
    #             "DESCRIPTION": f"Wedbush_Clearing and Exchange Fees_{current_date}",
    #             "ACCT_NO": 50120,
    #         },
    #     ],
    # }

    # for metric in metrics:
    #     if metric in mapping:
    #         for row in mapping[metric]:
    #             sage_file.loc[len(sage_file)] = row

    # sage_file["CREDIT"] = formatted_mny["UNREALISED"] + formatted_mny["PL_TOTAL"]
    # sage_file["DEBIT"] = formatted_mny["UNREALISED"] + formatted_mny["OPT_PREMIUM"]

    # sage_file.to_csv("sage_file.csv")
    # print(sage_file)
    # print(sage_cols)


def main():
    # Validate date, if user did input a valid date format
    current_date = validate_date()
    previous_date = working_day(current_date)

    # Check for files if they exist for the date user specified
    files_exist = check_files(current_date)

    if files_exist:
        working_day(current_date)
        # format_file_mtd(current_date)
        # format_file_mny(current_date, previous_date)
        prepare_for_sage(current_date, previous_date)
    else:
        print("Files do not exist, or some error has occured")


if __name__ == "__main__":
    main()
