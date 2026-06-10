 # if not missing_class_id_df.empty:
    #     if os.path.exists(full_reports_path):
    #         print(f"If path exists: {full_reports_path}")
    #         # Add class_id to existent file
    #         reports_df = pd.read_csv(full_reports_path)
    #         missing_class_id_df = missing_class_id_df[
    #             ~missing_class_id_df["Class_ID"].isin(reports_df["Class_ID"].tolist())
    #         ]
    #         print(missing_class_id_df)
    #     if not missing_class_id_df.empty:
    #         print(f"Missing class id not empty: {missing_class_id_df}")
    #         reports_df = pd.read_csv(full_reports_path)
    #         reports_df = pd.concat([reports_df, missing_class_id_df["Class_ID"]])
    #         reports_df = pd.to_csv(full_reports_path)
    # else:
    #     if os.path.exists(full_reports_path):
    #         print(f"If path exists: {full_reports_path}")
    #         reports_df = reports_df[~reports_df["Class_ID"].str.startswith("ARB0")]

    #         if not reports_df.empty:
    #             reports_df.to_csv(full_reports_path, index=False)
    #         else:
    #             os.remove(full_reports_path)

    # for class_id in df["Class_ID"]:
    #     if class_id not in class_id_ta_class:
    #         found_class_id = True
    #         class_id_list.append(class_id)
    # print(f"{class_id} found")
    # print(f"Found: {found_class_id}")

    # if found_class_id:
    #     if os.path.exists(full_reports_path):
    #         # Add class_id to existent file
    #         full_reports_path["Class_ID"] = class_id_list
    #         print("File found")
    #         # Add found class id's here to the full_reports_path
    #     else:
    #         missing_class = pd.DataFrame(columns=["Class_ID"])
    #         missing_class["Class_ID"] = class_id_list
    #         missing_class.to_csv(f"missing_accounts_{date}.csv", index=False)
    #         print("File not found: can create one")
    # else:
    #     print("Class ID not found safe to continue")