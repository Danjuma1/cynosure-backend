import json

# === MODEL MAP BASED ON YOUR APP STRUCTURE ===
MODEL_MAP = {
    "users": "authentication.user",
    "user_followings": "authentication.userfollowing",

    "courts": "courts.court",
    "divisions": "courts.division",
    "courtrooms": "courts.courtroom",
    "court_holidays": "courts.courtholiday",

    "judges": "judges.judge",

    "cases": "cases.case",
    "case_hearings": "cases.casehearing",

    "cause_lists": "cause_lists.causelist",
    "cause_list_entries": "cause_lists.causelistentry",

    "notifications": "notifications.notification",
    "notification_preferences": "notifications.notificationpreference",

    "document_categories": "repository.documentcategory",
    "legal_documents": "repository.legaldocument",
}

def convert_to_fixture(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixture = []

    for section, entries in data.items():
        # Skip metadata
        if section == "metadata":
            continue

        if section not in MODEL_MAP:
            print(f"[SKIPPED] No model mapping for: {section}")
            continue

        model_name = MODEL_MAP[section]

        for obj in entries:
            pk = obj.get("id") or obj.get("pk")

            # Remove "id" from fields
            obj_fields = {k: v for k, v in obj.items() if k not in ["id", "pk"]}

            fixture.append({
                "model": model_name,
                "pk": pk,
                "fields": obj_fields
            })

        print(f"[OK] Converted {len(entries)} objects from '{section}' → {model_name}")

    # Save final fixture
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(fixture, f, indent=2)

    print("\nDONE! Django fixture created:", output_file)


# === RUN ===
convert_to_fixture("sample_data.json", "final_fixture.json")
