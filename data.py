import pandas as pd
import os

# Using an env to get the path so I do not repeat myself
reportingData = os.getenv("Reporting-Data")
filePath = "Data_Temporary/Wedbush/FTP/"

# defining the dataframes for the two csv files
mtd = pd.read_csv("mtdvolfeed20260525.csv")
mny = pd.read_csv(reportingData + filePath + "mny20260525.csv")

account_number = mtd["ACCT"].astype(str).str.zfill(5)
mny_acount_number = mny["MACCT"].astype(str).str.zfill(5)

mny = mny[mny["MRECID"] == "M"]

mtd.insert(0, "Class_ID", "ARB" + account_number + "_" + mtd["CURRENCY"])
mny.insert(0, "Class_ID", "ARB" + mny_acount_number + "_" + mny["MCURAT"])

mtd = mtd.groupby("Class_ID").agg({"PL_TOTAL": "sum", "OPT_PREMIUM": "sum"})

# print(mtd["Class_ID"].head())
# print(mny["Class_ID"].head())


mtd.to_csv("mtd.csv")
