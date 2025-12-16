"""
Migration versions for Tax Summit Dashboard
Each migration should have:
- name: unique identifier (format: XXX_description)
- up: list of SQL statements to apply
- down: list of SQL statements to rollback (optional but recommended)
"""

MIGRATIONS = [
    {
        'name': '001_initial_schema',
        'up': [
            """
            CREATE TABLE IF NOT EXISTS tax_summit_master_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Practice_Head VARCHAR(100),
                Partner VARCHAR(100),
                Client_Name VARCHAR(200),
                Location VARCHAR(100),
                Sector VARCHAR(100),
                numInvitees INT DEFAULT 0,
                numRegistrations INT DEFAULT 0,
                Response VARCHAR(50),
                Invite_Dt DATE,
                Circle_Back_Dt DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_practice_head (Practice_Head),
                INDEX idx_partner (Partner),
                INDEX idx_sector (Sector),
                INDEX idx_response (Response)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS Tax_Persons_Analysis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Practice_Head VARCHAR(100),
                Partner VARCHAR(100),
                Client_Name VARCHAR(200),
                Person_Name VARCHAR(200),
                Location VARCHAR(100),
                Sector VARCHAR(100),
                numRegistrations INT DEFAULT 0,
                Response VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_practice_head (Practice_Head),
                INDEX idx_partner (Partner),
                INDEX idx_response (Response)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS CFO_Persons_Analysis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Practice_Head VARCHAR(100),
                Partner VARCHAR(100),
                Client_Name VARCHAR(200),
                Person_Name VARCHAR(200),
                Location VARCHAR(100),
                Sector VARCHAR(100),
                numRegistrations INT DEFAULT 0,
                Response VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_practice_head (Practice_Head),
                INDEX idx_partner (Partner),
                INDEX idx_response (Response)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS Other_Persons_Analysis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Practice_Head VARCHAR(100),
                Partner VARCHAR(100),
                Client_Name VARCHAR(200),
                Person_Name VARCHAR(200),
                Location VARCHAR(100),
                Sector VARCHAR(100),
                numRegistrations INT DEFAULT 0,
                Response VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_practice_head (Practice_Head),
                INDEX idx_partner (Partner),
                INDEX idx_response (Response)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        ],
        'down': [
            "DROP TABLE IF EXISTS Other_Persons_Analysis",
            "DROP TABLE IF EXISTS CFO_Persons_Analysis",
            "DROP TABLE IF EXISTS Tax_Persons_Analysis",
            "DROP TABLE IF EXISTS tax_summit_master_data"
        ]
    },
    
    # Add future migrations here
    # Example:
    # {
    #     'name': '002_add_email_column',
    #     'up': [
    #         """
    #         ALTER TABLE tax_summit_master_data 
    #         ADD COLUMN email VARCHAR(255) AFTER Client_Name,
    #         ADD INDEX idx_email (email)
    #         """
    #     ],
    #     'down': [
    #         "ALTER TABLE tax_summit_master_data DROP COLUMN email"
    #     ]
    # },
]