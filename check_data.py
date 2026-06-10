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

# date = "20260525"


# Here i get the date from the input and check if the date is a valid type matching my files
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


# This function gets the date and formats it to be 05/25/2026
def format_date(date):
    date_value = pd.to_datetime(date)
    return f"{date_value.month}/{date_value.day}/{date_value.year}"


# Here i find the last working day based on the frequency either monthly or daily
# If monthly => find the last working day of the previous month
# If daily => find the last working day goind backwards
def working_day(date: str, frequency: str = "monthly") -> str:
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


# This returns true or false if the previous day was a working day
def is_previous_day_working(date: str) -> bool:
    raw_date = datetime.strptime(date, "%Y%m%d")
    previous_day = raw_date.date() - timedelta(days=1)

    return previous_day.weekday() < 5


# Here I find the next workind day
def next_working_day(date: str) -> str:
    raw_date = datetime.strptime(date, "%Y%m%d")
    date_to_check = raw_date.date() + timedelta(days=1)

    while date_to_check.weekday() >= 5:
        date_to_check += timedelta(days=1)

    return date_to_check.strftime("%d/%m/%Y")


# Here i get the date user did provide and check if i have files for that date
def check_files(valid_date):
    for file in files_to_check:

        final_file = Path(path_origin) / file_path / f"{file}{valid_date}.csv"

        if final_file.exists():
            return True
        else:
            print(f"File does not exist for the current date: {file}{valid_date}")
            return False


# Take the mtdvolfeed file for the provided date and format it to be ready for mny file
def format_file_mtd(date):
    full_path = path_origin + file_path + f"/mtdvolfeed{date}.csv"
    mtd = pd.read_csv(full_path)

    account_number = mtd["ACCT"].astype(str).str.zfill(5)
    mtd_m = mtd[mtd["WDATID"] == "M"].copy()

    # --- Base aggregation (PL_TOTAL, OPT_PREMIUM) ---
    mtd_m.insert(0, "Class_ID", "ARB" + account_number + "_" + mtd["CURRENCY"])
    mtd_m["Class_ID"] = mtd_m["Class_ID"].replace("ARB00005_CNH", "ARB00005_CNY")
    result = mtd_m.groupby("Class_ID").agg({"PL_TOTAL": "sum", "OPT_PREMIUM": "sum"})

    # --- Dynamically find all *_C columns and their matching *_FEE columns ---
    fee_cols = [col for col in mtd.columns if col.endswith("_C")]

    def fee_calculation(currency_col, mtd_m):
        # Derive the fee column name by replacing _C suffix with _FEE
        fee_col = currency_col[:-2]

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

    result.to_csv(f"mtd-result{date}.csv")
    return result


# Optimizing the format_file_mny function to not reapeat myself for the current and prev files
def prepare_mny_file(df):
    account_number = df["MACCT"].astype(str).str.zfill(5)
    df.insert(0, "Class_ID", "ARB" + account_number + "_" + df["MCURAT"])
    df["Class_ID"] = df["Class_ID"].replace("ARB00005_CNH", "ARB00005_CNY")
    df = df[df["MRECID"] == "M"]

    return df


def check_if_file_exists(date, df):
    reports_path = "DailyReports/Daily_missing_accounts"
    full_reports_path = path_origin + reports_path + f"/missing_accounts_{date}.csv"
    ta_class_df = pd.read_csv(
        "C:/Users/Roman Lupan/ARB Sustained Holdings/Arb-Shares - Corporate/Accounting-Finance/Reporting Data/Sage/TA_Classes/TA_Classes.csv"
    )

    class_id_ta_class = set(ta_class_df["Class ID"])
    missing_class_id_df = df.loc[~df["Class_ID"].isin(class_id_ta_class)]

    # Step 1: Find class_ids in mny_file not present in accounts_df titles
    known_classes = set(ta_class_df["Class ID"].dropna().unique())
    all_class_ids = df["Class_ID"].dropna().unique()
    missing_ids = [cid for cid in all_class_ids if cid not in known_classes]
    print(missing_ids)

    # Step 2: Handle missing class_ids
    for class_id in missing_ids:
        if os.path.exists(full_reports_path):
            missing_df = pd.read_csv(full_reports_path, dtype=str)

            # Add only if not already tracked
            if class_id not in missing_df["Class_ID"].values:
                new_row = pd.DataFrame([{"Class_ID": class_id}])
                missing_df = pd.concat([missing_df, new_row], ignore_index=True)
                missing_df.to_csv(full_reports_path, index=False)
        else:
            # Create the file with this first missing entry
            pd.DataFrame([{"Class_ID": class_id}]).to_csv(
                full_reports_path, index=False
            )

    # Step 3: Clean up resolved ARB0* entries
    if os.path.exists(full_reports_path):
        missing_df = pd.read_csv(full_reports_path, dtype=str)

        resolved_mask = missing_df["Class_ID"].isin(known_classes) & missing_df[
            "Class_ID"
        ].str.startswith("ARB0")
        missing_df = missing_df[~resolved_mask]

        if missing_df.empty:
            os.remove(full_reports_path)
        else:
            missing_df.to_csv(full_reports_path, index=False)


def format_file_mny(current_date, previous_date):
    current_df = pd.read_csv(path_origin + file_path + f"/mny{current_date}.csv")
    prev_df = pd.read_csv(path_origin + file_path + f"/mny{previous_date}.csv")
    accounts = pd.read_csv(
        "C:/Users/Roman Lupan/ARB Sustained Holdings/Arb-Shares - Corporate/Accounting-Finance/Reporting Data/Sage/TA_Classes/Accounts.csv"
    )

    current_file = prepare_mny_file(current_df)
    prev_file = prepare_mny_file(prev_df)

    current_file = current_file[
        ~current_file["Class_ID"].isin(accounts["Title"].tolist())
    ]

    current_file = current_file.groupby("Class_ID", as_index=False).sum(
        numeric_only=True
    )
    prev_file = prev_file.groupby("Class_ID", as_index=False).sum(numeric_only=True)

    prev_file = prev_file[~prev_file["Class_ID"].isin(accounts["Title"].tolist())]

    # Check for new class ID's
    check_if_file_exists(current_date, current_file)

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

    # print(prev_metrics.head())
    # print(final_result.head())

    # final_result.to_csv(f"formatted_mny_{current_date}.csv")
    return final_result


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

    sage_template = pd.read_csv("C:/Users/Roman Lupan/Documents/GL-JE_template.csv")
    sage_cols = sage_template.columns.tolist()

    sage_file = pd.DataFrame(columns=sage_cols)

    formatted_mny["Temporary_Total"] = (
        formatted_mny["CLEARING_FEE"] + formatted_mny["EXCHANG_EFE"]
    )

    gl_list_to_post = []

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

    entries = [
        (
            "Wedbush_Trading gain (loss), net",
            "12100",
            "40050",
            "TRD_RESULT_CALCULATION",
        ),
        ("Wedbush_Brokerage Commissions", "12100", "50110", "COMMISSION"),
        ("Wedbush_Clearing and Exchange Fees", "12100", "50120", "Temporary_Total"),
    ]

    for description, debit_acct, credit_acct, reference in entries:
        dt = gl_dt_ct(
            sage_file,
            formatted_mny,
            description,
            "DEBIT",
            debit_acct,
            current_date,
            reference,
        )
        ct = gl_dt_ct(
            sage_file,
            formatted_mny,
            description,
            "CREDIT",
            credit_acct,
            current_date,
            reference,
        )
        gl_list_to_post.append(pd.concat([dt, ct]))

    combined_df = pd.concat(gl_list_to_post, ignore_index=True)

    id_maps = {
        "DEPT_ID": "Department ID",
        "LOCATION_ID": "Location ID",
        "GLENTRY_CUSTOMERID": "Customer ID",
    }

    for col, source_col in id_maps.items():
        combined_df[col] = combined_df["GLENTRY_CLASSID"].map(
            ta_classes.set_index("Class ID")[source_col]
        )

    formatted_date = format_date(current_date)

    combined_df["DATE"] = formatted_date

    if is_previous_day_working(current_date):
        combined_df["JOURNAL"] = "GJ"
    else:
        last_day = next_working_day(current_date)
        right_type = format_date(last_day)
        combined_df["JOURNAL"] = "DTA"
        combined_df["REVERSEDATE"] = right_type

    combined_df.to_csv(f"sage_ready_file_{current_date}.csv")


def main():
    # Validate date, if user did input a valid date format
    current_date = validate_date()
    previous_date = working_day(current_date)

    # Check for files if they exist for the date user specified
    files_exist = check_files(current_date)

    if files_exist:
        working_day(current_date)
        # format_file_mtd(current_date)
        format_file_mny(current_date, previous_date)
        # prepare_for_sage(current_date, previous_date)
    else:
        print("Files do not exist, or some error has occured")


if __name__ == "__main__":
    main()
