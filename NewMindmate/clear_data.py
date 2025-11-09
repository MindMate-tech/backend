"""
Safely clears all data from the MindMeld database while preserving tables and schema.
"""

from db.supabase_client import get_supabase

def clear_data(confirm: bool = True):
    """
    Deletes all data from the MindMeld database tables in the correct dependency order.
    Does NOT drop or alter any tables.
    """

    supabase = get_supabase()

    # Correct order: child tables → parent tables (respect foreign keys)
    tables_in_delete_order = [
        "doctor_records",  # depends on doctors, patients, sessions, mri_scans
        "mri_scans",       # depends on patients, doctors, sessions
        "memories",        # depends on patients
        "sessions",        # depends on patients
        "patients",        # independent of others except referenced by above
        "doctors",         # independent of others except referenced by above
    ]

    print("⚠️  This operation will permanently delete ALL DATA from all major tables.")
    if confirm:
        proceed = input("Type 'CONFIRM' to proceed: ")
        if proceed.strip().upper() != "CONFIRM":
            print("❌ Operation cancelled.")
            return

    print("\n🧹 Starting data cleanup...\n")

    for table in tables_in_delete_order:
        print(f"  - Clearing table '{table}' ...")
        try:
            # Supabase requires a filter to perform deletion.
            # Using a condition guaranteed to be true for all rows.
            response = (
                supabase.table(table)
                .delete()
                .neq("created_at", "2200-01-01T00:00:00+00:00")
                .execute()
            )

            # Log outcome
            deleted_count = len(response.data) if response.data else 0
            if deleted_count > 0:
                print(f"    ✅ Deleted {deleted_count} rows from '{table}'")
            else:
                print(f"    ⚪ No data found or already empty.")

        except Exception as e:
            print(f"    ❌ Error clearing {table}: {e}")

    print("\n✅ Database data cleared successfully (schema preserved).")


if __name__ == "__main__":
    clear_data()
