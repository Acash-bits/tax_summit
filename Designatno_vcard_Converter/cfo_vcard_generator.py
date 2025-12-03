import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def connect_to_mysql(host, user, password, database):
    """Establish connection to MySQL database"""
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        if connection.is_connected():
            print(f"✓ Connected to MySQL database: {database}")
            return connection
    except Error as e:
        print(f"✗ Error connecting to MySQL: {e}")
        return None

def sanitize_vcard_text(text):
    """Sanitize text for vCard format - escape special characters"""
    if text is None or text == '':
        return ''
    text = str(text).strip()
    # Escape special characters for vCard
    text = text.replace('\\', '\\\\')
    text = text.replace(',', '\\,')
    text = text.replace(';', '\\;')
    text = text.replace('\n', '\\n')
    return text

def create_vcard(cfo_name, designation_2, company_name, phone_number_4, email_id_3):
    """
    Create a single vCard (VCF format) entry for CFO
    
    vCard 3.0 Format:
    - First Name = CFO_Name + Designation_2
    - Last Name = Company_Name
    - Phone = Phone_Number_4
    - Email = Email_ID_3
    """
    
    # Build first name (CFO Name + Designation)
    first_name_parts = []
    if cfo_name:
        first_name_parts.append(sanitize_vcard_text(cfo_name))
    if designation_2:
        first_name_parts.append(f"({sanitize_vcard_text(designation_2)})")
    
    first_name = ' '.join(first_name_parts) if first_name_parts else 'Unknown'
    last_name = sanitize_vcard_text(company_name) if company_name else 'Company'
    
    # Full name for display
    full_name = f"{first_name} {last_name}"
    
    # Sanitize contact info
    phone = sanitize_vcard_text(phone_number_4) if phone_number_4 else ''
    email = sanitize_vcard_text(email_id_3) if email_id_3 else ''
    
    # Create vCard in version 3.0 format (best compatibility with iCloud)
    vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{full_name}
N:{last_name};{first_name};;;
"""
    
    # Add phone number if available
    if phone:
        vcard += f"TEL;TYPE=WORK,VOICE:{phone}\n"
    
    # Add email if available
    if email:
        vcard += f"EMAIL;TYPE=WORK:{email}\n"
    
    vcard += "END:VCARD"
    
    return vcard

def get_pending_contacts(connection):
    """Fetch CFO contacts with numRegistrations = 1 and Response_7 >= 0 (not null, not negative)"""
    cursor = connection.cursor(dictionary=True)
    
    query = """
    SELECT 
        S_No,
        Company_Name,
        CFO_Name,
        Designation_2,
        Email_ID_3,
        Phone_Number_4
    FROM CFO_Persons_details
    WHERE Contact_Created_Status = 0
    AND Phone_Number_4 IS NOT NULL 
    AND Phone_Number_4 != ''
    AND numRegistrations = 1
    AND Response_7 IS NOT NULL
    AND Response_7 >= 0
    ORDER BY Company_Name, CFO_Name
    """
    
    try:
        cursor.execute(query)
        contacts = cursor.fetchall()
        print(f"✓ Found {len(contacts)} pending CFO contacts to export")
        return contacts
    except Error as e:
        print(f"✗ Error fetching contacts: {e}")
        return []
    finally:
        cursor.close()

def update_contact_status(connection, s_no):
    """Update contact status to 1 and set creation timestamp"""
    cursor = connection.cursor()
    
    update_query = """
    UPDATE CFO_Persons_details
    SET Contact_Created_Status = 1,
        Contact_File_Created_Time_Stamp = CURRENT_TIMESTAMP
    WHERE S_No = %s
    """
    
    try:
        cursor.execute(update_query, (s_no,))
        connection.commit()
    except Error as e:
        print(f"✗ Error updating status for S_No {s_no}: {e}")
    finally:
        cursor.close()

def generate_vcards_from_cfo_persons():
    """Main function to generate vCard file from CFO_Persons_details table"""
    
    print("\n" + "="*70)
    print("  CFO PERSONS VCARD GENERATOR (FILTERED)")
    print("="*70 + "\n")
    
    # Connect to database
    connection = connect_to_mysql(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
    
    if not connection:
        return
    
    try:
        # Get pending contacts
        print("[Step 1] Fetching filtered CFO contacts from database...")
        print("           Filters: numRegistrations = 1, Response_7 >= 0 (not null)")
        contacts = get_pending_contacts(connection)
        
        if not contacts:
            print("\n✓ No pending CFO contacts matching criteria to export!")
            return
        
        # Generate vCards
        print(f"\n[Step 2] Generating vCards for {len(contacts)} CFO contacts...")
        
        all_vcards = []
        processed_contacts = []
        
        for contact in contacts:
            vcard = create_vcard(
                cfo_name=contact['CFO_Name'],
                designation_2=contact['Designation_2'],
                company_name=contact['Company_Name'],
                phone_number_4=contact['Phone_Number_4'],
                email_id_3=contact['Email_ID_3']
            )
            all_vcards.append(vcard)
            processed_contacts.append(contact['S_No'])
        
        # Create output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"CFO_Contacts_{timestamp}.vcf"
        
        # Write all vCards to single file
        print(f"\n[Step 3] Writing vCards to file: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(all_vcards))
        
        print(f"✓ Successfully created {output_file}")
        
        # Update database status
        print(f"\n[Step 4] Updating contact status in database...")
        for s_no in processed_contacts:
            update_contact_status(connection, s_no)
        
        print(f"✓ Updated {len(processed_contacts)} CFO contacts as 'Created'")
        
        # Summary
        print("\n" + "="*70)
        print("  ✓ VCARD GENERATION COMPLETE!")
        print("="*70)
        print(f"\nFile created: {output_file}")
        print(f"Total CFO contacts: {len(contacts)}")
        print(f"\nFilters applied:")
        print(f"  • numRegistrations = 1")
        print(f"  • Response_7 IS NOT NULL and >= 0")
        print(f"\nNext steps:")
        print(f"  1. Open {output_file}")
        print(f"  2. Import to iCloud Contacts")
        print(f"  3. All CFO contacts are now marked as 'Created' in database")
        print()
        
    finally:
        if connection.is_connected():
            connection.close()
            print("✓ MySQL connection closed\n")

if __name__ == "__main__":
    generate_vcards_from_cfo_persons()